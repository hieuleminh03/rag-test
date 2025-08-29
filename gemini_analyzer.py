#!/usr/bin/env python3
"""
Gemini AI Integration for Intelligent Excel Analysis
Uses Google's Gemini AI to analyze Excel content and suggest test case extraction patterns
"""

from langchain_google_genai import ChatGoogleGenerativeAI
import google.genai as genai
import json
import os
from typing import Dict, List, Any, Optional
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class GeminiExcelAnalyzer:
    """Uses Gemini AI to intelligently analyze Excel files for test case extraction"""
    
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if self.api_key:
            try:
                # Initialize with langchain-google-genai
                self.model = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash",
                    google_api_key=self.api_key,
                    temperature=0.1
                )
                self.available = True
                logger.info("Gemini AI analyzer initialized successfully with langchain-google-genai")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.available = False
        else:
            self.available = False
            logger.warning("GEMINI_API_KEY or GOOGLE_API_KEY not found in environment variables")
    
    def analyze_excel_content(self, sheet_data: Dict[str, Any], sheet_name: str) -> Dict[str, Any]:
        """Analyze Excel sheet content using Gemini AI"""
        if not self.available:
            return {'error': 'Gemini API key not configured'}
        
        try:
            # Prepare data for analysis - handle both 'preview' and 'data' formats
            preview_data = sheet_data.get('preview', [])
            if not preview_data:
                # Try 'data' format and take first 15 rows as preview
                full_data = sheet_data.get('data', [])
                if full_data:
                    preview_data = full_data[:15]
                else:
                    return {'error': 'No preview data available'}
            
            # Create prompt for Gemini
            prompt = self._create_analysis_prompt(preview_data, sheet_name)
            
            # Get AI analysis
            response = self.model.invoke(prompt)
            
            # Parse response
            analysis = self._parse_gemini_response(response.content)
            
            return {
                'success': True,
                'analysis': analysis,
                'sheet_name': sheet_name,
                'ai_powered': True
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini analysis: {e}")
            return {'error': f'Gemini analysis failed: {str(e)}'}
    
    def generate_extraction_logic(self, sheet_data: Dict[str, Any], sheet_name: str) -> Dict[str, Any]:
        """Generate complete extraction logic for test cases with merged cell handling"""
        if not self.available:
            return {'error': 'Gemini API key not configured'}
        
        try:
            # Prepare data for analysis - handle both 'preview' and 'data' formats
            preview_data = sheet_data.get('data', [])
            if not preview_data:
                preview_data = sheet_data.get('preview', [])
            if not preview_data:
                return {'error': 'No data available for extraction logic'}
            
            # Take up to 50 rows for analysis
            preview_data = preview_data[:50]
            
            # Create extraction logic prompt
            prompt = self._create_extraction_logic_prompt(preview_data, sheet_name)
            
            # Get AI analysis
            response = self.model.invoke(prompt)
            
            # Parse response
            extraction_logic = self._parse_extraction_logic_response(response.content)
            
            return {
                'success': True,
                'extraction_logic': extraction_logic,
                'sheet_name': sheet_name,
                'ai_powered': True
            }
            
        except Exception as e:
            logger.error(f"Error generating extraction logic: {e}")
            return {'error': f'Extraction logic generation failed: {str(e)}'}
    
    def suggest_field_mapping(self, headers: List[str], sample_data: List[List[str]]) -> Dict[str, Any]:
        """Use Gemini to suggest field mapping for test cases"""
        if not self.available:
            return {'error': 'Gemini API key not configured'}
        
        try:
            prompt = self._create_mapping_prompt(headers, sample_data)
            response = self.model.invoke(prompt)
            
            mapping = self._parse_mapping_response(response.content)
            
            return {
                'success': True,
                'suggested_mapping': mapping,
                'confidence': mapping.get('confidence', 0.5),
                'ai_powered': True
            }
            
        except Exception as e:
            logger.error(f"Error in Gemini field mapping: {e}")
            return {'error': f'Field mapping failed: {str(e)}'}
    
    def analyze_test_case_structure(self, excel_data: List[List[str]]) -> Dict[str, Any]:
        """Analyze the structure of potential test cases using AI"""
        if not self.available:
            return {'error': 'Gemini API key not configured'}
        
        try:
            prompt = self._create_structure_analysis_prompt(excel_data)
            response = self.model.invoke(prompt)
            
            structure = self._parse_structure_response(response.content)
            
            return {
                'success': True,
                'structure_analysis': structure,
                'ai_powered': True
            }
            
        except Exception as e:
            logger.error(f"Error in structure analysis: {e}")
            return {'error': f'Structure analysis failed: {str(e)}'}
    
    def _create_analysis_prompt(self, preview_data: List[List[str]], sheet_name: str) -> str:
        """Create prompt for general Excel analysis"""
        data_sample = "\n".join(["\t".join(str(cell) for cell in row[:10]) for row in preview_data[:15]])
        
        return f"""
Analyze this Excel sheet data and determine if it contains actual TEST CASES (not cover pages, introductions, or summaries).

Sheet Name: {sheet_name}
Data Sample:
{data_sample}

IMPORTANT: Only identify as test sheet if it contains ACTUAL TEST CASE DATA with:
- Test case IDs (like TC_001, HM_1, etc.)
- Test steps or procedures
- Expected results
- Multiple rows of test data

DO NOT identify these as test sheets:
- Cover pages (Trang bìa)
- Introduction pages (Giới thiệu) 
- Summary pages (Tổng hợp)
- Documentation or reference material
- Single-row headers without test data

Please analyze and provide a JSON response with:
1. is_test_sheet: boolean - TRUE only if contains actual test case data rows
2. confidence: float (0-1) - confidence level in the assessment
3. test_case_indicators: list - specific evidence of test cases found
4. suggested_header_row: int - which row likely contains headers (0-based)
5. suggested_data_start_row: int - which row test case data starts
6. potential_fields: object - mapping of detected columns to test case fields
7. data_quality: string - assessment of data quality
8. extraction_recommendations: list - specific recommendations for data extraction

Respond only with valid JSON.
"""
    
    def _create_mapping_prompt(self, headers: List[str], sample_data: List[List[str]]) -> str:
        """Create prompt for field mapping suggestions"""
        headers_str = ", ".join(f"{i}: {header}" for i, header in enumerate(headers))
        sample_str = "\n".join(["\t".join(str(cell) for cell in row[:len(headers)]) for row in sample_data[:5]])
        
        return f"""
Analyze these Excel headers and sample data to suggest mapping to test case fields.

Headers (index: value):
{headers_str}

Sample Data:
{sample_str}

Map to these test case fields:
- id: Test case identifier
- purpose: Test case purpose/objective
- scenerio: Test scenario description
- test_data: Test data or input
- steps: Test execution steps
- expected: Expected results
- note: Additional notes

Provide JSON response with:
1. field_mapping: object mapping test case fields to column indices
2. confidence: float (0-1) - overall confidence in mapping
3. field_confidence: object - confidence for each field mapping
4. suggestions: list - additional suggestions for improvement
5. data_format_notes: list - notes about data format in each column

Respond only with valid JSON.
"""
    
    def _create_structure_analysis_prompt(self, excel_data: List[List[str]]) -> str:
        """Create prompt for structure analysis"""
        data_sample = "\n".join(["\t".join(str(cell) for cell in row[:10]) for row in excel_data[:20]])
        
        return f"""
Analyze this Excel data structure to understand the test case organization.

Data Sample:
{data_sample}

Analyze and provide JSON response with:
1. data_organization: string - how the data is organized
2. header_detection: object - detected headers and their positions
3. data_patterns: list - patterns found in the data
4. test_case_boundaries: list - how individual test cases are separated
5. data_quality_issues: list - any quality issues found
6. extraction_strategy: object - recommended extraction approach
7. special_formatting: list - any special formatting or merged cells detected

Respond only with valid JSON.
"""
    
    def _create_extraction_logic_prompt(self, preview_data: List[List[str]], sheet_name: str) -> str:
        """Create prompt for generating extraction logic with merged cell handling"""
        data_sample = "\n".join([f"Row {i}: " + "\t".join(str(cell) for cell in row[:15]) for i, row in enumerate(preview_data[:30])])
        
        return f"""
Analyze this Excel sheet data and generate complete extraction logic for test cases with merged cell handling.

Sheet Name: {sheet_name}
Data Sample (first 30 rows):
{data_sample}

CRITICAL: Only proceed if this sheet contains ACTUAL TEST CASE DATA. Look for:
- Multiple rows with test case IDs (like HM_1, TC_001, etc.)
- Test steps or procedures in cells
- Expected results or outcomes
- Structured test case data (not just headers or documentation)

Target JSON format for each test case:
{{
  "id": "check-blacklist_1",
  "purpose": "Kiểm tra update DB", 
  "scenerio": "TH status = ACTIVE",
  "test_data": "DB loan_application",
  "steps": ["1. Thực hiện call API"],
  "expected": ["1. Thực hiện update DB theo kafka trả về - status = ACTIVE - substatus = ACTIVE"],
  "note": ""
}}

IMPORTANT REQUIREMENTS:
1. ONLY extract if you find actual test case rows with IDs and test data
2. Handle merged cells in purpose column (2+ rows may share same purpose)
3. Each ID = each test case = each row (guaranteed)
4. Some cells may be empty - use smart data sharing
5. Detect which columns contain: id, purpose, scenerio, test_data, steps, expected, note
6. Generate logic to handle merged cells and data propagation
7. If no test cases found, set extraction_config to empty

Provide JSON response with:
1. extraction_config: Complete configuration for extraction
2. column_mapping: Which column index maps to which field
3. merged_cell_logic: How to handle merged cells and data sharing
4. data_processing_rules: Rules for handling empty cells and data propagation
5. row_processing_strategy: How to process each row and extract test cases
6. validation_rules: How to validate extracted test cases
7. sample_extraction: Show 2-3 sample extractions from the provided data

Example extraction_config structure:
{{
  "header_row": 0,
  "data_start_row": 1,
  "column_mapping": {{
    "id": 0,
    "purpose": 1, 
    "scenerio": 2,
    "test_data": 3,
    "steps": 4,
    "expected": 5,
    "note": 6
  }},
  "merged_cell_handling": {{
    "purpose_column_merged": true,
    "propagate_down": ["purpose", "test_data"],
    "merge_detection_strategy": "empty_cell_indicates_merge"
  }},
  "data_processing": {{
    "empty_cell_strategy": "inherit_from_above",
    "list_field_separators": ["\\n", ";", "•"],
    "text_cleaning_rules": ["trim_whitespace", "remove_empty_lines"]
  }}
}}

Respond only with valid JSON.
"""
    
    def _parse_gemini_response(self, response_text: str) -> Dict[str, Any]:
        """Parse Gemini response and extract JSON"""
        try:
            # Clean response text
            cleaned = response_text.strip()
            
            # Try to extract JSON from response
            if '```json' in cleaned:
                start = cleaned.find('```json') + 7
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            elif '```' in cleaned:
                start = cleaned.find('```') + 3
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            
            # Parse JSON
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}")
            return {
                'is_test_sheet': False,
                'confidence': 0.0,
                'error': 'Failed to parse AI response',
                'raw_response': response_text[:500]
            }
    
    def _parse_mapping_response(self, response_text: str) -> Dict[str, Any]:
        """Parse field mapping response"""
        try:
            cleaned = response_text.strip()
            
            if '```json' in cleaned:
                start = cleaned.find('```json') + 7
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            elif '```' in cleaned:
                start = cleaned.find('```') + 3
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse mapping response: {e}")
            return {
                'field_mapping': {},
                'confidence': 0.0,
                'error': 'Failed to parse mapping response'
            }
    
    def _parse_structure_response(self, response_text: str) -> Dict[str, Any]:
        """Parse structure analysis response"""
        try:
            cleaned = response_text.strip()
            
            if '```json' in cleaned:
                start = cleaned.find('```json') + 7
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            elif '```' in cleaned:
                start = cleaned.find('```') + 3
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse structure response: {e}")
            return {
                'data_organization': 'unknown',
                'error': 'Failed to parse structure response'
            }
    
    def _parse_extraction_logic_response(self, response_text: str) -> Dict[str, Any]:
        """Parse extraction logic response"""
        try:
            cleaned = response_text.strip()
            
            if '```json' in cleaned:
                start = cleaned.find('```json') + 7
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            elif '```' in cleaned:
                start = cleaned.find('```') + 3
                end = cleaned.find('```', start)
                cleaned = cleaned[start:end].strip()
            
            return json.loads(cleaned)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse extraction logic response: {e}")
            return {
                'extraction_config': {},
                'error': 'Failed to parse extraction logic response'
            }
    
    def enhance_extraction_config(self, basic_config: Dict[str, Any], ai_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance extraction configuration with AI insights"""
        enhanced_config = basic_config.copy()
        
        if ai_analysis.get('success') and 'analysis' in ai_analysis:
            analysis = ai_analysis['analysis']
            
            # Update header row if AI suggests different
            if 'suggested_header_row' in analysis:
                enhanced_config['header_row'] = analysis['suggested_header_row']
            
            # Update data start row
            if 'suggested_data_start_row' in analysis:
                enhanced_config['start_row'] = analysis['suggested_data_start_row']
            
            # Add AI-suggested field mapping
            if 'potential_fields' in analysis:
                enhanced_config['ai_field_mapping'] = analysis['potential_fields']
            
            # Add extraction recommendations
            if 'extraction_recommendations' in analysis:
                enhanced_config['ai_recommendations'] = analysis['extraction_recommendations']
            
            enhanced_config['ai_enhanced'] = True
            enhanced_config['ai_confidence'] = analysis.get('confidence', 0.5)
        
        return enhanced_config