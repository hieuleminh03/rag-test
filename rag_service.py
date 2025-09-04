#!/usr/bin/env python3
"""
RAG Service for Test Case Generation System
Handles Weaviate embedding and retrieval operations
"""

import os
import json
import time
import logging
import asyncio
import threading
from typing import List, Dict, Any, Optional
from pathlib import Path
import dotenv

dotenv.load_dotenv()

import weaviate
from weaviate.embedded import EmbeddedOptions
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_weaviate import WeaviateVectorStore
from langchain.text_splitter import CharacterTextSplitter
from langgraph.graph import StateGraph, END
from typing import TypedDict

from config import Config
from vietnamese_prompts import DEFAULT_RAG_PROMPT_TEMPLATE, GENERAL_RULES_TEMPLATE
from rag_planning_service import RAGPlanningService

logger = logging.getLogger(__name__)

class RAGGraphState(TypedDict):
    question: str
    documents: List[Document]
    generation: str
    final_prompt: str
    context_used: str

class RAGService:
    """RAG service for test case generation using Weaviate"""
    
    def __init__(self):
        self.client = None
        self.vectorstore = None
        self.retriever = None
        self.llm = None
        self.app = None
        self.is_initialized = False
        self.is_embedded = False
        self.planning_service = RAGPlanningService()
        
    def initialize(self):
        """Initialize Weaviate client and LLM"""
        try:
            # Set up event loop for async operations
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Kill any existing processes and start fresh
            import subprocess
            try:
                subprocess.run(["pkill", "-f", "weaviate"], check=False, capture_output=True)
                time.sleep(3)
            except:
                pass
            
            # Initialize embedded Weaviate client
            self.client = weaviate.WeaviateClient(
                embedded_options=EmbeddedOptions()
            )
            self.client.connect()
            logger.info("Weaviate embedded client initialized and connected")
            
            # Initialize vector store
            self.vectorstore = WeaviateVectorStore(
                client=self.client,
                embedding=GoogleGenerativeAIEmbeddings(model="gemini-embedding-001"),
                index_name="TestCases",
                text_key="text_content",
            )
            logger.info("Vector store created")
            
            # Initialize LLM
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
            logger.info("LLM initialized")
            
            # Check if data is already embedded
            self._check_embedded_status()
            
            if self.is_embedded:
                self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": Config.RAG_TOP_K})
                self._setup_workflow()
                logger.info("RAG workflow initialized")
            
            self.is_initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Error initializing RAG service: {e}")
            return False
    
    def _check_embedded_status(self):
        """Check if test cases are already embedded in the vector store"""
        try:
            # Try to perform a simple query to check if data exists
            test_query = self.vectorstore.similarity_search("test", k=1)
            self.is_embedded = len(test_query) > 0
            logger.info(f"Embedded status: {self.is_embedded}")
        except Exception as e:
            logger.warning(f"Could not check embedded status: {e}")
            self.is_embedded = False
    
    def load_test_case_documents(self, test_case_service=None) -> List[Document]:
        """Load test case data from database and convert to documents with size optimization"""
        try:
            # Import here to avoid circular imports
            if test_case_service is None:
                from services import TestCaseService
                test_case_service = TestCaseService()
            
            # Get all test cases from database
            test_cases = test_case_service.get_all_test_cases()
            
            if not test_cases:
                logger.warning("No test cases found in database")
                return []
            
            documents = []
            for test_case in test_cases:
                # Create a comprehensive text representation of each test case
                test_case_dict = test_case.to_dict() if hasattr(test_case, 'to_dict') else test_case.__dict__
                
                test_case_id = test_case_dict.get('id', '')
                
                # Optimize content by truncating long fields and using concise format
                purpose = self._truncate_text(test_case_dict.get('purpose', ''), 200)
                scenario = self._truncate_text(test_case_dict.get('scenerio', ''), 200)
                test_data = self._truncate_text(test_case_dict.get('test_data', ''), 150)
                
                # Limit and truncate steps and expected results
                steps = test_case_dict.get('steps', [])[:5]  # Max 5 steps
                steps_text = ' | '.join([self._truncate_text(step, 100) for step in steps])
                
                expected = test_case_dict.get('expected', [])[:5]  # Max 5 expected results
                expected_text = ' | '.join([self._truncate_text(exp, 100) for exp in expected])
                
                note = self._truncate_text(test_case_dict.get('note', ''), 100)
                
                # Create optimized content with size limit
                content = f"""ID: {test_case_id}
Purpose: {purpose}
Scenario: {scenario}
Test Data: {test_data}
Steps: {steps_text}
Expected: {expected_text}
Note: {note}""".strip()
                
                # Ensure document doesn't exceed reasonable size (max 1500 chars per document)
                if len(content) > 1500:
                    content = content[:1500] + "..."
                    logger.debug(f"Truncated content for test case {test_case_id} to fit size limit")
                
                # Create document with metadata
                doc = Document(
                    page_content=content,
                    metadata={
                        'test_case_id': test_case_id,
                        'purpose': purpose[:100],  # Truncate metadata too
                        'scenario': scenario[:100],
                        'test_data': test_data[:100],
                        'source': 'database'
                    }
                )
                documents.append(doc)
            
            # Log size information
            total_content_size = sum(len(doc.page_content) for doc in documents)
            logger.info(f"Loaded {len(documents)} test case documents from database")
            logger.info(f"Total content size: {total_content_size:,} characters ({total_content_size/1024:.1f} KB)")
            
            return documents
            
        except Exception as e:
            logger.error(f"Error loading test case documents from database: {e}")
            return []
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncate text to maximum length with ellipsis"""
        if not text:
            return ""
        text = str(text).strip()
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    def embed_documents(self, progress_callback=None, test_case_service=None) -> Dict[str, Any]:
        """Embed test case documents into vector store with progress tracking"""
        if not self.is_initialized:
            # Try to initialize if not already done
            if not self.initialize():
                return {"success": False, "error": "RAG service initialization failed"}
        
        try:
            # Load documents from database
            documents = self.load_test_case_documents(test_case_service)
            if not documents:
                return {"success": False, "error": "No test cases found in database. Please add some test cases first."}
            
            # Process in smaller batches to avoid payload size limits
            # Start with small batches and adjust based on content size
            total_content_size = sum(len(doc.page_content) for doc in documents)
            avg_doc_size = total_content_size / len(documents) if documents else 0
            
            # Calculate optimal batch size based on content size
            # Target max 20KB per batch to stay well under 36KB limit
            target_batch_size_bytes = 20000
            optimal_batch_size = max(1, min(10, int(target_batch_size_bytes / max(avg_doc_size, 1))))
            
            batch_size = optimal_batch_size
            total_docs = len(documents)
            total_batches = (total_docs + batch_size - 1) // batch_size
            
            embedded_count = 0
            errors = []
            
            logger.info(f"🚀 Optimized embedding: {total_docs} documents in {total_batches} batches")
            logger.info(f"📊 Avg doc size: {avg_doc_size:.0f} chars, batch size: {batch_size}")
            
            for i in range(0, total_docs, batch_size):
                batch_end = min(i + batch_size, total_docs)
                batch_docs = documents[i:batch_end]
                batch_num = i // batch_size + 1
                
                # Calculate batch content size
                batch_content_size = sum(len(doc.page_content) for doc in batch_docs)
                
                logger.info(f"⚡ Processing batch {batch_num}/{total_batches} ({len(batch_docs)} docs, {batch_content_size:,} chars)")
                
                try:
                    # Check if batch is too large and split if necessary
                    if batch_content_size > 25000:  # Conservative limit
                        logger.warning(f"Batch {batch_num} too large ({batch_content_size:,} chars), processing individually")
                        # Process documents one by one
                        for doc in batch_docs:
                            try:
                                self.vectorstore.add_documents([doc])
                                embedded_count += 1
                                time.sleep(0.1)  # Small delay between individual docs
                            except Exception as doc_e:
                                logger.warning(f"Failed to add document {doc.metadata.get('test_case_id', 'unknown')}: {doc_e}")
                                errors.append(f"Document {doc.metadata.get('test_case_id', 'unknown')}: {doc_e}")
                    else:
                        # Add batch at once
                        self.vectorstore.add_documents(batch_docs)
                        embedded_count += len(batch_docs)
                        logger.info(f"✅ Batch {batch_num} completed: {len(batch_docs)} documents embedded")
                    
                    # Delay between batches to avoid rate limiting
                    if batch_end < total_docs:
                        time.sleep(1.0)  # Longer delay to be safe
                        
                except Exception as e:
                    # If batch fails, try individual documents as fallback
                    logger.warning(f"Batch {batch_num} failed ({str(e)[:100]}...), trying individual documents")
                    for doc in batch_docs:
                        try:
                            # Check individual document size
                            doc_size = len(doc.page_content)
                            if doc_size > 30000:  # Very large document
                                logger.warning(f"Document {doc.metadata.get('test_case_id', 'unknown')} too large ({doc_size:,} chars), skipping")
                                errors.append(f"Document {doc.metadata.get('test_case_id', 'unknown')} too large: {doc_size:,} chars")
                                continue
                            
                            self.vectorstore.add_documents([doc])
                            embedded_count += 1
                            time.sleep(0.2)  # Small delay between individual docs
                        except Exception as doc_e:
                            logger.warning(f"Failed to add document {doc.metadata.get('test_case_id', 'unknown')}: {doc_e}")
                            errors.append(f"Document {doc.metadata.get('test_case_id', 'unknown')}: {doc_e}")
                    
                    logger.info(f"⚠️ Batch {batch_num} completed with individual processing")
            
            # Setup retriever and workflow if embedding was successful
            if embedded_count > 0:
                try:
                    self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": Config.RAG_TOP_K})
                    self._setup_workflow()
                    self.is_embedded = True
                    logger.info("RAG workflow setup completed")
                except Exception as setup_e:
                    logger.warning(f"Workflow setup failed: {setup_e}")
            
            return {
                "success": True,
                "embedded_count": embedded_count,
                "total_documents": total_docs,
                "errors": errors,
                "message": f"🚀 Embedding nhanh hoàn tất: {embedded_count}/{total_docs} tài liệu (batch size: {batch_size})"
            }
            
        except Exception as e:
            logger.error(f"Error embedding documents: {e}")
            return {"success": False, "error": str(e)}
    
    def _setup_workflow(self, custom_prompt_template: str = None):
        """Setup the RAG workflow graph"""
        def retrieve_documents_node(state: RAGGraphState) -> RAGGraphState:
            question = state["question"]
            documents = self.retriever.invoke(question)
            return {"documents": documents, "question": question, "generation": "", "final_prompt": "", "context_used": ""}
        
        def generate_response_node(state: RAGGraphState) -> RAGGraphState:
            question = state["question"]
            documents = state["documents"]
            
            # Build context with size optimization
            context_parts = []
            total_context_size = 0
            max_context_size = 15000  # Conservative limit for context
            
            for doc in documents:
                doc_content = doc.page_content
                if total_context_size + len(doc_content) + 2 <= max_context_size:  # +2 for \n\n
                    context_parts.append(doc_content)
                    total_context_size += len(doc_content) + 2
                else:
                    # Try to fit a truncated version
                    remaining_space = max_context_size - total_context_size - 2
                    if remaining_space > 100:  # Only if we have meaningful space left
                        truncated_content = doc_content[:remaining_space-3] + "..."
                        context_parts.append(truncated_content)
                    break
            
            context = "\n\n".join(context_parts)
            
            # Add truncation notice if we had to truncate
            if len(documents) > len(context_parts) or any("..." in part for part in context_parts):
                context += "\n\n[Note: Some context was truncated to fit size limits]"
            
            logger.info(f"Context built: {len(context_parts)}/{len(documents)} documents, {len(context):,} chars")
            
            # Use custom prompt if provided, otherwise use default template
            if custom_prompt_template:
                template = custom_prompt_template
            else:
                # Use default prompt template for test case generation
                template = DEFAULT_RAG_PROMPT_TEMPLATE + "\n\n" + GENERAL_RULES_TEMPLATE
            prompt = ChatPromptTemplate.from_template(template)
            
            # RAG chain
            rag_chain = prompt | self.llm | StrOutputParser()
            
            # Build the final prompt for logging/debugging
            try:
                final_prompt_text = template.format(context=context, question=question)
                
                # Check final prompt size and truncate if necessary
                if len(final_prompt_text) > 30000:  # Very conservative limit
                    logger.warning(f"Final prompt too large ({len(final_prompt_text):,} chars), truncating")
                    # Try to reduce context further
                    max_context_for_prompt = 10000
                    if len(context) > max_context_for_prompt:
                        context = context[:max_context_for_prompt] + "\n\n[Context truncated for prompt size limits]"
                        final_prompt_text = template.format(context=context, question=question)
                
            except Exception as e:
                logger.warning(f"Error formatting prompt: {e}")
                final_prompt_text = f"Error formatting prompt: {str(e)}"
            
            # Invoke with error handling
            try:
                generation = rag_chain.invoke({"context": context, "question": question})
            except Exception as e:
                logger.error(f"Error invoking RAG chain: {e}")
                # Try with even smaller context
                if len(context) > 5000:
                    logger.info("Retrying with smaller context...")
                    context = context[:5000] + "\n\n[Context further reduced due to processing limits]"
                    try:
                        generation = rag_chain.invoke({"context": context, "question": question})
                    except Exception as e2:
                        logger.error(f"Error even with reduced context: {e2}")
                        generation = f"Error generating response: {str(e2)}"
                else:
                    generation = f"Error generating response: {str(e)}"
            
            return {
                "question": question, 
                "documents": documents, 
                "generation": generation,
                "final_prompt": final_prompt_text,
                "context_used": context
            }
        
        # Construct workflow
        workflow = StateGraph(RAGGraphState)
        workflow.add_node("retrieve", retrieve_documents_node)
        workflow.add_node("generate", generate_response_node)
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        self.app = workflow.compile()
    
    def generate_test_cases(self, api_documentation: str, custom_prompt: str = None) -> Dict[str, Any]:
        """Generate test cases using RAG analysis with input size optimization"""
        if not self.is_initialized:
            return {"success": False, "error": "RAG service not initialized"}
        
        if not self.is_embedded:
            return {"success": False, "error": "Documents not embedded. Please embed documents first."}
        
        try:
            # Optimize API documentation input size
            api_doc_optimized = self._optimize_api_documentation(api_documentation)
            
            query = f"Generate test cases for this API documentation:\n\n{api_doc_optimized}"
            
            # Check total query size and truncate if necessary
            if len(query) > 25000:  # Conservative limit for query
                logger.warning(f"Query too large ({len(query):,} chars), truncating to fit limits")
                # Keep the instruction and truncate the API doc part
                instruction = "Generate test cases for this API documentation:\n\n"
                max_api_doc_size = 25000 - len(instruction) - 100  # Leave some buffer
                truncated_api_doc = api_doc_optimized[:max_api_doc_size] + "\n\n[Content truncated due to size limits]"
                query = instruction + truncated_api_doc
            
            inputs = {"question": query}
            
            # If custom prompt is provided, update the workflow
            if custom_prompt:
                logger.info("Using custom prompt for test case generation")
                self._setup_workflow(custom_prompt)
            
            logger.info(f"Generating test cases using RAG... (query size: {len(query):,} chars)")
            result = None
            final_prompt = None
            context_used = None
            
            for s in self.app.stream(inputs):
                if 'generate' in s:
                    result = s['generate']['generation']
                    final_prompt = s['generate'].get('final_prompt', '')
                    context_used = s['generate'].get('context_used', '')
            
            if result:
                logger.info(f"LLM response received: {len(result)} characters")
                logger.debug(f"Raw LLM response: {result[:500]}...")
                
                # Try to parse the generated test cases
                test_cases = self._parse_generated_test_cases(result)
                logger.info(f"Parsed {len(test_cases)} test cases from response")
                
                # Log the final prompt and context for debugging (truncated for logs)
                if final_prompt:
                    logger.info("=" * 80)
                    logger.info("🔍 FINAL PROMPT SENT TO LLM:")
                    logger.info("=" * 80)
                    logger.info(final_prompt[:2000] + "..." if len(final_prompt) > 2000 else final_prompt)
                    logger.info("=" * 80)
                
                if context_used:
                    logger.info("📚 CONTEXT FROM RAG (Similar Test Cases):")
                    logger.info("-" * 60)
                    logger.info(context_used[:1000] + "..." if len(context_used) > 1000 else context_used)
                    logger.info("-" * 60)
                
                logger.info(f"✅ RAG Generation Summary:")
                logger.info(f"   - Test Cases Generated: {len(test_cases)}")
                logger.info(f"   - Custom Prompt Used: {'Yes' if custom_prompt else 'No'}")
                logger.info(f"   - Context Length: {len(context_used) if context_used else 0} characters")
                logger.info(f"   - Final Prompt Length: {len(final_prompt) if final_prompt else 0} characters")
                logger.info(f"   - API Doc Size (optimized): {len(api_doc_optimized):,} characters")
                
                return {
                    "success": True,
                    "generated_cases": test_cases,
                    "raw_response": result,
                    "final_prompt": final_prompt,
                    "context_used": context_used,
                    "message": f"Đã tạo {len(test_cases)} Test Case bằng RAG analysis" + (" (với prompt tùy chỉnh)" if custom_prompt else ""),
                    "used_custom_prompt": bool(custom_prompt),
                    "input_optimized": len(api_documentation) != len(api_doc_optimized)
                }
            else:
                return {"success": False, "error": "No response generated"}
                
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return {"success": False, "error": str(e)}
    
    def create_generation_plan(self, api_documentation: str) -> Dict[str, Any]:
        """
        Step 1 of two-step process: Create generation plan
        Analyzes documentation and creates a plan with combined docs and call breakdown
        """
        try:
            logger.info("🔍 Step 1: Creating generation plan...")
            
            # Initialize planning service if needed
            if not self.planning_service.is_initialized:
                if not self.planning_service.initialize():
                    return {"success": False, "error": "Failed to initialize planning service"}
            
            # Create the plan
            plan_result = self.planning_service.create_generation_plan(api_documentation)
            
            if plan_result["success"]:
                logger.info(f"✅ Generation plan created successfully")
                plan_data = plan_result["plan"]
                
                # Add some additional metadata
                plan_result["step"] = 1
                plan_result["next_step"] = "generation"
                plan_result["plan_summary"] = {
                    "total_calls": plan_data.get("estimated_calls_needed", 0),
                    "total_test_cases": plan_data.get("total_estimated_test_cases", 0),
                    "complexity": plan_data.get("complexity_analysis", {}).get("complexity_level", "unknown"),
                    "focus_areas": [call.get("focus_area", "") for call in plan_data.get("generation_calls", [])]
                }
                
                return plan_result
            else:
                return plan_result
                
        except Exception as e:
            logger.error(f"Error creating generation plan: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_test_cases_with_plan(self, plan: Dict[str, Any], call_id: int, custom_prompt: str = None) -> Dict[str, Any]:
        """
        Step 2 of two-step process: Generate test cases for a specific call using the plan
        Uses RAG with the combined documentation and focused context
        """
        if not self.is_initialized:
            return {"success": False, "error": "RAG service not initialized"}
        
        if not self.is_embedded:
            return {"success": False, "error": "Documents not embedded. Please embed documents first."}
        
        try:
            logger.info(f"🚀 Step 2: Generating test cases for call {call_id}...")
            
            # Get context for this specific call
            context_result = self.planning_service.get_call_context(plan, call_id)
            if not context_result["success"]:
                return context_result
            
            call_context = context_result["context"]
            
            # Create focused query for RAG
            focus_area = call_context.get("focus_area", "")
            content_scope = call_context.get("content_scope", "")
            # Use original documentation for phase 2, not combined
            original_doc = call_context.get("original_documentation", "")
            
            # Build the focused query with original documentation
            focused_query = f"""Generate test cases for: {focus_area}
            
