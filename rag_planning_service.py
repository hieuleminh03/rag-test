#!/usr/bin/env python3
"""
RAG Planning Service for Two-Step Test Case Generation
Handles the planning phase that breaks down documentation into manageable chunks
"""

import json
import logging
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

logger = logging.getLogger(__name__)

class RAGPlanningService:
    """Service for planning test case generation in two steps"""
    
    def __init__(self):
        self.llm = None
        self.is_initialized = False
    
    def initialize(self):
        """Initialize the planning service"""
        try:
            self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0)
            self.is_initialized = True
            logger.info("RAG Planning Service initialized")
            return True
        except Exception as e:
            logger.error(f"Error initializing RAG Planning Service: {e}")
            return False
    
    def create_generation_plan(self, api_documentation: str) -> Dict[str, Any]:
        """
        Step 1: Create a plan for test case generation
        Analyzes the documentation and creates a combined version with generation strategy
        """
        if not self.is_initialized:
            if not self.initialize():
                return {"success": False, "error": "Failed to initialize planning service"}
        
        try:
            # Optimize input size for planning step
            optimized_doc = self._optimize_documentation_for_planning(api_documentation)
            
            # Planning prompt template
            planning_prompt = """Bạn là chuyên gia phân tích API để lập kế hoạch tạo test case. Nhiệm vụ của bạn là phân tích tài liệu API và tạo kế hoạch chi tiết.

## TÀI LIỆU API CẦN PHÂN TÍCH:
{api_documentation}

## YÊU CẦU PHÂN TÍCH:

1. **Tạo phiên bản kết hợp của tài liệu** - loại bỏ thông tin trùng lặp, tổng hợp các phần liên quan
2. **Ước tính số lượng calls cần thiết** - dựa trên độ phức tạp và số lượng endpoint/business flow
3. **Xác định nội dung cho từng call** - chia nhỏ thành các phần logic có thể xử lý độc lập

## QUY TẮC CHIA NHỎ:
- API với 30+ bước → khoảng 200-250 test case → chia thành ~5 calls
- Mỗi call nên tập trung vào 1 business domain hoặc nhóm chức năng liên quan
- Ví dụ nội dung call: "service flag, customer remain order", "payment processing", "error handling", v.v.

## ĐỊNH DẠNG ĐẦU RA (JSON):
```json
{{
  "combined_documentation": "Phiên bản tài liệu đã được tối ưu, loại bỏ trùng lặp, tổng hợp thông tin",
  "estimated_calls_needed": 5,
  "generation_calls": [
    {{
      "call_id": 1,
      "focus_area": "Authentication and User Management",
      "description": "Tập trung vào các API liên quan đến xác thực, đăng nhập, quản lý user",
      "content_scope": "login, logout, token validation, user profile APIs",
      "estimated_test_cases": 40
    }},
    {{
      "call_id": 2,
      "focus_area": "Payment Processing",
      "description": "Các API thanh toán, xử lý giao dịch, refund",
      "content_scope": "payment APIs, transaction processing, refund logic",
      "estimated_test_cases": 50
    }}
  ],
  "total_estimated_test_cases": 250,
  "complexity_analysis": {{
    "total_endpoints": 15,
    "business_flows": 8,
    "complexity_level": "high",
    "reasoning": "Lý do đánh giá độ phức tạp và cách chia nhỏ"
  }}
}}
```

Hãy phân tích tài liệu và trả về kế hoạch chi tiết theo định dạng JSON trên."""

            prompt_template = ChatPromptTemplate.from_template(planning_prompt)
            chain = prompt_template | self.llm | StrOutputParser()
            
            logger.info(f"Creating generation plan for documentation (original: {len(api_documentation):,} chars, optimized: {len(optimized_doc):,} chars)")
            
            # Generate the plan
            result = chain.invoke({"api_documentation": optimized_doc})
            
            # Parse the JSON response
            try:
                # Extract JSON from the response
                json_start = result.find('{')
                json_end = result.rfind('}') + 1
                
                if json_start != -1 and json_end > json_start:
                    json_str = result[json_start:json_end]
                    plan_data = json.loads(json_str)
                    
                    # Validate the plan structure
                    if self._validate_plan_structure(plan_data):
                        logger.info(f"✅ Generation plan created: {plan_data.get('estimated_calls_needed', 0)} calls, "
                                  f"{plan_data.get('total_estimated_test_cases', 0)} estimated test cases")
                        
                        # Store original documentation for phase 2
                        plan_data["original_documentation"] = api_documentation
                        
                        return {
                            "success": True,
                            "plan": plan_data,
                            "raw_response": result,
                            "message": f"Kế hoạch tạo test case đã được lập: {plan_data.get('estimated_calls_needed', 0)} calls"
                        }
                    else:
                        logger.warning("Invalid plan structure returned")
                        return {"success": False, "error": "Invalid plan structure returned from LLM"}
                else:
                    logger.warning("No valid JSON found in response")
                    return {"success": False, "error": "No valid JSON found in planning response"}
                    
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing error: {e}")
                return {"success": False, "error": f"Failed to parse planning response: {str(e)}"}
                
        except Exception as e:
            logger.error(f"Error creating generation plan: {e}")
            return {"success": False, "error": str(e)}
    
    def _validate_plan_structure(self, plan_data: Dict[str, Any]) -> bool:
        """Validate the structure of the generated plan"""
        required_fields = [
            "combined_documentation",
            "estimated_calls_needed", 
            "generation_calls",
            "total_estimated_test_cases"
        ]
        
        # Check required top-level fields
        for field in required_fields:
            if field not in plan_data:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Validate generation_calls structure
        calls = plan_data.get("generation_calls", [])
        if not isinstance(calls, list) or len(calls) == 0:
            logger.warning("generation_calls must be a non-empty list")
            return False
        
        # Validate each call structure
        required_call_fields = ["call_id", "focus_area", "description", "content_scope"]
        for call in calls:
            if not isinstance(call, dict):
                logger.warning("Each generation call must be a dictionary")
                return False
            
            for field in required_call_fields:
                if field not in call:
                    logger.warning(f"Missing required call field: {field}")
                    return False
        
        return True
    
    def get_call_context(self, plan: Dict[str, Any], call_id: int) -> Dict[str, Any]:
        """Get the context for a specific generation call"""
        try:
            generation_calls = plan.get("generation_calls", [])
            
            # Find the specific call
            target_call = None
            for call in generation_calls:
                if call.get("call_id") == call_id:
                    target_call = call
                    break
            
            if not target_call:
                return {"success": False, "error": f"Call ID {call_id} not found in plan"}
            
            # Get the combined documentation
            combined_doc = plan.get("combined_documentation", "")
            original_doc = plan.get("original_documentation", "")
            
            # Create focused context for this call
            call_context = {
                "combined_documentation": combined_doc,
                "original_documentation": original_doc,  # Add original docs for phase 2
                "focus_area": target_call.get("focus_area", ""),
                "description": target_call.get("description", ""),
                "content_scope": target_call.get("content_scope", ""),
                "estimated_test_cases": target_call.get("estimated_test_cases", 50),
                "call_id": call_id,
                "total_calls": len(generation_calls)
            }
            
            return {
                "success": True,
                "context": call_context,
                "message": f"Context prepared for call {call_id}: {target_call.get('focus_area', '')}"
            }
            
        except Exception as e:
            logger.error(f"Error getting call context: {e}")
            return {"success": False, "error": str(e)}
    
    def _optimize_documentation_for_planning(self, api_doc: str) -> str:
        """Optimize API documentation size for the planning step"""
        if not api_doc or len(api_doc) <= 25000:  # Increased threshold
            return api_doc
        
        logger.info(f"Optimizing documentation for planning (original size: {len(api_doc):,} chars)")
        
        # Split into sections and lines for better processing
        sections = api_doc.split('\n\n')  # Split by paragraphs/sections
        optimized_sections = []
        current_size = 0
        max_size = 25000  # Increased target size for planning
        
        # Prioritize certain types of content for planning
        priority_keywords = [
            'endpoint', 'api', 'method', 'parameter', 'request', 'response', 
            'error', 'status', 'code', 'example', 'authentication', 'authorization',
            'POST', 'GET', 'PUT', 'DELETE', 'PATCH', 'HTTP', 'JSON', 'XML',
            'business', 'rule', 'flow', 'process', 'validation', 'logic',
            '##', '###', '####', '#',  # Headers
            'overview', 'description', 'summary', 'introduction'
        ]
        
        # First pass: include high-priority sections
        for section in sections:
            if not section.strip():
                continue
                
            section_lower = section.lower()
            is_priority = any(keyword in section_lower for keyword in priority_keywords)
            
            if is_priority and current_size + len(section) + 2 <= max_size:
                optimized_sections.append(section)
                current_size += len(section) + 2
        
        # Second pass: fill remaining space with other sections (but be more selective)
        remaining_space = max_size - current_size
        if remaining_space > 1000:  # Only if we have significant space left
            for section in sections:
                if section not in optimized_sections and section.strip():
                    # Skip very long sections that might be examples or logs
                    if len(section) > 2000:
                        continue
                        
                    if current_size + len(section) + 2 <= max_size:
                        optimized_sections.append(section)
                        current_size += len(section) + 2
                    else:
                        # Try to include a truncated version if it's important
                        if any(keyword in section.lower() for keyword in ['endpoint', 'api', 'method']):
                            truncated = section[:remaining_space-100] + "..."
                            optimized_sections.append(truncated)
                        break
        
        optimized_doc = '\n\n'.join(optimized_sections)
        
        if len(optimized_doc) < len(api_doc):
            optimized_doc += "\n\n[Note: Documentation optimized for planning - detailed examples and long sections may be truncated]"
        
        logger.info(f"Documentation optimized for planning: {len(api_doc):,} -> {len(optimized_doc):,} chars")
        return optimized_doc