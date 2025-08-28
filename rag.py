import os
import requests
import json
from typing import List, Dict, Any, TypedDict

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

# 1. load JSON data & create documents
def load_json_data(file_path: str) -> List[Document]:
    """Load JSON test case data and convert to documents"""
    with open(file_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    
    documents = []
    for item in json_data:
        # Create a comprehensive text representation of each test case
        content = f"""
Test Case ID: {item.get('id', '')}
Purpose: {item.get('purpose', '')}
Scenario: {item.get('scenerio', '')}
Test Data: {item.get('test_data', '')}
Steps: {' | '.join(item.get('steps', []))}
Expected Results: {' | '.join(item.get('expected', []))}
Note: {item.get('note', '')}
        """.strip()
        
        # Create document with metadata
        doc = Document(
            page_content=content,
            metadata={
                'id': item.get('id', ''),
                'purpose': item.get('purpose', ''),
                'scenario': item.get('scenerio', ''),
                'test_data': item.get('test_data', ''),
                'source': 'test_cases'
            }
        )
        documents.append(doc)
    
    return documents

# Load test case data
documents = load_json_data('./test_data.json')
print(f"Loaded {len(documents)} test case documents.")

# 2. embed client
client = weaviate.WeaviateClient(
   embedded_options = EmbeddedOptions()
)
client.connect()  # Need to explicitly connect the client
print("Weaviate client initialized and connected.")

vectorstore = WeaviateVectorStore(
   client=client,
   embedding=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001"),
   index_name="test_cases",
   text_key="content",
)
print("Vector store created.")

# Actually add the documents to the vector store with rate limiting!
print(f"Adding {len(documents)} documents to vector store...")
import time

# Process in smaller batches to avoid quota issues
batch_size = 3  # Smaller batches to respect API limits
total_docs = len(documents)

for i in range(0, total_docs, batch_size):
    batch_end = min(i + batch_size, total_docs)
    batch_docs = documents[i:batch_end]
    
    print(f"Processing batch {i//batch_size + 1}/{(total_docs + batch_size - 1)//batch_size}: documents {i+1}-{batch_end}")
    
    try:
        vectorstore.add_documents(batch_docs)
        print(f"✅ Batch {i//batch_size + 1} completed successfully")
        
        # Add delay between batches to respect rate limits
        if batch_end < total_docs:  # Don't sleep after the last batch
            print("⏳ Waiting 2 seconds to respect API rate limits...")
            time.sleep(2)
            
    except Exception as e:
        if "quota" in str(e).lower() or "exhausted" in str(e).lower():
            print(f"❌ Quota exceeded at batch {i//batch_size + 1}. Waiting 10 seconds...")
            time.sleep(10)
            # Retry the same batch
            try:
                vectorstore.add_documents(batch_docs)
                print(f"✅ Batch {i//batch_size + 1} completed after retry")
            except Exception as retry_e:
                print(f"❌ Failed again: {retry_e}")
                print("💡 Try again later when quota resets")
                break
        else:
            print(f"❌ Unexpected error: {e}")
            break

print("Vector store population completed.")

retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

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

   # Enhanced prompt template for test case generation
   template = """You are an expert test case generator specializing in API documentation analysis and comprehensive test scenario creation.

## TASK OVERVIEW
Analyze the provided API documentation and generate detailed test cases that cover business logic flows, focusing on real-world scenarios and edge cases.

## CONTEXT ANALYSIS
Study these similar test cases to understand the expected format and coverage patterns:
{context}

## API DOCUMENTATION TO ANALYZE
{question}

## TEST CASE GENERATION REQUIREMENTS

### JSON Structure (MANDATORY)
Each test case must follow this exact structure:
```json
{{
  "id": "descriptive_test_id_with_scenario",
  "purpose": "Clear business purpose of the test",
  "scenerio": "Specific scenario being tested with conditions",
  "test_data": "Required data sources, DB tables, or mock data",
  "steps": [
    "1. Detailed step with actor and action",
    "2. Include system interactions and API calls",
    "3. Specify database operations and validations"
  ],
  "expected": [
    "1. Expected system behavior with specific status/values",
    "2. Database state changes with table and field details",
    "3. API response format and error codes if applicable"
  ],
  "note": "API references, business rules, or technical constraints"
}}
```

### COVERAGE AREAS (Generate test cases for each applicable area)

1. **Happy Path Scenarios**
   - Normal business flow execution
   - Successful API integrations
   - Proper database updates

2. **Error Handling & Edge Cases**
   - API timeouts and connection failures
   - Invalid input data and validation errors
   - System unavailability and maintenance modes
   - Insufficient resources (balance, quota, etc.)

3. **Business Logic Validation**
   - Conditional flows and decision points
   - Data transformation and calculations
   - State transitions and status updates
   - Multi-step process validation

4. **Integration & Concurrency**
   - External system communication
   - Database transaction consistency
   - Concurrent request handling
   - Race condition prevention

5. **Data Consistency & Rollback**
   - Transaction rollback scenarios
   - Data integrity validation
   - Cross-table consistency checks
   - Audit trail verification

### NAMING CONVENTIONS
- IDs: Use format "category-scenario_number" (e.g., "payment-timeout_1", "validation-invalid-product_1")
- Be descriptive and specific about the scenario being tested

### TECHNICAL DETAILS TO INCLUDE
- Specific database tables and fields
- API endpoint references and versions
- Status codes and error messages
- Timing constraints and timeouts
- Configuration dependencies (CMS, etc.)

## OUTPUT REQUIREMENTS
Generate 5-8 comprehensive test cases covering different aspects of the API documentation. Ensure each test case is:
- **Specific**: Clear scenario with exact conditions
- **Actionable**: Detailed steps that can be executed
- **Verifiable**: Measurable expected outcomes
- **Realistic**: Based on actual business requirements

Focus on business logic testing, not basic validation. Each test should represent a meaningful user journey or system interaction.

## GENERATED TEST CASES:
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
   print("\n--- Running RAG Test Case Generation ---")
   
   # Load sample API documentation
   with open('./sample.md', 'r', encoding='utf-8') as f:
       api_doc = f.read()
   
   query = f"Generate test cases for this API documentation:\n\n{api_doc}"
   inputs = {"question": query}
   
   print("Generating test cases based on API documentation...")
   result = None
   for s in app.stream(inputs):
       print(f"Step: {list(s.keys())[0]}")
       if 'generate' in s:
           result = s['generate']['generation']
   
   print("\n--- Generated Test Cases ---")
   print(result)
   
   # Clean up
   client.close()
   print("\nWeaviate client closed.")