Scope: {content_scope}
Description: {call_context.get("description", "")}

API Documentation (Full):
{original_doc[:20000]}"""  # Use larger limit for original docs
            
            # Check total query size and truncate if necessary
            if len(focused_query) > 25000:
                logger.warning(f"Focused query too large ({len(focused_query):,} chars), truncating")
                # Keep the instruction and truncate the API doc part
                instruction_part = f"""Generate test cases for: {focus_area}
            
Scope: {content_scope}
Description: {call_context.get("description", "")}

API Documentation (Combined):
"""
                max_doc_size = 25000 - len(instruction_part) - 100
                truncated_doc = combined_doc[:max_doc_size] + "\n\n[Content truncated for processing]"
                focused_query = instruction_part + truncated_doc
            
            # Create enhanced prompt for this specific call
            enhanced_prompt = self._create_enhanced_prompt_for_call(call_context, custom_prompt)
            
            inputs = {"question": focused_query}
            
            # Update workflow with enhanced prompt
            if enhanced_prompt:
                logger.info(f"Using enhanced prompt for call {call_id}: {focus_area}")
                self._setup_workflow(enhanced_prompt)
            
            logger.info(f"Generating test cases for call {call_id}/{call_context.get('total_calls', '?')} "
                       f"(focus: {focus_area}, query size: {len(focused_query):,} chars)")
            
            result = None
            final_prompt = None
            context_used = None
            
            # Execute the RAG workflow
            for s in self.app.stream(inputs):
                if 'generate' in s:
                    result = s['generate']['generation']
                    final_prompt = s['generate'].get('final_prompt', '')
                    context_used = s['generate'].get('context_used', '')
            
            if result:
                logger.info(f"LLM response received for call {call_id}: {len(result)} characters")
                
                # Parse the generated test cases
                test_cases = self._parse_generated_test_cases(result)
                logger.info(f"Parsed {len(test_cases)} test cases from call {call_id}")
                
                # Log generation summary
                logger.info(f"✅ Call {call_id} Generation Summary:")
                logger.info(f"   - Focus Area: {focus_area}")
                logger.info(f"   - Test Cases Generated: {len(test_cases)}")
                logger.info(f"   - Estimated: {call_context.get('estimated_test_cases', 'N/A')}")
                logger.info(f"   - Context Length: {len(context_used) if context_used else 0} characters")
                
                return {
                    "success": True,
                    "generated_cases": test_cases,
                    "raw_response": result,
                    "final_prompt": final_prompt,
                    "context_used": context_used,
                    "call_info": {
                        "call_id": call_id,
                        "focus_area": focus_area,
                        "content_scope": content_scope,
                        "estimated_test_cases": call_context.get("estimated_test_cases", 0),
                        "total_calls": call_context.get("total_calls", 0)
                    },
                    "message": f"Đã tạo {len(test_cases)} Test Case cho '{focus_area}' (Call {call_id})",
                    "used_enhanced_prompt": bool(enhanced_prompt),
                    "step": 2
                }
            else:
                return {"success": False, "error": f"No response generated for call {call_id}"}
                
        except Exception as e:
            logger.error(f"Error generating test cases for call {call_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_enhanced_prompt_for_call(self, call_context: Dict[str, Any], custom_prompt: str = None) -> str:
        """Create an enhanced prompt template for a specific generation call"""
        try:
            focus_area = call_context.get("focus_area", "")
            content_scope = call_context.get("content_scope", "")
            description = call_context.get("description", "")
            estimated_cases = call_context.get("estimated_test_cases", 50)
            call_id = call_context.get("call_id", 1)
            total_calls = call_context.get("total_calls", 1)
            
            # Use custom prompt if provided, otherwise enhance the default prompt
            base_prompt = custom_prompt if custom_prompt else (DEFAULT_RAG_PROMPT_TEMPLATE + "\n\n" + GENERAL_RULES_TEMPLATE)
            
            # Add call-specific instructions
            enhanced_prompt = f"""## THÔNG TIN CALL HIỆN TẠI
