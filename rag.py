import os
import requests
from typing import List, Dict, Any, TypedDict
from langchain_community.document_loaders import TextLoader

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_weaviate import WeaviateVectorStore
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langgraph.graph import StateGraph, END
import dotenv
import weaviate
from weaviate.embedded import EmbeddedOptions

dotenv.load_dotenv()

# 1. load data & chunk 
loader = TextLoader('./state_of_the_union.txt')
documents = loader.load()
text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.split_documents(documents)
print(f"Loaded {len(chunks)} chunks from the document.")

# 2. embed client
client = weaviate.WeaviateClient(
   embedded_options = EmbeddedOptions()
)
client.connect()  # Need to explicitly connect the client
print("Weaviate client initialized and connected.")

vectorstore = WeaviateVectorStore(
   client=client,
   embedding=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001"),
   index_name="state_of_the_union",
   text_key="content",
)
print("Vector store created.")

# Actually add the chunks to the vector store with rate limiting!
print(f"Adding {len(chunks)} chunks to vector store...")
import time

# Process in smaller batches to avoid quota issues
batch_size = 5  # Smaller batches to respect API limits
total_chunks = len(chunks)

for i in range(0, total_chunks, batch_size):
    batch_end = min(i + batch_size, total_chunks)
    batch_chunks = chunks[i:batch_end]
    
    print(f"Processing batch {i//batch_size + 1}/{(total_chunks + batch_size - 1)//batch_size}: chunks {i+1}-{batch_end}")
    
    try:
        vectorstore.add_documents(batch_chunks)
        print(f"✅ Batch {i//batch_size + 1} completed successfully")
        
        # Add delay between batches to respect rate limits
        if batch_end < total_chunks:  # Don't sleep after the last batch
            print("⏳ Waiting 2 seconds to respect API rate limits...")
            time.sleep(2)
            
    except Exception as e:
        if "quota" in str(e).lower() or "exhausted" in str(e).lower():
            print(f"❌ Quota exceeded at batch {i//batch_size + 1}. Waiting 10 seconds...")
            time.sleep(10)
            # Retry the same batch
            try:
                vectorstore.add_documents(batch_chunks)
                print(f"✅ Batch {i//batch_size + 1} completed after retry")
            except Exception as retry_e:
                print(f"❌ Failed again: {retry_e}")
                print("💡 Try again later when quota resets")
                break
        else:
            print(f"❌ Unexpected error: {e}")
            break

print("Vector store population completed.")

retriever = vectorstore.as_retriever()

llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", temperature=0)

class RAGGraphState(TypedDict):
    question: str
    documents: List[Document]
    generation: str

# question -> relevant documents
def retrieve_documents_node(state: RAGGraphState) -> RAGGraphState:
   question = state["question"]
   documents = retriever.invoke(question)
   return {"documents": documents, "question": question, "generation": ""}

# question + documents -> generation
def generate_response_node(state: RAGGraphState) -> RAGGraphState:
   question = state["question"]
   documents = state["documents"]

   # prompt template
   template = """You are an assistant for question-answering tasks.
Use the following pieces of retrieved context to answer the question.
If you don't know the answer, just say that you don't know.
Use three sentences maximum and keep the answer concise.
Question: {question}
Context: {context}
Answer:
"""
   prompt = ChatPromptTemplate.from_template(template)

   # complete context
   context = "\n\n".join([doc.page_content for doc in documents])

   # RAG chain
   rag_chain = prompt | llm | StrOutputParser()

   # invoke
   generation = rag_chain.invoke({"context": context, "question": question})
   return {"question": question, "documents": documents, "generation": generation}

# construct workflow
workflow = StateGraph(RAGGraphState)
workflow.add_node("retrieve", retrieve_documents_node)
workflow.add_node("generate", generate_response_node)
workflow.set_entry_point("retrieve")
workflow.add_edge("retrieve", "generate")
workflow.add_edge("generate", END)
app = workflow.compile()


if __name__ == "__main__":
   print("\n--- Running RAG Query ---")
   query = "What did the president say about Justice Breyer"
   inputs = {"question": query}
   for s in app.stream(inputs):
       print(s)
   
   # Clean up
   client.close()
   print("\nWeaviate client closed.")
