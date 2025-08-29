#!/usr/bin/env python3
"""
Simple Excel reader that works without pandas/openpyxl
Uses basic file structure analysis for Excel files
"""

import zipfile
import xml.etree.ElementTree as ET
import os
from typing import Dict, List, Any, Optional

class SimpleExcelReader:
    """Basic Excel file reader without external dependencies"""
    
    def __init__(self):
        self.namespaces = {
            'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
            'w': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        }
    
    def read_excel_basic_info(self, file_path: str) -> Dict[str, Any]:
        """Read basic Excel file information without pandas"""
        try:
            if not file_path.lower().endswith(('.xlsx', '.xlsm', '.ods')):
                return {'error': 'Only .xlsx, .xlsm, and .ods files are supported in fallback mode'}
            
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                # Read workbook.xml to get sheet names
                workbook_xml = zip_file.read('xl/workbook.xml')
                root = ET.fromstring(workbook_xml)
                
                sheets_info = {}
                sheet_names = []
                
                # Find all sheets
                for sheet in root.findall('.//w:sheet', self.namespaces):
                    sheet_name = sheet.get('name', 'Unknown')
                    sheet_names.append(sheet_name)
                    
                    # Basic info - we can't easily get row/col count without pandas
                    sheets_info[sheet_name] = {
                        'rows': 'Unknown',
                        'cols': 'Unknown', 
                        'has_data': True,  # Assume has data
                        'preview': [['Sheet data preview not available without pandas/openpyxl']]
                    }
                
                return {
                    'filename': os.path.basename(file_path),
                    'sheets': sheets_info,
                    'total_sheets': len(sheet_names),
                    'fallback_mode': True
                }
                
        except Exception as e:
            return {'error': f'Error reading Excel file: {str(e)}'}
    
    def analyze_structure_basic(self, file_path: str) -> Dict[str, Any]:
        """Basic structure analysis without pandas"""
        info = self.read_excel_basic_info(file_path)
        
        if 'error' in info:
            return info
        
        # Simple heuristic based on sheet names
        potential_test_sheets = []
        test_keywords = ['test', 'case', 'tc', 'scenario', 'testcase']
        
        for sheet_name in info['sheets'].keys():
            sheet_lower = sheet_name.lower()
            keyword_count = sum(1 for keyword in test_keywords if keyword in sheet_lower)
            
            if keyword_count > 0:
                potential_test_sheets.append({
                    'sheet_name': sheet_name,
                    'confidence': keyword_count / len(test_keywords),
                    'rows': 'Unknown',
                    'cols': 'Unknown',
                    'keywords_found': keyword_count,
                    'detection_method': 'sheet_name_analysis'
                })
        
        return {
            'filename': info['filename'],
            'total_sheets': info['total_sheets'],
            'sheets': info['sheets'],
            'potential_test_sheets': potential_test_sheets,
            'fallback_mode': True,
            'message': 'Using fallback mode. Install pandas and openpyxl for full functionality.'
        }