Call {call_id}/{total_calls} - Tập trung vào: {focus_area}

Mô tả: {description}
Phạm vi nội dung: {content_scope}
Số test case ước tính: {estimated_cases}

## HƯỚNG DẪN ĐẶC BIỆT CHO CALL NÀY
- Tập trung chủ yếu vào các API và business logic liên quan đến: {focus_area}
- Ưu tiên các kịch bản trong phạm vi: {content_scope}
- Tạo khoảng {estimated_cases} test case chất lượng cao
- Đảm bảo coverage toàn diện cho domain này

{base_prompt}

## LƯU Ý QUAN TRỌNG
Đây là call {call_id} trong tổng số {total_calls} calls. Hãy tập trung vào domain "{focus_area}" và tạo test case chi tiết, thực tế cho phạm vi này."""
            
            return enhanced_prompt
            
        except Exception as e:
            logger.warning(f"Error creating enhanced prompt: {e}")
            return custom_prompt or VIETNAMESE_RAG_PROMPT_TEMPLATE
    
    def _optimize_api_documentation(self, api_doc: str) -> str:
        """Optimize API documentation to reduce size while preserving important information"""
        if not api_doc or len(api_doc) <= 15000:  # If already small enough, return as-is
            return api_doc
        
        logger.info(f"Optimizing API documentation (original size: {len(api_doc):,} chars)")
        
        # Split into lines for processing
        lines = api_doc.split('\n')
        optimized_lines = []
        current_size = 0
        max_size = 15000  # Target size
        
        # Prioritize certain types of content
        priority_keywords = [
            'endpoint', 'api', 'method', 'parameter', 'request', 'response', 
            'error', 'status', 'code', 'example', 'authentication', 'authorization',
            'POST', 'GET', 'PUT', 'DELETE', 'PATCH', 'HTTP', 'JSON', 'XML'
        ]
        
        # First pass: include high-priority lines
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in priority_keywords):
                if current_size + len(line) + 1 <= max_size:
                    optimized_lines.append(line)
                    current_size += len(line) + 1
                else:
                    break
        
        # Second pass: fill remaining space with other content
        if current_size < max_size:
            for line in lines:
                if line not in optimized_lines:
                    if current_size + len(line) + 1 <= max_size:
                        optimized_lines.append(line)
                        current_size += len(line) + 1
                    else:
                        break
        
        optimized_doc = '\n'.join(optimized_lines)
        
        if len(optimized_doc) < len(api_doc):
            optimized_doc += "\n\n[Note: Content optimized for processing - some details may be truncated]"
        
        logger.info(f"API documentation optimized: {len(api_doc):,} -> {len(optimized_doc):,} chars")
        return optimized_doc
    
    def _parse_generated_test_cases(self, response: str) -> List[Dict[str, Any]]:
        """Parse generated test cases from LLM response with improved JSON extraction"""
        test_cases = []
        
        try:
            logger.info("Starting to parse LLM response for test cases")
            
            # Try to extract JSON blocks from the response
            import re
            
            # Enhanced JSON patterns with better regex
            patterns = [
                # JSON arrays in code blocks
                (r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', 'JSON array in code block'),
                # Single JSON objects in code blocks  
                (r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', 'JSON object in code block'),
                # JSON arrays without code blocks
                (r'(\[[\s\S]*?\{[\s\S]*?"id"[\s\S]*?\}[\s\S]*?\])', 'JSON array without code block'),
                # Multiple JSON objects (one per line or separated) - more flexible
                (r'(\{[^{}]*?"id"[^{}]*?\})', 'Simple JSON objects'),
            ]
            
            for pattern, description in patterns:
                matches = re.findall(pattern, response, re.DOTALL | re.IGNORECASE)
                logger.info(f"Pattern '{description}' found {len(matches)} matches")
                
                for i, match in enumerate(matches):
                    try:
                        # Clean up the match
                        clean_match = match.strip()
                        
                        # Log the match for debugging
                        logger.debug(f"Attempting to parse match {i+1}: {clean_match[:200]}...")
                        
                        parsed_data = json.loads(clean_match)
                        
                        # Handle both single objects and arrays
                        if isinstance(parsed_data, list):
                            for item in parsed_data:
                                if isinstance(item, dict):
                                    # Try to normalize first, then validate
                                    try:
                                        normalized_item = self._normalize_test_case(item)
                                        if self._validate_test_case_structure(normalized_item):
                                            test_cases.append(normalized_item)
                                            logger.info(f"Successfully parsed test case: {normalized_item.get('id', 'unknown')}")
                                    except Exception as norm_e:
                                        logger.warning(f"Error normalizing test case: {norm_e}")
                        elif isinstance(parsed_data, dict):
                            # Try to normalize first, then validate
                            try:
                                normalized_item = self._normalize_test_case(parsed_data)
                                if self._validate_test_case_structure(normalized_item):
                                    test_cases.append(normalized_item)
                                    logger.info(f"Successfully parsed test case: {normalized_item.get('id', 'unknown')}")
                            except Exception as norm_e:
                                logger.warning(f"Error normalizing test case: {norm_e}")
                                
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error for match {i+1}: {e}")
                        logger.debug(f"Failed match content: {match[:500]}...")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing match {i+1}: {e}")
                        continue
                
                if test_cases:
                    logger.info(f"Successfully extracted {len(test_cases)} test cases using pattern: {description}")
                    break  # Stop if we found valid test cases
            
            # If no JSON blocks found, try to find individual test cases in text format
            if not test_cases:
                logger.info("No valid JSON found, trying text parsing")
                test_cases = self._parse_text_format(response)
            
            # Final validation and cleanup
            valid_test_cases = []
            for tc in test_cases:
                if self._validate_test_case_structure(tc):
                    valid_test_cases.append(tc)
                else:
                    logger.warning(f"Invalid test case structure: {tc}")
            
            logger.info(f"Final parsing result: {len(valid_test_cases)} valid test cases")
            return valid_test_cases
            
        except Exception as e:
            logger.error(f"Error parsing test cases: {e}")
            return []
    
    def _normalize_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize test case structure and ensure all required fields"""
        normalized = {
            'id': str(test_case.get('id', '')).strip(),
            'purpose': str(test_case.get('purpose', '')).strip(),
            'scenerio': str(test_case.get('scenerio', test_case.get('scenario', ''))).strip(),
            'test_data': str(test_case.get('test_data', 'Test data')).strip(),
            'steps': test_case.get('steps', ['Manual test step']),
            'expected': test_case.get('expected', ['Expected result']),
            'note': str(test_case.get('note', 'Generated test case')).strip()
        }
        
        # Ensure steps and expected are lists
        if isinstance(normalized['steps'], str):
            normalized['steps'] = [normalized['steps']]
        if isinstance(normalized['expected'], str):
            normalized['expected'] = [normalized['expected']]
            
        return normalized
    
    def _parse_text_format(self, response: str) -> List[Dict[str, Any]]:
        """Parse test cases from text format when JSON parsing fails"""
        test_cases = []
        lines = response.split('\n')
        current_case = {}
        
        for line in lines:
            line = line.strip()
            
            # Look for test case ID
            if any(pattern in line.lower() for pattern in ['id:', 'test case id:', 'testcase id:']):
                # Save previous case if it exists
                if current_case and len(current_case) >= 3:
                    test_cases.append(self._normalize_test_case(current_case))
                
                # Start new case
                id_value = line.split(':', 1)[-1].strip().strip('"\'')
                current_case = {'id': id_value}
                
            elif current_case:  # Only process if we have started a test case
                if line.startswith('Purpose:') or 'purpose' in line.lower():
                    current_case['purpose'] = line.split(':', 1)[-1].strip().strip('"\'')
                elif any(pattern in line.lower() for pattern in ['scenario:', 'scenerio:']):
                    current_case['scenerio'] = line.split(':', 1)[-1].strip().strip('"\'')
                elif 'test data:' in line.lower():
                    current_case['test_data'] = line.split(':', 1)[-1].strip().strip('"\'')
                elif 'steps:' in line.lower():
                    steps_text = line.split(':', 1)[-1].strip().strip('"\'')
                    current_case['steps'] = [s.strip() for s in steps_text.split('|') if s.strip()]
                elif 'expected:' in line.lower():
                    expected_text = line.split(':', 1)[-1].strip().strip('"\'')
                    current_case['expected'] = [e.strip() for e in expected_text.split('|') if e.strip()]
                elif 'note:' in line.lower():
                    current_case['note'] = line.split(':', 1)[-1].strip().strip('"\'')
        
        # Don't forget the last case
        if current_case and len(current_case) >= 3:
            test_cases.append(self._normalize_test_case(current_case))
        
        logger.info(f"Text parsing extracted {len(test_cases)} test cases")
        return test_cases
    
    def _validate_test_case_structure(self, test_case: Dict[str, Any]) -> bool:
        """Validate test case structure"""
        required_fields = ['id', 'purpose', 'scenerio']
        return all(field in test_case for field in required_fields)
    
    def get_status(self) -> Dict[str, Any]:
        """Get RAG service status"""
        return {
            "initialized": self.is_initialized,
            "embedded": self.is_embedded,
            "client_connected": self.client is not None and self.client.is_ready(),
            "vectorstore_ready": self.vectorstore is not None,
            "retriever_ready": self.retriever is not None,
            "workflow_ready": self.app is not None
        }
    
    def close(self):
        """Close connections"""
        if self.client:
            self.client.close()
            logger.info("Weaviate client closed")
