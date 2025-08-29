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
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
            logger.info("LLM initialized")
            
            # Check if data is already embedded
            self._check_embedded_status()
            
            if self.is_embedded:
                self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
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
    
    def load_test_case_documents(self, file_path: str = None) -> List[Document]:
        """Load JSON test case data and convert to documents"""
        if file_path is None:
            file_path = str(Config.TEST_DATA_FILE)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            documents = []
            for item in json_data:
                # Create a comprehensive text representation of each test case
                # Avoid using "id" in content to prevent Weaviate conflicts
                test_case_id = item.get('id', '')
                content = f"""
Test Case Identifier: {test_case_id}
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
                        'test_case_id': test_case_id,
                        'purpose': item.get('purpose', ''),
                        'scenario': item.get('scenerio', ''),
                        'test_data': item.get('test_data', ''),
                        'source': 'test_cases'
                    }
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} test case documents")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading test case documents: {e}")
            return []
    
    def embed_documents(self, progress_callback=None) -> Dict[str, Any]:
        """Embed test case documents into vector store with progress tracking"""
        if not self.is_initialized:
            # Try to initialize if not already done
            if not self.initialize():
                return {"success": False, "error": "RAG service initialization failed"}
        
        try:
            # Load documents
            documents = self.load_test_case_documents()
            if not documents:
                return {"success": False, "error": "No documents to embed"}
            
            # Process in smaller batches to avoid quota issues
            batch_size = 2  # Even smaller batches
            total_docs = len(documents)
            total_batches = (total_docs + batch_size - 1) // batch_size
            
            embedded_count = 0
            errors = []
            
            logger.info(f"Starting to embed {total_docs} documents in {total_batches} batches")
            
            for i in range(0, total_docs, batch_size):
                batch_end = min(i + batch_size, total_docs)
                batch_docs = documents[i:batch_end]
                batch_num = i // batch_size + 1
                
                logger.info(f"Processing batch {batch_num}/{total_batches}")
                
                try:
                    # Add documents one by one to avoid batch issues
                    for doc in batch_docs:
                        try:
                            self.vectorstore.add_documents([doc])
                            embedded_count += 1
                            time.sleep(1)  # Small delay between documents
                        except Exception as doc_e:
                            logger.warning(f"Failed to add document: {doc_e}")
                            errors.append(f"Document error: {doc_e}")
                    
                    logger.info(f"✅ Batch {batch_num} completed successfully")
                    
                    # Add delay between batches to respect rate limits
                    if batch_end < total_docs:
                        time.sleep(3)
                        
                except Exception as e:
                    error_msg = f"Batch {batch_num} error: {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Setup retriever and workflow if embedding was successful
            if embedded_count > 0:
                try:
                    self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 5})
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
                "message": f"Đã embedding thành công {embedded_count}/{total_docs} tài liệu"
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
            
            # Complete context
            context = "\n\n".join([doc.page_content for doc in documents])
            
            # Use custom prompt if provided, otherwise use default
            if custom_prompt_template:
                template = custom_prompt_template
            else:
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
            
            # Complete context
            context = "\n\n".join([doc.page_content for doc in documents])
            
            # RAG chain
            rag_chain = prompt | self.llm | StrOutputParser()
            
            # Build the final prompt for logging/debugging
            final_prompt_text = template.format(context=context, question=question)
            
            # Invoke
            generation = rag_chain.invoke({"context": context, "question": question})
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
        """Generate test cases using RAG analysis"""
        if not self.is_initialized:
            return {"success": False, "error": "RAG service not initialized"}
        
        if not self.is_embedded:
            return {"success": False, "error": "Documents not embedded. Please embed documents first."}
        
        try:
            query = f"Generate test cases for this API documentation:\n\n{api_documentation}"
            inputs = {"question": query}
            
            # If custom prompt is provided, update the workflow
            if custom_prompt:
                logger.info("Using custom prompt for test case generation")
                self._setup_workflow(custom_prompt)
            
            logger.info("Generating test cases using RAG...")
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
                
                # Log the final prompt and context for debugging
                if final_prompt:
                    logger.info("=" * 80)
                    logger.info("🔍 FINAL PROMPT SENT TO LLM:")
                    logger.info("=" * 80)
                    logger.info(final_prompt)
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
                
                return {
                    "success": True,
                    "generated_cases": test_cases,
                    "raw_response": result,
                    "final_prompt": final_prompt,
                    "context_used": context_used,
                    "message": f"Đã tạo {len(test_cases)} Test Case bằng RAG analysis" + (" (với prompt tùy chỉnh)" if custom_prompt else ""),
                    "used_custom_prompt": bool(custom_prompt)
                }
            else:
                return {"success": False, "error": "No response generated"}
                
        except Exception as e:
            logger.error(f"Error generating test cases: {e}")
            return {"success": False, "error": str(e)}
    
    def _parse_generated_test_cases(self, response: str) -> List[Dict[str, Any]]:
        """Parse generated test cases from LLM response"""
        test_cases = []
        
        try:
            logger.info("Starting to parse LLM response for test cases")
            
            # Try to extract JSON blocks from the response
            import re
            
            # Try multiple JSON patterns
            patterns = [
                r'```json\s*(\[.*?\])\s*```',  # JSON arrays
                r'```json\s*(\{.*?\})\s*```',  # Standard JSON blocks
                r'```\s*(\[.*?\])\s*```',      # JSON arrays without 'json' label
                r'```\s*(\{.*?\})\s*```',      # JSON blocks without 'json' label
                r'(\{[^{}]*"id"[^{}]*\})',     # Simple JSON objects with id field
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, response, re.DOTALL)
                logger.info(f"Pattern '{pattern}' found {len(matches)} matches")
                
                for match in matches:
                    try:
                        parsed_data = json.loads(match)
                        
                        # Handle both single objects and arrays
                        if isinstance(parsed_data, list):
                            for item in parsed_data:
                                if self._validate_test_case_structure(item):
                                    test_cases.append(item)
                                    logger.info(f"Successfully parsed test case: {item.get('id', 'unknown')}")
                        elif isinstance(parsed_data, dict):
                            if self._validate_test_case_structure(parsed_data):
                                test_cases.append(parsed_data)
                                logger.info(f"Successfully parsed test case: {parsed_data.get('id', 'unknown')}")
                    except json.JSONDecodeError as e:
                        logger.warning(f"JSON decode error for match: {e}")
                        continue
                
                if test_cases:
                    break  # Stop if we found valid test cases
            
            # If no JSON blocks found, try to find individual test cases in text format
            if not test_cases:
                logger.info("No JSON found, trying text parsing")
                lines = response.split('\n')
                current_case = {}
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('ID:') or line.startswith('Test Case ID:') or 'id":' in line.lower():
                        if current_case and len(current_case) > 2:
                            # Add default values for missing fields
                            current_case.setdefault('steps', ['Manual test step'])
                            current_case.setdefault('expected', ['Expected result'])
                            current_case.setdefault('test_data', 'Test data')
                            current_case.setdefault('note', 'Generated test case')
                            test_cases.append(current_case)
                        current_case = {'id': line.split(':', 1)[-1].strip().strip('"')}
                    elif line.startswith('Purpose:') or 'purpose":' in line.lower():
                        current_case['purpose'] = line.split(':', 1)[-1].strip().strip('"')
                    elif line.startswith('Scenario:') or line.startswith('Scenerio:') or 'scenerio":' in line.lower():
                        current_case['scenerio'] = line.split(':', 1)[-1].strip().strip('"')
                
                if current_case and len(current_case) > 2:
                    current_case.setdefault('steps', ['Manual test step'])
                    current_case.setdefault('expected', ['Expected result'])
                    current_case.setdefault('test_data', 'Test data')
                    current_case.setdefault('note', 'Generated test case')
                    test_cases.append(current_case)
            
            logger.info(f"Final parsing result: {len(test_cases)} test cases")
            
        except Exception as e:
            logger.error(f"Error parsing test cases: {e}")
        
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
