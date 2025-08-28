#!/usr/bin/env python3
"""
Data Management Utilities for RAG Test Case System
Provides tools for managing test case data, validation, and operations
"""

import json
import os
import sys
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse

class TestCaseManager:
    """Manages test case data operations"""
    
    def __init__(self, data_file: str = "test_data.json"):
        self.data_file = data_file
        self.required_fields = ["id", "purpose", "scenerio", "test_data", "steps", "expected", "note"]
    
    def load_test_cases(self) -> List[Dict[str, Any]]:
        """Load test cases from JSON file"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"❌ File {self.data_file} not found")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in {self.data_file}: {e}")
            return []
    
    def save_test_cases(self, test_cases: List[Dict[str, Any]]) -> bool:
        """Save test cases to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(test_cases, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved {len(test_cases)} test cases to {self.data_file}")
            return True
        except Exception as e:
            print(f"❌ Error saving to {self.data_file}: {e}")
            return False
    
    def validate_test_case(self, test_case: Dict[str, Any]) -> List[str]:
        """Validate a single test case structure"""
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in test_case:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        if "id" in test_case and not isinstance(test_case["id"], str):
            errors.append("Field 'id' must be a string")
        
        if "steps" in test_case and not isinstance(test_case["steps"], list):
            errors.append("Field 'steps' must be a list")
        
        if "expected" in test_case and not isinstance(test_case["expected"], list):
            errors.append("Field 'expected' must be a list")
        
        # Check for empty required fields
        if test_case.get("id", "").strip() == "":
            errors.append("Field 'id' cannot be empty")
        
        if test_case.get("purpose", "").strip() == "":
            errors.append("Field 'purpose' cannot be empty")
        
        return errors
    
    def validate_all_test_cases(self) -> Dict[str, Any]:
        """Validate all test cases and return validation report"""
        test_cases = self.load_test_cases()
        report = {
            "total_cases": len(test_cases),
            "valid_cases": 0,
            "invalid_cases": 0,
            "errors": [],
            "duplicate_ids": []
        }
        
        seen_ids = set()
        
        for i, test_case in enumerate(test_cases):
            case_errors = self.validate_test_case(test_case)
            
            if case_errors:
                report["invalid_cases"] += 1
                report["errors"].append({
                    "index": i,
                    "id": test_case.get("id", f"case_{i}"),
                    "errors": case_errors
                })
            else:
                report["valid_cases"] += 1
            
            # Check for duplicate IDs
            case_id = test_case.get("id")
            if case_id:
                if case_id in seen_ids:
                    report["duplicate_ids"].append(case_id)
                seen_ids.add(case_id)
        
        return report
    
    def add_test_case(self, test_case: Dict[str, Any]) -> bool:
        """Add a new test case"""
        errors = self.validate_test_case(test_case)
        if errors:
            print(f"❌ Invalid test case: {', '.join(errors)}")
            return False
        
        test_cases = self.load_test_cases()
        
        # Check for duplicate ID
        existing_ids = [tc.get("id") for tc in test_cases]
        if test_case["id"] in existing_ids:
            print(f"❌ Test case with ID '{test_case['id']}' already exists")
            return False
        
        test_cases.append(test_case)
        return self.save_test_cases(test_cases)
    
    def update_test_case(self, case_id: str, updates: Dict[str, Any]) -> bool:
        """Update an existing test case"""
        test_cases = self.load_test_cases()
        
        for i, test_case in enumerate(test_cases):
            if test_case.get("id") == case_id:
                # Apply updates
                test_cases[i].update(updates)
                
                # Validate updated test case
                errors = self.validate_test_case(test_cases[i])
                if errors:
                    print(f"❌ Updated test case is invalid: {', '.join(errors)}")
                    return False
                
                return self.save_test_cases(test_cases)
        
        print(f"❌ Test case with ID '{case_id}' not found")
        return False
    
    def delete_test_case(self, case_id: str) -> bool:
        """Delete a test case by ID"""
        test_cases = self.load_test_cases()
        original_count = len(test_cases)
        
        test_cases = [tc for tc in test_cases if tc.get("id") != case_id]
        
        if len(test_cases) == original_count:
            print(f"❌ Test case with ID '{case_id}' not found")
            return False
        
        print(f"✅ Deleted test case '{case_id}'")
        return self.save_test_cases(test_cases)
    
    def search_test_cases(self, query: str) -> List[Dict[str, Any]]:
        """Search test cases by keyword in any field"""
        test_cases = self.load_test_cases()
        results = []
        
        query_lower = query.lower()
        
        for test_case in test_cases:
            # Search in all string fields
            searchable_text = " ".join([
                str(test_case.get("id", "")),
                str(test_case.get("purpose", "")),
                str(test_case.get("scenerio", "")),
                str(test_case.get("test_data", "")),
                " ".join(test_case.get("steps", [])),
                " ".join(test_case.get("expected", [])),
                str(test_case.get("note", ""))
            ]).lower()
            
            if query_lower in searchable_text:
                results.append(test_case)
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about test cases"""
        test_cases = self.load_test_cases()
        
        stats = {
            "total_cases": len(test_cases),
            "purposes": {},
            "test_data_sources": {},
            "avg_steps": 0,
            "avg_expected": 0
        }
        
        total_steps = 0
        total_expected = 0
        
        for test_case in test_cases:
            # Count purposes
            purpose = test_case.get("purpose", "Unknown")
            stats["purposes"][purpose] = stats["purposes"].get(purpose, 0) + 1
            
            # Count test data sources
            test_data = test_case.get("test_data", "Unknown")
            stats["test_data_sources"][test_data] = stats["test_data_sources"].get(test_data, 0) + 1
            
            # Calculate averages
            total_steps += len(test_case.get("steps", []))
            total_expected += len(test_case.get("expected", []))
        
        if len(test_cases) > 0:
            stats["avg_steps"] = round(total_steps / len(test_cases), 2)
            stats["avg_expected"] = round(total_expected / len(test_cases), 2)
        
        return stats

def create_sample_test_case() -> Dict[str, Any]:
    """Create a sample test case template"""
    return {
        "id": "sample-test_1",
        "purpose": "Sample test case purpose",
        "scenerio": "Sample scenario description",
        "test_data": "Sample data source",
        "steps": [
            "1. Sample step 1",
            "2. Sample step 2"
        ],
        "expected": [
            "1. Sample expected result 1",
            "2. Sample expected result 2"
        ],
        "note": "Sample note"
    }

def main():
    parser = argparse.ArgumentParser(description="Test Case Data Manager")
    parser.add_argument("--file", default="test_data.json", help="Test data file path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate test cases")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List all test cases")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search test cases")
    search_parser.add_argument("query", help="Search query")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show statistics")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add new test case")
    add_parser.add_argument("--template", action="store_true", help="Create from template")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete test case")
    delete_parser.add_argument("id", help="Test case ID to delete")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = TestCaseManager(args.file)
    
    if args.command == "validate":
        print("🔍 Validating test cases...")
        report = manager.validate_all_test_cases()
        
        print(f"\n📊 Validation Report:")
        print(f"Total cases: {report['total_cases']}")
        print(f"Valid cases: {report['valid_cases']} ✅")
        print(f"Invalid cases: {report['invalid_cases']} ❌")
        
        if report['duplicate_ids']:
            print(f"\n⚠️  Duplicate IDs found: {', '.join(report['duplicate_ids'])}")
        
        if report['errors']:
            print(f"\n❌ Errors found:")
            for error in report['errors']:
                print(f"  Case {error['index']} ({error['id']}): {', '.join(error['errors'])}")
    
    elif args.command == "list":
        test_cases = manager.load_test_cases()
        print(f"📋 Found {len(test_cases)} test cases:")
        for i, tc in enumerate(test_cases):
            print(f"  {i+1}. {tc.get('id', 'No ID')} - {tc.get('purpose', 'No purpose')}")
    
    elif args.command == "search":
        results = manager.search_test_cases(args.query)
        print(f"🔍 Found {len(results)} test cases matching '{args.query}':")
        for tc in results:
            print(f"  - {tc.get('id', 'No ID')}: {tc.get('purpose', 'No purpose')}")
    
    elif args.command == "stats":
        stats = manager.get_statistics()
        print(f"📊 Test Case Statistics:")
        print(f"Total cases: {stats['total_cases']}")
        print(f"Average steps per case: {stats['avg_steps']}")
        print(f"Average expected results per case: {stats['avg_expected']}")
        
        print(f"\n🎯 Top purposes:")
        for purpose, count in sorted(stats['purposes'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {purpose}: {count}")
        
        print(f"\n💾 Top data sources:")
        for source, count in sorted(stats['test_data_sources'].items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"  - {source}: {count}")
    
    elif args.command == "add":
        if args.template:
            sample = create_sample_test_case()
            print("📝 Sample test case template:")
            print(json.dumps(sample, ensure_ascii=False, indent=2))
            print("\nEdit this template and use it to add new test cases.")
        else:
            print("Use --template flag to see the test case structure")
    
    elif args.command == "delete":
        if manager.delete_test_case(args.id):
            print(f"✅ Successfully deleted test case '{args.id}'")
        else:
            print(f"❌ Failed to delete test case '{args.id}'")

if __name__ == "__main__":
    main()