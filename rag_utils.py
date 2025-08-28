#!/usr/bin/env python3
"""
RAG System Utilities
Provides helper functions for RAG operations, data processing, and system management
"""

import json
import os
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import argparse

def load_api_documentation(file_path: str) -> str:
    """Load API documentation from markdown file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"✅ Loaded API documentation from {file_path} ({len(content)} characters)")
        return content
    except FileNotFoundError:
        print(f"❌ API documentation file {file_path} not found")
        return ""
    except Exception as e:
        print(f"❌ Error loading API documentation: {e}")
        return ""

def extract_api_sections(api_doc: str) -> Dict[str, str]:
    """Extract different sections from API documentation"""
    sections = {}
    
    # Common section headers to look for
    section_headers = [
        "# 1. Mô tả chung",
        "# 2. Biểu đồ nghiệp vụ", 
        "# 3. Mô tả luồng nghiệp vụ",
        "## Mục đích",
        "## Từ điển nghiệp vụ"
    ]
    
    lines = api_doc.split('\n')
    current_section = "overview"
    current_content = []
    
    for line in lines:
        # Check if this line is a section header
        is_header = False
        for header in section_headers:
            if line.strip().startswith(header):
                # Save previous section
                if current_content:
                    sections[current_section] = '\n'.join(current_content)
                
                # Start new section
                current_section = header.replace('#', '').replace('.', '').strip().lower().replace(' ', '_')
                current_content = [line]
                is_header = True
                break
        
        if not is_header:
            current_content.append(line)
    
    # Save last section
    if current_content:
        sections[current_section] = '\n'.join(current_content)
    
    return sections

def extract_business_flows(api_doc: str) -> List[Dict[str, str]]:
    """Extract business flow steps from API documentation"""
    flows = []
    lines = api_doc.split('\n')
    
    in_flow_table = False
    for line in lines:
        # Look for flow table
        if "| Bước |" in line and "Đối tượng thực thể" in line:
            in_flow_table = True
            continue
        
        if in_flow_table and line.strip().startswith('|') and not line.strip().startswith('| :'):
            parts = [part.strip() for part in line.split('|')[1:-1]]  # Remove empty first/last
            if len(parts) >= 3:
                flows.append({
                    "step": parts[0],
                    "actor": parts[1],
                    "description": parts[2],
                    "note": parts[3] if len(parts) > 3 else "",
                    "related_tables": parts[4] if len(parts) > 4 else ""
                })
    
    return flows

def generate_test_case_suggestions(api_doc: str) -> List[Dict[str, Any]]:
    """Generate test case suggestions based on API documentation analysis"""
    suggestions = []
    
    # Extract business flows
    flows = extract_business_flows(api_doc)
    
    # Analyze for common test scenarios
    if "timeout" in api_doc.lower() or "30s" in api_doc:
        suggestions.append({
            "category": "timeout",
            "description": "API timeout scenarios",
            "priority": "high",
            "rationale": "Documentation mentions timeout conditions"
        })
    
    if "error" in api_doc.lower() or "lỗi" in api_doc.lower():
        suggestions.append({
            "category": "error_handling",
            "description": "Error handling scenarios",
            "priority": "high", 
            "rationale": "Documentation mentions error conditions"
        })
    
    if "database" in api_doc.lower() or "bảng" in api_doc.lower():
        suggestions.append({
            "category": "database",
            "description": "Database interaction scenarios",
            "priority": "medium",
            "rationale": "Documentation involves database operations"
        })
    
    if "api" in api_doc.lower() and ("gọi" in api_doc.lower() or "call" in api_doc.lower()):
        suggestions.append({
            "category": "api_integration",
            "description": "API integration scenarios",
            "priority": "high",
            "rationale": "Documentation describes API calls between systems"
        })
    
    if "concurrent" in api_doc.lower() or "đồng thời" in api_doc.lower():
        suggestions.append({
            "category": "concurrency",
            "description": "Concurrent request scenarios",
            "priority": "medium",
            "rationale": "Documentation mentions concurrent operations"
        })
    
    return suggestions

def analyze_test_coverage(test_cases: List[Dict[str, Any]], api_doc: str) -> Dict[str, Any]:
    """Analyze test coverage against API documentation"""
    analysis = {
        "total_test_cases": len(test_cases),
        "coverage_areas": {},
        "missing_scenarios": [],
        "recommendations": []
    }
    
    # Extract business flows from API doc
    flows = extract_business_flows(api_doc)
    flow_steps = [flow["step"] for flow in flows]
    
    # Analyze existing test cases
    covered_steps = set()
    test_categories = {}
    
    for test_case in test_cases:
        # Categorize test cases
        test_id = test_case.get("id", "")
        category = test_id.split("-")[0] if "-" in test_id else "general"
        test_categories[category] = test_categories.get(category, 0) + 1
        
        # Check which flow steps are covered
        test_content = " ".join([
            test_case.get("purpose", ""),
            test_case.get("scenerio", ""),
            " ".join(test_case.get("steps", [])),
            " ".join(test_case.get("expected", []))
        ]).lower()
        
        for step in flow_steps:
            if step.lower() in test_content:
                covered_steps.add(step)
    
    analysis["coverage_areas"] = test_categories
    analysis["covered_flow_steps"] = len(covered_steps)
    analysis["total_flow_steps"] = len(flow_steps)
    analysis["coverage_percentage"] = round((len(covered_steps) / len(flow_steps)) * 100, 2) if flow_steps else 0
    
    # Identify missing scenarios
    suggestions = generate_test_case_suggestions(api_doc)
    existing_categories = set(test_categories.keys())
    
    for suggestion in suggestions:
        if suggestion["category"] not in existing_categories:
            analysis["missing_scenarios"].append(suggestion)
    
    # Generate recommendations
    if analysis["coverage_percentage"] < 70:
        analysis["recommendations"].append("Consider adding more test cases to cover business flows")
    
    if "error_handling" not in existing_categories:
        analysis["recommendations"].append("Add error handling test cases")
    
    if "timeout" not in existing_categories and "timeout" in api_doc.lower():
        analysis["recommendations"].append("Add timeout scenario test cases")
    
    return analysis

def benchmark_rag_performance(rag_function, test_queries: List[str], iterations: int = 3) -> Dict[str, Any]:
    """Benchmark RAG system performance"""
    results = {
        "total_queries": len(test_queries),
        "iterations_per_query": iterations,
        "response_times": [],
        "average_response_time": 0,
        "min_response_time": float('inf'),
        "max_response_time": 0,
        "success_rate": 0,
        "errors": []
    }
    
    successful_queries = 0
    
    for query in test_queries:
        query_times = []
        
        for i in range(iterations):
            start_time = time.time()
            try:
                response = rag_function(query)
                end_time = time.time()
                response_time = end_time - start_time
                query_times.append(response_time)
                
                if i == 0:  # Only count success on first iteration
                    successful_queries += 1
                    
            except Exception as e:
                results["errors"].append(f"Query '{query[:50]}...': {str(e)}")
                break
        
        if query_times:
            avg_time = sum(query_times) / len(query_times)
            results["response_times"].append(avg_time)
            results["min_response_time"] = min(results["min_response_time"], min(query_times))
            results["max_response_time"] = max(results["max_response_time"], max(query_times))
    
    if results["response_times"]:
        results["average_response_time"] = sum(results["response_times"]) / len(results["response_times"])
        results["success_rate"] = (successful_queries / len(test_queries)) * 100
    
    return results

def export_test_cases_to_formats(test_cases: List[Dict[str, Any]], output_dir: str = "exports"):
    """Export test cases to different formats (CSV, Excel, etc.)"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Export to CSV
    try:
        import csv
        csv_file = os.path.join(output_dir, f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            if test_cases:
                writer = csv.DictWriter(f, fieldnames=test_cases[0].keys())
                writer.writeheader()
                
                for test_case in test_cases:
                    # Convert lists to strings for CSV
                    row = test_case.copy()
                    for key, value in row.items():
                        if isinstance(value, list):
                            row[key] = " | ".join(value)
                    writer.writerow(row)
        
        print(f"✅ Exported to CSV: {csv_file}")
        
    except Exception as e:
        print(f"❌ Error exporting to CSV: {e}")
    
    # Export to JSON with pretty formatting
    try:
        json_file = os.path.join(output_dir, f"test_cases_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)
        print(f"✅ Exported to JSON: {json_file}")
        
    except Exception as e:
        print(f"❌ Error exporting to JSON: {e}")

def main():
    parser = argparse.ArgumentParser(description="RAG System Utilities")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Analyze API doc command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze API documentation")
    analyze_parser.add_argument("api_file", help="API documentation file path")
    analyze_parser.add_argument("--test-data", default="test_data.json", help="Test data file")
    
    # Extract sections command
    extract_parser = subparsers.add_parser("extract", help="Extract sections from API doc")
    extract_parser.add_argument("api_file", help="API documentation file path")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export test cases")
    export_parser.add_argument("--test-data", default="test_data.json", help="Test data file")
    export_parser.add_argument("--output-dir", default="exports", help="Output directory")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == "analyze":
        api_doc = load_api_documentation(args.api_file)
        if not api_doc:
            return
        
        # Load test cases
        try:
            with open(args.test_data, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)
        except Exception as e:
            print(f"❌ Error loading test cases: {e}")
            return
        
        # Perform analysis
        analysis = analyze_test_coverage(test_cases, api_doc)
        
        print("📊 Test Coverage Analysis:")
        print(f"Total test cases: {analysis['total_test_cases']}")
        print(f"Coverage percentage: {analysis['coverage_percentage']}%")
        print(f"Covered flow steps: {analysis['covered_flow_steps']}/{analysis['total_flow_steps']}")
        
        print(f"\n📋 Test categories:")
        for category, count in analysis['coverage_areas'].items():
            print(f"  - {category}: {count}")
        
        if analysis['missing_scenarios']:
            print(f"\n⚠️  Missing scenarios:")
            for scenario in analysis['missing_scenarios']:
                print(f"  - {scenario['category']}: {scenario['description']} ({scenario['priority']} priority)")
        
        if analysis['recommendations']:
            print(f"\n💡 Recommendations:")
            for rec in analysis['recommendations']:
                print(f"  - {rec}")
    
    elif args.command == "extract":
        api_doc = load_api_documentation(args.api_file)
        if not api_doc:
            return
        
        sections = extract_api_sections(api_doc)
        flows = extract_business_flows(api_doc)
        
        print("📄 Extracted sections:")
        for section_name, content in sections.items():
            print(f"  - {section_name}: {len(content)} characters")
        
        print(f"\n🔄 Extracted {len(flows)} business flow steps:")
        for i, flow in enumerate(flows[:5]):  # Show first 5
            print(f"  {i+1}. Step {flow['step']}: {flow['actor']} - {flow['description'][:100]}...")
    
    elif args.command == "export":
        try:
            with open(args.test_data, 'r', encoding='utf-8') as f:
                test_cases = json.load(f)
            
            export_test_cases_to_formats(test_cases, args.output_dir)
            
        except Exception as e:
            print(f"❌ Error exporting test cases: {e}")

if __name__ == "__main__":
    main()