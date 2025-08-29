#!/usr/bin/env python3
"""
Excel Processing Utilities for Data Cleaning
Handles multiple Excel files with smart cell selection and extraction
"""

import json
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Try to import Excel libraries, fallback if not available
try:
    import pandas as pd
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    EXCEL_AVAILABLE = False
    logger.warning("Excel libraries (pandas, openpyxl) not available. Using fallback mode.")

# Import fallback reader and template extractor (AI components removed)
from simple_excel_reader import SimpleExcelReader
from template_extractor import TemplateTestCaseExtractor

class ExcelProcessor:
    """Handles Excel file processing and data extraction"""
    
    def __init__(self):
        self.supported_extensions = ['.xlsx', '.xls', '.ods']
        self.selection_configs = {}  # Store selection configurations
        self.fallback_reader = SimpleExcelReader()  # Fallback when pandas not available
        self.template_extractor = TemplateTestCaseExtractor()  # Template-based extraction
    
    def get_excel_info(self, file_path: str) -> Dict[str, Any]:
        """Get basic information about an Excel file"""
        if not EXCEL_AVAILABLE:
            # Use fallback reader
            logger.info("Using fallback Excel reader")
            return self.fallback_reader.read_excel_basic_info(file_path)
        
        try:
            # Read all sheets with pandas (supports .xlsx, .xls, .ods)
            if file_path.lower().endswith('.ods'):
                # For ODS files, use odf engine
                excel_file = pd.ExcelFile(file_path, engine='odf')
            else:
                # For Excel files, use default engine
                excel_file = pd.ExcelFile(file_path)
            
            sheets_info = {}
            
            for sheet_name in excel_file.sheet_names:
                if file_path.lower().endswith('.ods'):
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='odf')
                else:
                    df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                
                sheets_info[sheet_name] = {
                    'rows': len(df),
                    'cols': len(df.columns),
                    'has_data': not df.empty,
                    'preview': self._get_sheet_preview(df)
                }
            
            return {
                'filename': os.path.basename(file_path),
                'sheets': sheets_info,
                'total_sheets': len(excel_file.sheet_names)
            }
        except Exception as e:
            logger.error(f"Error reading Excel file {file_path}: {e}")
            return {'error': str(e)}
    
    def _get_sheet_preview(self, df, max_rows: int = 10, max_cols: int = 10) -> List[List[str]]:
        """Get a preview of sheet data"""
        if not EXCEL_AVAILABLE:
            return [['Preview not available without pandas']]
        preview_df = df.iloc[:max_rows, :max_cols]
        return preview_df.fillna('').astype(str).values.tolist()
    
    def get_sheet_data(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """Get full data for a specific sheet"""
        if not EXCEL_AVAILABLE:
            return {'error': 'Full sheet data not available without pandas. Please install: pip install pandas openpyxl'}
        
        try:
            # Handle ODS files with proper engine
            if file_path.lower().endswith('.ods'):
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='odf')
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            return {
                'data': df.fillna('').astype(str).values.tolist(),
                'rows': len(df),
                'cols': len(df.columns)
            }
        except Exception as e:
            logger.error(f"Error reading sheet {sheet_name} from {file_path}: {e}")
            return {'error': str(e)}
    
    def save_selection_config(self, config_name: str, config: Dict[str, Any]) -> bool:
        """Save a selection configuration for reuse"""
        try:
            config_file = f"selection_configs/{config_name}.json"
            os.makedirs("selection_configs", exist_ok=True)
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            self.selection_configs[config_name] = config
            return True
        except Exception as e:
            logger.error(f"Error saving selection config: {e}")
            return False
    
    def load_selection_config(self, config_name: str) -> Optional[Dict[str, Any]]:
        """Load a saved selection configuration"""
        try:
            config_file = f"selection_configs/{config_name}.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.selection_configs[config_name] = config
                return config
            return None
        except Exception as e:
            logger.error(f"Error loading selection config: {e}")
            return None
    
    def get_available_configs(self) -> List[str]:
        """Get list of available selection configurations"""
        config_dir = "selection_configs"
        if not os.path.exists(config_dir):
            return []
        
        configs = []
        for file in os.listdir(config_dir):
            if file.endswith('.json'):
                configs.append(file[:-5])  # Remove .json extension
        return configs
    
    def extract_data_with_selection(self, file_path: str, selection_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data based on selection configuration"""
        if not EXCEL_AVAILABLE:
            logger.error("Data extraction not available without pandas")
            return []
        
        try:
            extracted_data = []
            
            for sheet_config in selection_config.get('sheets', []):
                sheet_name = sheet_config['name']
                selections = sheet_config.get('selections', [])
                
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
                
                for selection in selections:
                    data = self._extract_selection_data(df, selection)
                    if data:
                        extracted_data.extend(data)
            
            return extracted_data
        except Exception as e:
            logger.error(f"Error extracting data: {e}")
            return []
    
    def _extract_selection_data(self, df, selection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data from a specific selection"""
        try:
            selection_type = selection.get('type', 'range')
            
            if selection_type == 'range':
                return self._extract_range_data(df, selection)
            elif selection_type == 'table':
                return self._extract_table_data(df, selection)
            elif selection_type == 'pattern':
                return self._extract_pattern_data(df, selection)
            
            return []
        except Exception as e:
            logger.error(f"Error extracting selection data: {e}")
            return []
    
    def _extract_range_data(self, df, selection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data from a cell range"""
        if not EXCEL_AVAILABLE:
            return []
        
        start_row = selection.get('start_row', 0)
        end_row = selection.get('end_row', len(df))
        start_col = selection.get('start_col', 0)
        end_col = selection.get('end_col', len(df.columns))
        
        # Extract the range
        range_df = df.iloc[start_row:end_row+1, start_col:end_col+1]
        
        # Convert to test case format if mapping is provided
        mapping = selection.get('field_mapping', {})
        if mapping:
            return self._convert_to_test_cases(range_df, mapping)
        
        return []
    
    def _extract_table_data(self, df, selection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data from a table with headers"""
        if not EXCEL_AVAILABLE:
            return []
        
        header_row = selection.get('header_row', 0)
        start_row = selection.get('start_row', header_row + 1)
        end_row = selection.get('end_row', len(df))
        start_col = selection.get('start_col', 0)
        end_col = selection.get('end_col', len(df.columns))
        
        # Get headers
        headers = df.iloc[header_row, start_col:end_col+1].fillna('').astype(str).tolist()
        
        # Get data rows
        data_rows = df.iloc[start_row:end_row+1, start_col:end_col+1]
        
        # Convert to test cases
        test_cases = []
        mapping = selection.get('field_mapping', {})
        
        for _, row in data_rows.iterrows():
            row_data = row.fillna('').astype(str).tolist()
            if any(cell.strip() for cell in row_data):  # Skip empty rows
                test_case = self._map_row_to_test_case(headers, row_data, mapping)
                if test_case:
                    test_cases.append(test_case)
        
        return test_cases
    
    def _extract_pattern_data(self, df, selection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract data based on patterns (e.g., find tables by keywords)"""
        # This is for advanced pattern matching - can be implemented later
        return []
    
    def _convert_to_test_cases(self, df, mapping: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert DataFrame to test case format using field mapping"""
        test_cases = []
        
        for _, row in df.iterrows():
            test_case = {}
            row_data = row.fillna('').astype(str).tolist()
            
            for field, col_index in mapping.items():
                if isinstance(col_index, int) and 0 <= col_index < len(row_data):
                    value = row_data[col_index].strip()
                    
                    # Handle list fields (steps, expected)
                    if field in ['steps', 'expected'] and value:
                        # Split by common delimiters
                        test_case[field] = [step.strip() for step in value.split('\n') if step.strip()]
                        if not test_case[field]:  # If no newlines, try other delimiters
                            test_case[field] = [step.strip() for step in value.split(';') if step.strip()]
                        if not test_case[field]:  # If still empty, use as single item
                            test_case[field] = [value]
                    else:
                        test_case[field] = value
            
            # Only add if we have essential fields
            if test_case.get('id') and test_case.get('purpose'):
                # Set defaults for missing fields
                test_case.setdefault('scenerio', '')
                test_case.setdefault('test_data', '')
                test_case.setdefault('steps', [])
                test_case.setdefault('expected', [])
                test_case.setdefault('note', '')
                
                test_cases.append(test_case)
        
        return test_cases
    
    def _map_row_to_test_case(self, headers: List[str], row_data: List[str], mapping: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Map a row of data to test case format using headers and mapping"""
        test_case = {}
        
        for field, header_pattern in mapping.items():
            # Find matching header
            col_index = None
            for i, header in enumerate(headers):
                if header_pattern.lower() in header.lower() or header.lower() in header_pattern.lower():
                    col_index = i
                    break
            
            if col_index is not None and col_index < len(row_data):
                value = row_data[col_index].strip()
                
                # Handle list fields
                if field in ['steps', 'expected'] and value:
                    test_case[field] = [step.strip() for step in value.split('\n') if step.strip()]
                    if not test_case[field]:
                        test_case[field] = [step.strip() for step in value.split(';') if step.strip()]
                    if not test_case[field]:
                        test_case[field] = [value]
                else:
                    test_case[field] = value
        
        # Only return if we have essential fields
        if test_case.get('id') and test_case.get('purpose'):
            # Set defaults
            test_case.setdefault('scenerio', '')
            test_case.setdefault('test_data', '')
            test_case.setdefault('steps', [])
            test_case.setdefault('expected', [])
            test_case.setdefault('note', '')
            return test_case
        
        return None
    
    def get_ai_enhanced_sheet_analysis(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """Get AI-enhanced analysis of a specific sheet"""
        try:
            # Get basic sheet data
            sheet_data = self.get_sheet_data(file_path, sheet_name)
            
            if 'error' in sheet_data:
                return sheet_data
            
            # Get AI analysis
            ai_analysis = self.gemini_analyzer.analyze_excel_content(sheet_data, sheet_name)
            
            # Combine basic data with AI insights
            enhanced_analysis = {
                'sheet_name': sheet_name,
                'basic_data': sheet_data,
                'ai_analysis': ai_analysis,
                'enhanced': True
            }
            
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Error in AI-enhanced analysis: {e}")
            return {'error': str(e)}
    
    def get_ai_field_mapping_suggestions(self, file_path: str, sheet_name: str, header_row: int = 0) -> Dict[str, Any]:
        """Get AI suggestions for field mapping"""
        try:
            if not EXCEL_AVAILABLE:
                return {'error': 'Field mapping requires pandas/openpyxl'}
            
            # Read sheet data (Excel or ODS)
            if file_path.lower().endswith('.ods'):
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='odf')
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            # Extract headers and sample data
            headers = df.iloc[header_row].fillna('').astype(str).tolist()
            sample_data = df.iloc[header_row+1:header_row+6].fillna('').astype(str).values.tolist()
            
            # Get AI suggestions
            mapping_suggestions = self.gemini_analyzer.suggest_field_mapping(headers, sample_data)
            
            return {
                'success': True,
                'headers': headers,
                'sample_data': sample_data,
                'ai_suggestions': mapping_suggestions,
                'sheet_name': sheet_name
            }
            
        except Exception as e:
            logger.error(f"Error getting AI field mapping: {e}")
            return {'error': str(e)}
    
    def generate_extraction_logic(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """Generate AI-powered extraction logic for test cases"""
        try:
            # Get sheet data
            sheet_data = self.get_sheet_data(file_path, sheet_name)
            
            if 'error' in sheet_data:
                return sheet_data
            
            # Generate extraction logic using AI
            extraction_logic = self.gemini_analyzer.generate_extraction_logic(sheet_data, sheet_name)
            
            return {
                'success': True,
                'extraction_logic': extraction_logic,
                'sheet_name': sheet_name,
                'file_path': file_path
            }
            
        except Exception as e:
            logger.error(f"Error generating extraction logic: {e}")
            return {'error': str(e)}
    
    def extract_test_cases_smart(self, file_path: str, sheet_name: str, extraction_logic: Dict[str, Any]) -> Dict[str, Any]:
        """Extract test cases using AI-generated logic with merged cell handling"""
        try:
            if not EXCEL_AVAILABLE:
                return {'error': 'Smart extraction requires pandas/openpyxl'}
            
            # Extract test cases using smart extractor
            test_cases = self.smart_extractor.extract_with_ai_logic(file_path, sheet_name, extraction_logic)
            
            # Validate extracted data
            validation = self.smart_extractor.validate_extracted_data(test_cases)
            
            return {
                'success': True,
                'test_cases': test_cases,
                'validation': validation,
                'total_extracted': len(test_cases),
                'extraction_method': 'ai_smart_extraction'
            }
            
        except Exception as e:
            logger.error(f"Error in smart test case extraction: {e}")
            return {'error': str(e)}
    
    def preview_smart_extraction(self, file_path: str, sheet_name: str, extraction_logic: Dict[str, Any], max_rows: int = 5) -> Dict[str, Any]:
        """Preview smart extraction results"""
        try:
            if not EXCEL_AVAILABLE:
                return {'error': 'Smart extraction preview requires pandas/openpyxl'}
            
            # Get preview
            preview_result = self.smart_extractor.preview_extraction(file_path, sheet_name, extraction_logic, max_rows)
            
            return preview_result
            
        except Exception as e:
            logger.error(f"Error in smart extraction preview: {e}")
            return {'error': str(e)}
    
    def extract_test_cases_template(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """Extract test cases using template-based logic"""
        try:
            if not EXCEL_AVAILABLE:
                return {'error': 'Template extraction requires pandas/openpyxl'}
            
            # Extract test cases using template extractor
            result = self.template_extractor.extract_with_template(file_path, sheet_name)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in template test case extraction: {e}")
            return {'error': str(e)}
    
    def preview_template_extraction(self, file_path: str, sheet_name: str, max_rows: int = 5) -> Dict[str, Any]:
        """Preview template extraction results"""
        try:
            if not EXCEL_AVAILABLE:
                return {'error': 'Template extraction preview requires pandas/openpyxl'}
            
            # Get preview
            preview_result = self.template_extractor.preview_template_extraction(file_path, sheet_name, max_rows)
            
            return preview_result
            
        except Exception as e:
            logger.error(f"Error in template extraction preview: {e}")
            return {'error': str(e)}
    
    def find_template_header(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """Find the header row for template extraction"""
        try:
            if not EXCEL_AVAILABLE:
                return {'error': 'Header detection requires pandas/openpyxl'}
            
            header_row = self.template_extractor.find_header_row(file_path, sheet_name)
            
            if header_row is not None:
                return {
                    'success': True,
                    'header_row': header_row,
                    'template_mapping': self.template_extractor.template_mapping
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not find ID header in column A'
                }
            
        except Exception as e:
            logger.error(f"Error finding template header: {e}")
            return {'error': str(e)}

def analyze_excel_structure(file_path: str) -> Dict[str, Any]:
    """Analyze Excel file structure - simple rule-based analysis only"""
    if not EXCEL_AVAILABLE:
        # Use fallback reader
        fallback_reader = SimpleExcelReader()
        return fallback_reader.analyze_structure_basic(file_path)
    
    processor = ExcelProcessor()
    excel_info = processor.get_excel_info(file_path)
    
    if 'error' in excel_info:
        return excel_info
    
    # Simple structure analysis without AI
    analysis = {
        'filename': excel_info['filename'],
        'file_type': 'Excel/ODS',
        'total_sheets': excel_info['total_sheets'],
        'sheets': []
    }
    
    # Convert sheets info to simple format
    for sheet_name, sheet_info in excel_info['sheets'].items():
        sheet_analysis = {
            'name': sheet_name,
            'rows': sheet_info['rows'],
            'cols': sheet_info['cols'],
            'has_data': sheet_info['has_data']
        }
        analysis['sheets'].append(sheet_analysis)
    
    return analysis