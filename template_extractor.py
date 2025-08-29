#!/usr/bin/env python3
"""
Template-based Test Case Extractor
Extracts test cases using predefined column template structure
"""

import pandas as pd
import re
from typing import Dict, List, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class TemplateTestCaseExtractor:
    """Template-based extractor using predefined column structure"""
    
    def __init__(self):
        # Default column mapping based on Vietnamese template
        self.template_mapping = {
            'A': 'id',           # ID column
            'B': 'purpose',      # Mục đích kiểm thử
            'C': 'scenerio',     # Trường hợp kiểm thử  
            'D': 'test_data',    # Data test
            'E': 'steps',        # Các bước
            'F': 'expected',     # Mong muốn
            'P': 'note'          # Ghi chú (column P = index 15)
        }
        
        # Column indices (0-based)
        self.column_indices = {
            'id': 0,        # A
            'purpose': 1,   # B
            'scenerio': 2,  # C
            'test_data': 3, # D
            'steps': 4,     # E
            'expected': 5,  # F
            'note': 15      # P
        }
    
    def find_header_row(self, file_path: str, sheet_name: str) -> Optional[int]:
        """Find the row containing 'ID' in column A"""
        try:
            # Read Excel data
            if file_path.lower().endswith('.ods'):
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='odf')
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            # Look for 'ID' in column A (index 0)
            for row_idx in range(len(df)):
                cell_value = str(df.iloc[row_idx, 0]).strip().upper()
                if cell_value == 'ID':
                    logger.info(f"Found ID header at row {row_idx}")
                    return row_idx
            
            logger.warning("No 'ID' header found in column A")
            return None
            
        except Exception as e:
            logger.error(f"Error finding header row: {e}")
            return None
    
    def extract_with_template(self, file_path: str, sheet_name: str) -> Dict[str, Any]:
        """Extract test cases using template structure"""
        try:
            # Find header row
            header_row = self.find_header_row(file_path, sheet_name)
            if header_row is None:
                return {
                    'success': False,
                    'error': 'Could not find ID header in column A. Please ensure the sheet has an "ID" cell in column A.',
                    'test_cases': []
                }
            
            # Read Excel data
            if file_path.lower().endswith('.ods'):
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None, engine='odf')
            else:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
            
            # Extract test cases starting from header_row + 1
            test_cases = self._extract_test_cases_from_template(df, header_row)
            
            # Validate extracted data
            validation = self._validate_extracted_data(test_cases)
            
            return {
                'success': True,
                'test_cases': test_cases,
                'validation': validation,
                'header_row': header_row,
                'extraction_method': 'template_based',
                'template_mapping': self.template_mapping
            }
            
        except Exception as e:
            logger.error(f"Error in template extraction: {e}")
            return {
                'success': False,
                'error': str(e),
                'test_cases': []
            }
    
    def _extract_test_cases_from_template(self, df: pd.DataFrame, header_row: int) -> List[Dict[str, Any]]:
        """Extract test cases using template logic"""
        test_cases = []
        current_shared_data = {}
        
        # Start from row after header
        for row_idx in range(header_row + 1, len(df)):
            try:
                # Get ID from column A
                id_cell = str(df.iloc[row_idx, self.column_indices['id']]).strip()
                
                # Skip empty rows
                if not id_cell or id_cell.lower() in ['nan', 'none', '']:
                    continue
                
                # Check if this looks like a test case ID (not a header)
                if self._is_test_case_id(id_cell):
                    # Extract test case from this row
                    test_case = self._extract_single_test_case(df, row_idx, current_shared_data)
                    if test_case:
                        test_cases.append(test_case)
                        
                        # Update shared data for merged cells
                        self._update_shared_data(current_shared_data, test_case)
                
            except Exception as e:
                logger.warning(f"Error processing row {row_idx}: {e}")
                continue
        
        return test_cases
    
    def _is_test_case_id(self, id_value: str) -> bool:
        """Check if the value looks like a test case ID"""
        if not id_value:
            return False
        
        # Common test case ID patterns
        patterns = [
            r'^[A-Z]+_\d+$',      # HM_1, TC_001, etc.
            r'^[A-Z]+\d+$',       # HM1, TC001, etc.
            r'^\d+$',             # Just numbers: 1, 2, 3
            r'^Test_\d+$',        # Test_1, Test_2
            r'^TC\d+$',           # TC1, TC2
        ]
        
        for pattern in patterns:
            if re.match(pattern, id_value, re.IGNORECASE):
                return True
        
        # If it contains common header words, it's not a test case ID
        header_words = ['mục đích', 'trường hợp', 'bước', 'mong muốn', 'ghi chú', 'purpose', 'scenario', 'step', 'expected', 'note']
        if any(word in id_value.lower() for word in header_words):
            return False
        
        return True
    
    def _extract_single_test_case(self, df: pd.DataFrame, row_idx: int, shared_data: Dict) -> Optional[Dict[str, Any]]:
        """Extract a single test case from a row"""
        try:
            test_case = {
                "id": "",
                "purpose": "",
                "scenerio": "",
                "test_data": "",
                "steps": [],
                "expected": [],
                "note": ""
            }
            
            # Extract data from each column
            for field, col_idx in self.column_indices.items():
                if col_idx < len(df.columns):
                    cell_value = str(df.iloc[row_idx, col_idx]).strip()
                    
                    # Handle empty cells - use shared data if available
                    if not cell_value or cell_value.lower() in ['nan', 'none']:
                        if field in shared_data and field in ['purpose', 'test_data']:
                            cell_value = shared_data[field]
                        else:
                            cell_value = ""
                    
                    # Process the cell value
                    if field in ['steps', 'expected']:
                        # Handle list fields
                        test_case[field] = self._parse_list_field(cell_value)
                    else:
                        # Handle text fields
                        test_case[field] = self._clean_text_field(cell_value)
            
            # Only return if we have a valid ID
            if test_case['id']:
                return self._finalize_test_case(test_case)
            
            return None
            
        except Exception as e:
            logger.warning(f"Error extracting test case from row {row_idx}: {e}")
            return None
    
    def _parse_list_field(self, cell_value: str) -> List[str]:
        """Parse list fields (steps, expected) with multiple separators"""
        if not cell_value:
            return []
        
        # Don't split if it looks like a single item (no clear separators)
        # Check for JSON content or single coherent text
        if ('{' in cell_value and '}' in cell_value) or '\n' not in cell_value:
            # This is likely a single item (JSON response or single step)
            return [cell_value.strip()]
        
        # Try different separators only for clearly multi-line content
        separators = ['\n']  # Only use newline as primary separator
        items = [cell_value]  # Default: single item
        
        for separator in separators:
            if separator in cell_value:
                potential_items = [item.strip() for item in cell_value.split(separator) if item.strip()]
                # Only split if we get meaningful items (not just JSON fragments)
                if len(potential_items) > 1 and not any('{' in item and '}' not in item for item in potential_items):
                    items = potential_items
                    break
        
        # Clean items without adding extra numbering
        cleaned_items = []
        for item in items:
            item = item.strip()
            if item:
                cleaned_items.append(item)
        
        return cleaned_items if cleaned_items else ["Không có dữ liệu"]
    
    def _clean_text_field(self, text: str) -> str:
        """Clean text fields"""
        if not text or text.lower() in ['nan', 'none']:
            return ""
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove common Excel artifacts
        text = text.replace('\xa0', ' ')  # Non-breaking space
        text = text.replace('\u200b', '')  # Zero-width space
        
        return text
    
    def _update_shared_data(self, shared_data: Dict, test_case: Dict):
        """Update shared data for merged cells"""
        # Update shared data for fields that might be merged
        for field in ['purpose', 'test_data']:
            if test_case.get(field):
                shared_data[field] = test_case[field]
    
    def _finalize_test_case(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """Final validation and cleaning of test case"""
        
        # Ensure required fields are not empty
        if not test_case.get('purpose'):
            test_case['purpose'] = "Không có mục đích được định nghĩa"
        
        if not test_case.get('scenerio'):
            test_case['scenerio'] = "Không có trường hợp kiểm thử được định nghĩa"
        
        # Ensure lists are not empty
        if not test_case.get('steps'):
            test_case['steps'] = ["1. Không có bước thực hiện được định nghĩa"]
        
        if not test_case.get('expected'):
            test_case['expected'] = ["1. Không có kết quả mong đợi được định nghĩa"]
        
        # Clean up empty strings
        for field in ['purpose', 'scenerio', 'test_data', 'note']:
            if not test_case.get(field):
                test_case[field] = ""
        
        return test_case
    
    def _validate_extracted_data(self, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate extracted test cases"""
        validation_report = {
            'total_extracted': len(test_cases),
            'valid_cases': 0,
            'invalid_cases': 0,
            'errors': [],
            'warnings': []
        }
        
        seen_ids = set()
        
        for i, test_case in enumerate(test_cases):
            errors = []
            warnings = []
            
            # Check required fields
            if not test_case.get('id'):
                errors.append("Missing ID")
            elif test_case['id'] in seen_ids:
                errors.append(f"Duplicate ID: {test_case['id']}")
            else:
                seen_ids.add(test_case['id'])
            
            if not test_case.get('purpose'):
                warnings.append("Missing purpose")
            
            if not test_case.get('steps') or len(test_case['steps']) == 0:
                warnings.append("No test steps defined")
            
            if not test_case.get('expected') or len(test_case['expected']) == 0:
                warnings.append("No expected results defined")
            
            if errors:
                validation_report['invalid_cases'] += 1
                validation_report['errors'].append({
                    'index': i,
                    'id': test_case.get('id', f'case_{i}'),
                    'errors': errors
                })
            else:
                validation_report['valid_cases'] += 1
            
            if warnings:
                validation_report['warnings'].append({
                    'index': i,
                    'id': test_case.get('id', f'case_{i}'),
                    'warnings': warnings
                })
        
        return validation_report
    
    def preview_template_extraction(self, file_path: str, sheet_name: str, max_rows: int = 5) -> Dict[str, Any]:
        """Preview template extraction results"""
        try:
            # Extract limited number of test cases
            result = self.extract_with_template(file_path, sheet_name)
            
            if not result['success']:
                return result
            
            test_cases = result['test_cases']
            
            # Limit for preview
            preview_cases = test_cases[:max_rows]
            
            return {
                'success': True,
                'preview_cases': preview_cases,
                'validation': result['validation'],
                'total_available': len(test_cases),
                'header_row': result['header_row'],
                'extraction_method': 'template_based_preview',
                'template_mapping': self.template_mapping
            }
            
        except Exception as e:
            logger.error(f"Error in template extraction preview: {e}")
            return {
                'success': False,
                'error': str(e)
            }