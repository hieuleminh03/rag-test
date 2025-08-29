#!/usr/bin/env python3
"""
Service layer for RAG Test Case Management System
Handles business logic and data operations
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from models import TestCase, ValidationReport, CoverageAnalysis, Statistics
from config import Config
# Force use JSON database to avoid SQLite locking issues
from json_database import JSONDatabaseManager as DatabaseManager
DATABASE_TYPE = "json"
print(f"Using {DATABASE_TYPE} database for reliability")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestCaseService:
    """Service for test case operations using SQLite database"""
    
    def __init__(self, db_path: Path = None):
        self.db = DatabaseManager(db_path)
        # Migrate from JSON if it exists
        self._migrate_from_json_if_needed()
    
    def _migrate_from_json_if_needed(self):
        """Migrate from JSON file if it exists and database is empty"""
        try:
            json_file = Config.TEST_DATA_FILE
            if json_file.exists():
                existing_count = len(self.get_all_test_cases())
                if existing_count == 0:
                    migrated = self.db.migrate_from_json(json_file)
                    if migrated > 0:
                        logger.info(f"Migrated {migrated} test cases from JSON to SQLite")
                        # Backup the JSON file
                        backup_file = json_file.with_suffix('.json.backup')
                        json_file.rename(backup_file)
                        logger.info(f"Backed up JSON file to {backup_file}")
        except Exception as e:
            logger.error(f"Error during JSON migration: {e}")
    
    def get_all_test_cases(self) -> List[TestCase]:
        """Get all test cases"""
        return self.db.get_all_test_cases()
    
    def get_test_case_by_id(self, case_id: str) -> Optional[TestCase]:
        """Get test case by ID (first match for backward compatibility)"""
        return self.db.get_test_case_by_id(case_id)
    
    def get_test_case_by_id_and_purpose(self, case_id: str, purpose: str) -> Optional[TestCase]:
        """Get test case by ID and purpose (unique key)"""
        return self.db.get_test_case_by_id_and_purpose(case_id, purpose)
    
    def create_test_case(self, test_case_data: Dict[str, Any]) -> TestCase:
        """Create new test case"""
        test_case = TestCase.from_dict(test_case_data)
        
        # Validate
        errors = test_case.validate()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")
        
        # Try to create
        if not self.db.create_test_case(test_case):
            raise ValueError(f"Test case with ID '{test_case.id}' and purpose '{test_case.purpose}' already exists")
        
        logger.info(f"Created test case: {test_case.id}")
        return test_case
    
    def upsert_test_case(self, test_case_data: Dict[str, Any]) -> TestCase:
        """Insert or update test case (for data import)"""
        test_case = TestCase.from_dict(test_case_data)
        
        # Validate
        errors = test_case.validate()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")
        
        # Upsert
        if not self.db.upsert_test_case(test_case):
            raise ValueError(f"Failed to save test case: {test_case.id}")
        
        logger.info(f"Upserted test case: {test_case.id}")
        return test_case
    
    def update_test_case(self, case_id: str, updates: Dict[str, Any]) -> TestCase:
        """Update existing test case"""
        # Get existing test case (first match)
        existing = self.get_test_case_by_id(case_id)
        if not existing:
            raise ValueError(f"Test case with ID '{case_id}' not found")
        
        # Apply updates
        updated_data = existing.to_dict()
        updated_data.update(updates)
        updated_data['updated_at'] = datetime.now().isoformat()
        
        updated_case = TestCase.from_dict(updated_data)
        
        # Validate
        errors = updated_case.validate()
        if errors:
            raise ValueError(f"Validation errors: {', '.join(errors)}")
        
        # Update in database
        if not self.db.update_test_case(updated_case):
            raise ValueError(f"Failed to update test case: {case_id}")
        
        logger.info(f"Updated test case: {case_id}")
        return updated_case
    
    def delete_test_case(self, case_id: str, purpose: str = None) -> bool:
        """Delete test case"""
        return self.db.delete_test_case(case_id, purpose)
    
    def search_test_cases(self, query: str) -> List[TestCase]:
        """Search test cases"""
        if len(query) < Config.SEARCH_MIN_LENGTH:
            return []
        
        return self.db.search_test_cases(query)
    
    def validate_all_test_cases(self) -> ValidationReport:
        """Validate all test cases"""
        test_cases = self.get_all_test_cases()
        report = ValidationReport(total_cases=len(test_cases))
        
        seen_keys = set()
        
        for i, tc in enumerate(test_cases):
            errors = tc.validate()
            
            if errors:
                report.invalid_cases += 1
                report.errors.append({
                    'index': i,
                    'id': tc.id,
                    'errors': errors
                })
            else:
                report.valid_cases += 1
            
            # Check for duplicate ID+purpose combinations
            key = f"{tc.id}|{tc.purpose}"
            if key in seen_keys:
                report.duplicate_ids.append(f"{tc.id} (purpose: {tc.purpose})")
            seen_keys.add(key)
        
        return report
    
    def get_statistics(self) -> Statistics:
        """Get test case statistics"""
        db_stats = self.db.get_statistics()
        test_cases = self.get_all_test_cases()
        
        stats = Statistics(
            total_cases=db_stats['total_cases'],
            purposes=db_stats['purposes'],
            test_data_sources=db_stats['test_data_sources']
        )
        
        if test_cases:
            total_steps = sum(len(tc.steps) for tc in test_cases)
            total_expected = sum(len(tc.expected) for tc in test_cases)
            
            stats.avg_steps = round(total_steps / len(test_cases), 2)
            stats.avg_expected = round(total_expected / len(test_cases), 2)
        
        return stats

class APIDocumentationService:
    """Service for API documentation operations"""
    
    def __init__(self, api_doc_file: Path = None):
        self.api_doc_file = api_doc_file or Config.API_DOC_FILE
    
    def load_api_documentation(self) -> str:
        """Load API documentation"""
        try:
            if not self.api_doc_file.exists():
                logger.warning(f"API documentation file not found: {self.api_doc_file}")
                return ""
            
            with open(self.api_doc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            logger.info(f"Loaded API documentation: {len(content)} characters")
            return content
        except Exception as e:
            logger.error(f"Error loading API documentation: {e}")
            return ""
    
    def extract_business_flows(self, api_doc: str) -> List[Dict[str, str]]:
        """Extract business flows from API documentation"""
        flows = []
        lines = api_doc.split('\n')
        
        in_flow_table = False
        for line in lines:
            # Look for flow table
            if "| Bước |" in line and "Đối tượng thực thể" in line:
                in_flow_table = True
                continue
            
            if in_flow_table and line.strip().startswith('|') and not line.strip().startswith('| :'):
                parts = [part.strip() for part in line.split('|')[1:-1]]
                if len(parts) >= 3:
                    flows.append({
                        "step": parts[0],
                        "actor": parts[1],
                        "description": parts[2],
                        "note": parts[3] if len(parts) > 3 else "",
                        "related_tables": parts[4] if len(parts) > 4 else ""
                    })
        
        return flows

class CoverageAnalysisService:
    """Service for coverage analysis operations"""
    
    def __init__(self, test_case_service: TestCaseService, api_doc_service: APIDocumentationService):
        self.test_case_service = test_case_service
        self.api_doc_service = api_doc_service
    
    def analyze_coverage(self, api_doc: str = None) -> CoverageAnalysis:
        """Analyze test coverage"""
        if api_doc is None:
            api_doc = self.api_doc_service.load_api_documentation()
        
        test_cases = self.test_case_service.get_all_test_cases()
        flows = self.api_doc_service.extract_business_flows(api_doc)
        
        analysis = CoverageAnalysis(
            total_test_cases=len(test_cases),
            total_flow_steps=len(flows)
        )
        
        # Analyze test case categories
        for tc in test_cases:
            category = tc.id.split("-")[0] if "-" in tc.id else "general"
            analysis.coverage_areas[category] = analysis.coverage_areas.get(category, 0) + 1
        
        # Calculate flow coverage
        flow_steps = [flow["step"] for flow in flows]
        covered_steps = set()
        
        for tc in test_cases:
            test_content = " ".join([
                tc.purpose, tc.scenerio,
                " ".join(tc.steps), " ".join(tc.expected)
            ]).lower()
            
            for step in flow_steps:
                if step.lower() in test_content:
                    covered_steps.add(step)
        
        analysis.covered_flow_steps = len(covered_steps)
        analysis.coverage_percentage = (
            (len(covered_steps) / len(flow_steps)) * 100 
            if flow_steps else 0
        )
        
        # Generate recommendations
        analysis.recommendations = self._generate_recommendations(analysis, api_doc)
        analysis.missing_scenarios = self._identify_missing_scenarios(analysis, api_doc)
        
        return analysis
    
    def _generate_recommendations(self, analysis: CoverageAnalysis, api_doc: str) -> List[str]:
        """Generate coverage recommendations"""
        recommendations = []
        
        if analysis.coverage_percentage < 70:
            recommendations.append("Consider adding more test cases to cover business flows")
        
        if "error_handling" not in analysis.coverage_areas:
            recommendations.append("Add error handling test cases")
        
        if "timeout" not in analysis.coverage_areas and "timeout" in api_doc.lower():
            recommendations.append("Add timeout scenario test cases")
        
        if analysis.total_test_cases < 10:
            recommendations.append("Increase test case coverage for better quality assurance")
        
        return recommendations
    
    def _identify_missing_scenarios(self, analysis: CoverageAnalysis, api_doc: str) -> List[Dict[str, str]]:
        """Identify missing test scenarios"""
        missing = []
        existing_categories = set(analysis.coverage_areas.keys())
        
        # Common scenarios to check
        scenarios = [
            {
                "category": "timeout",
                "description": "API timeout scenarios",
                "priority": "high",
                "rationale": "Documentation mentions timeout conditions",
                "keywords": ["timeout", "30s", "time"]
            },
            {
                "category": "error_handling", 
                "description": "Error handling scenarios",
                "priority": "high",
                "rationale": "Documentation mentions error conditions",
                "keywords": ["error", "lỗi", "fail"]
            },
            {
                "category": "concurrency",
                "description": "Concurrent request scenarios", 
                "priority": "medium",
                "rationale": "Documentation mentions concurrent operations",
                "keywords": ["concurrent", "đồng thời", "parallel"]
            }
        ]
        
        for scenario in scenarios:
            if scenario["category"] not in existing_categories:
                # Check if scenario is relevant to the API doc
                if any(keyword in api_doc.lower() for keyword in scenario["keywords"]):
                    missing.append({
                        "category": scenario["category"],
                        "description": scenario["description"],
                        "priority": scenario["priority"],
                        "rationale": scenario["rationale"]
                    })
        
        return missing

class ExportService:
    """Service for data export operations"""
    
    def __init__(self, test_case_service: TestCaseService):
        self.test_case_service = test_case_service
    
    def export_to_json(self, output_file: Path = None) -> Path:
        """Export test cases to JSON"""
        test_cases = self.test_case_service.get_all_test_cases()
        
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Config.EXPORTS_DIR / f"test_cases_{timestamp}.json"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = [tc.to_dict() for tc in test_cases]
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Exported {len(test_cases)} test cases to {output_file}")
        return output_file
    
    def export_to_csv(self, output_file: Path = None) -> Path:
        """Export test cases to CSV"""
        import csv
        
        test_cases = self.test_case_service.get_all_test_cases()
        
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = Config.EXPORTS_DIR / f"test_cases_{timestamp}.csv"
        
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            if test_cases:
                fieldnames = ['id', 'purpose', 'scenerio', 'test_data', 'steps', 'expected', 'note', 'created_at', 'updated_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for tc in test_cases:
                    row = tc.to_dict()
                    # Convert lists to strings for CSV
                    row['steps'] = " | ".join(row['steps'])
                    row['expected'] = " | ".join(row['expected'])
                    writer.writerow(row)
        
        logger.info(f"Exported {len(test_cases)} test cases to {output_file}")
        return output_file