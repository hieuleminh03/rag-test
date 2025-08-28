#!/usr/bin/env python3
"""
Flask Web UI for RAG Test Case Generation System
Provides a user-friendly interface to manage test cases and demonstrate RAG capabilities
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import logging
from typing import Dict, Any

from config import Config
from services import (
    TestCaseService, 
    APIDocumentationService, 
    CoverageAnalysisService,
    ExportService
)
from utils import ErrorHandler, setup_logging
from models import TestCase

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def create_app(config_name: str = 'default') -> Flask:
    """Application factory"""
    app = Flask(__name__)
    
    # Load configuration
    from config import config
    app.config.from_object(config[config_name])
    
    # Initialize directories
    Config.init_directories()
    
    # Initialize services
    test_case_service = TestCaseService()
    api_doc_service = APIDocumentationService()
    coverage_service = CoverageAnalysisService(test_case_service, api_doc_service)
    export_service = ExportService(test_case_service)
    
    return app, test_case_service, api_doc_service, coverage_service, export_service

app, test_case_service, api_doc_service, coverage_service, export_service = create_app()

@app.route('/')
def index():
    """Main dashboard"""
    try:
        # Get statistics and validation
        stats = test_case_service.get_statistics()
        validation_report = test_case_service.validate_all_test_cases()
        
        # Get coverage analysis
        coverage_analysis = coverage_service.analyze_coverage()
        
        return render_template('index.html', 
                             stats=stats.to_dict(),
                             validation_report=validation_report.to_dict(),
                             coverage_analysis=coverage_analysis.to_dict(),
                             total_cases=stats.total_cases)
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        flash(f"Error loading dashboard: {str(e)}", 'error')
        return render_template('index.html', 
                             stats={}, 
                             validation_report={}, 
                             coverage_analysis={}, 
                             total_cases=0)

@app.route('/test-cases')
def test_cases():
    """View and manage test cases"""
    try:
        search_query = request.args.get('search', '')
        
        if search_query:
            test_cases = test_case_service.search_test_cases(search_query)
        else:
            test_cases = test_case_service.get_all_test_cases()
        
        # Convert to dict for template
        test_cases_data = [tc.to_dict() for tc in test_cases]
        
        return render_template('test_cases.html', 
                             test_cases=test_cases_data, 
                             search_query=search_query)
    except Exception as e:
        logger.error(f"Error loading test cases: {e}")
        flash(f"Error loading test cases: {str(e)}", 'error')
        return render_template('test_cases.html', test_cases=[], search_query='')

@app.route('/test-case/<case_id>')
def view_test_case(case_id):
    """View individual test case details"""
    try:
        test_case = test_case_service.get_test_case_by_id(case_id)
        
        if not test_case:
            flash(f"Test case '{case_id}' not found", 'error')
            return redirect(url_for('test_cases'))
        
        return render_template('test_case_detail.html', test_case=test_case.to_dict())
    except Exception as e:
        logger.error(f"Error loading test case {case_id}: {e}")
        flash(f"Error loading test case: {str(e)}", 'error')
        return redirect(url_for('test_cases'))

@app.route('/add-test-case', methods=['GET', 'POST'])
def add_test_case():
    """Add new test case"""
    if request.method == 'POST':
        try:
            # Get form data
            test_case_data = {
                'id': request.form.get('id', '').strip(),
                'purpose': request.form.get('purpose', '').strip(),
                'scenerio': request.form.get('scenerio', '').strip(),
                'test_data': request.form.get('test_data', '').strip(),
                'steps': [step.strip() for step in request.form.get('steps', '').split('\n') if step.strip()],
                'expected': [exp.strip() for exp in request.form.get('expected', '').split('\n') if exp.strip()],
                'note': request.form.get('note', '').strip()
            }
            
            test_case = test_case_service.create_test_case(test_case_data)
            flash(f"Test case '{test_case.id}' added successfully!", 'success')
            return redirect(url_for('test_cases'))
                
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            logger.error(f"Error adding test case: {e}")
            flash(f"Error adding test case: {str(e)}", 'error')
    
    return render_template('add_test_case.html')

@app.route('/delete-test-case/<case_id>', methods=['POST'])
def delete_test_case(case_id):
    """Delete test case"""
    try:
        if test_case_service.delete_test_case(case_id):
            flash(f"Test case '{case_id}' deleted successfully!", 'success')
        else:
            flash(f"Test case '{case_id}' not found", 'error')
    except Exception as e:
        logger.error(f"Error deleting test case {case_id}: {e}")
        flash(f"Error deleting test case: {str(e)}", 'error')
    
    return redirect(url_for('test_cases'))

@app.route('/rag-demo')
def rag_demo():
    """RAG demonstration page"""
    try:
        # Load API documentation
        api_doc = api_doc_service.load_api_documentation()
        
        # Extract business flows for display
        flows = api_doc_service.extract_business_flows(api_doc) if api_doc else []
        
        # Get existing test cases for context
        test_cases = test_case_service.get_all_test_cases()
        
        return render_template('rag_demo.html', 
                             api_doc=api_doc[:2000] + "..." if len(api_doc) > 2000 else api_doc,
                             flows=flows[:10],  # Show first 10 flows
                             total_test_cases=len(test_cases))
    except Exception as e:
        logger.error(f"Error loading RAG demo: {e}")
        flash(f"Error loading RAG demo: {str(e)}", 'error')
        return render_template('rag_demo.html', api_doc="", flows=[], total_test_cases=0)

@app.route('/generate-test-cases', methods=['POST'])
def generate_test_cases():
    """Generate test cases using RAG analysis"""
    try:
        api_input = request.form.get('api_input', '').strip()
        
        if not api_input:
            return jsonify(ErrorHandler.handle_validation_error(['API documentation is required'])), 400
        
        # Analyze the input and suggest test cases based on existing patterns
        flows = api_doc_service.extract_business_flows(api_input)
        existing_test_cases = test_case_service.get_all_test_cases()
        
        # Generate suggestions based on analysis
        suggestions = []
        
        # Analyze API input for common patterns
        api_lower = api_input.lower()
        
        if 'payment' in api_lower or 'thanh toán' in api_lower:
            suggestions.append({
                'id': 'payment-success_generated',
                'purpose': 'Kiểm tra thanh toán thành công',
                'scenerio': 'TH API thanh toán được gọi với dữ liệu hợp lệ',
                'test_data': 'Valid payment request data',
                'steps': ['1. Gửi request thanh toán', '2. Xử lý thanh toán', '3. Trả về kết quả'],
                'expected': ['1. Status code 200', '2. Transaction ID được tạo', '3. Database được cập nhật'],
                'note': 'Generated from payment API analysis'
            })
        
        if 'error' in api_lower or 'timeout' in api_lower:
            suggestions.append({
                'id': 'error-handling_generated',
                'purpose': 'Kiểm tra xử lý lỗi',
                'scenerio': 'TH API trả về lỗi hoặc timeout',
                'test_data': 'Error scenario data',
                'steps': ['1. Gửi request không hợp lệ', '2. API xử lý lỗi', '3. Trả về error response'],
                'expected': ['1. Error code được trả về', '2. Error message rõ ràng', '3. Log được ghi'],
                'note': 'Generated from error handling analysis'
            })
        
        return jsonify({
            'success': True,
            'generated_cases': suggestions,
            'message': f'Analyzed API documentation and suggested {len(suggestions)} test cases',
            'analysis': {
                'flows_found': len(flows),
                'existing_cases': len(existing_test_cases),
                'patterns_detected': len(suggestions)
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating test cases: {e}")
        return jsonify(ErrorHandler.handle_generic_error(e)), 500


@app.route('/coverage-analysis')
def coverage_analysis():
    """Test coverage analysis page"""
    try:
        # Get coverage analysis
        analysis = coverage_service.analyze_coverage()
        
        # Get business flows for display
        api_doc = api_doc_service.load_api_documentation()
        flows = api_doc_service.extract_business_flows(api_doc) if api_doc else []
        
        return render_template('coverage_analysis.html', 
                             analysis=analysis.to_dict(), 
                             flows=flows)
    except Exception as e:
        logger.error(f"Error performing coverage analysis: {e}")
        flash(f"Error performing coverage analysis: {str(e)}", 'error')
        return render_template('coverage_analysis.html', analysis={}, flows=[])

@app.route('/api/validate-test-case', methods=['POST'])
def api_validate_test_case():
    """API endpoint to validate test case data"""
    try:
        test_case_data = request.json
        if not test_case_data:
            return jsonify(ErrorHandler.handle_validation_error(['No data provided'])), 400
        
        # Create test case object for validation
        test_case = TestCase.from_dict(test_case_data)
        errors = test_case.validate()
        
        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors
        })
    except Exception as e:
        logger.error(f"Error validating test case: {e}")
        return jsonify(ErrorHandler.handle_generic_error(e)), 500

@app.route('/api/search-test-cases')
def api_search_test_cases():
    """API endpoint to search test cases"""
    try:
        query = request.args.get('q', '')
        if not query:
            return jsonify(ErrorHandler.handle_validation_error(['Search query is required'])), 400
        
        results = test_case_service.search_test_cases(query)
        results_data = [tc.to_dict() for tc in results]
        
        return jsonify({
            'results': results_data,
            'count': len(results_data),
            'query': query
        })
    except Exception as e:
        logger.error(f"Error searching test cases: {e}")
        return jsonify(ErrorHandler.handle_generic_error(e)), 500

@app.route('/export')
def export_data():
    """Export test cases"""
    try:
        # Export to JSON
        json_file = export_service.export_to_json()
        
        # Export to CSV
        csv_file = export_service.export_to_csv()
        
        flash(f"Test cases exported successfully to {json_file.parent}", 'success')
        
    except Exception as e:
        logger.error(f"Error exporting test cases: {e}")
        flash(f"Error exporting test cases: {str(e)}", 'error')
    
    return redirect(url_for('test_cases'))

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Initialize configuration and directories
    Config.init_directories()
    
    print("🚀 Starting RAG Test Case Management Web UI...")
    print("📊 Dashboard: http://localhost:5000")
    print("📋 Test Cases: http://localhost:5000/test-cases")
    print("🤖 RAG Demo: http://localhost:5000/rag-demo")
    print("📈 Coverage Analysis: http://localhost:5000/coverage-analysis")
    print("💡 Press Ctrl+C to stop the server")
    
    try:
        app.run(debug=Config.DEBUG, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        logger.info("Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        logger.error(f"Error starting server: {e}")