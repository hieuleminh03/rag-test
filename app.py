#!/usr/bin/env python3
"""
Flask Web UI for RAG Test Case Generation System
Provides a user-friendly interface to manage test cases and demonstrate RAG capabilities
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import logging
import os
import uuid
from typing import Dict, Any
from werkzeug.utils import secure_filename

from config import Config
from services import (
    TestCaseService, 
    APIDocumentationService, 
    CoverageAnalysisService,
    ExportService
)
from utils import ErrorHandler, setup_logging
from models import TestCase
from excel_processor import ExcelProcessor, analyze_excel_structure
from rag_service import RAGService

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
    excel_processor = ExcelProcessor()
    rag_service = RAGService()
    
    return app, test_case_service, api_doc_service, coverage_service, export_service, excel_processor, rag_service

app, test_case_service, api_doc_service, coverage_service, export_service, excel_processor, rag_service = create_app()

# Global storage for uploaded files (in production, use Redis or database)
uploaded_files = {}

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
        # Initialize RAG service if not already done
        if not rag_service.is_initialized:
            rag_service.initialize()
        
        # Load API documentation
        api_doc = api_doc_service.load_api_documentation()
        
        # Extract business flows for display
        flows = api_doc_service.extract_business_flows(api_doc) if api_doc else []
        
        # Get existing test cases for context
        test_cases = test_case_service.get_all_test_cases()
        
        # Get RAG service status
        rag_status = rag_service.get_status()
        
        return render_template('rag_demo.html', 
                             api_doc=api_doc[:2000] + "..." if len(api_doc) > 2000 else api_doc,
                             flows=flows[:10],  # Show first 10 flows
                             total_test_cases=len(test_cases),
                             rag_status=rag_status)
    except Exception as e:
        logger.error(f"Error loading RAG demo: {e}")
        flash(f"Error loading RAG demo: {str(e)}", 'error')
        return render_template('rag_demo.html', api_doc="", flows=[], total_test_cases=0, rag_status={})

@app.route('/generate-test-cases', methods=['POST'])
def generate_test_cases():
    """Generate test cases using RAG analysis"""
    try:
        api_input = request.form.get('api_input', '').strip()
        custom_prompt = request.form.get('custom_prompt', '').strip()
        
        if not api_input:
            return jsonify(ErrorHandler.handle_validation_error(['API documentation is required'])), 400
        
        # Initialize RAG service if not already done
        if not rag_service.is_initialized:
            if not rag_service.initialize():
                return jsonify({'success': False, 'error': 'Failed to initialize RAG service'}), 500
        
        # Use RAG service to generate test cases with optional custom prompt
        result = rag_service.generate_test_cases(api_input, custom_prompt if custom_prompt else None)
        
        if result['success']:
            return jsonify(result)
        else:
            # Fallback to simple analysis if RAG fails
            logger.warning(f"RAG generation failed: {result.get('error')}. Using fallback.")
            
            flows = api_doc_service.extract_business_flows(api_input)
            existing_test_cases = test_case_service.get_all_test_cases()
            
            # Generate simple suggestions based on analysis
            suggestions = []
            api_lower = api_input.lower()
            
            if 'payment' in api_lower or 'thanh toán' in api_lower:
                suggestions.append({
                    'id': 'payment-success_generated',
                    'purpose': 'Kiểm tra thanh toán thành công',
                    'scenerio': 'TH API thanh toán được gọi với dữ liệu hợp lệ',
                    'test_data': 'Valid payment request data',
                    'steps': ['1. Gửi request thanh toán', '2. Xử lý thanh toán', '3. Trả về kết quả'],
                    'expected': ['1. Status code 200', '2. Transaction ID được tạo', '3. Database được cập nhật'],
                    'note': 'Generated from payment API analysis (fallback)'
                })
            
            if 'error' in api_lower or 'timeout' in api_lower:
                suggestions.append({
                    'id': 'error-handling_generated',
                    'purpose': 'Kiểm tra xử lý lỗi',
                    'scenerio': 'TH API trả về lỗi hoặc timeout',
                    'test_data': 'Error scenario data',
                    'steps': ['1. Gửi request không hợp lệ', '2. API xử lý lỗi', '3. Trả về error response'],
                    'expected': ['1. Error code được trả về', '2. Error message rõ ràng', '3. Log được ghi'],
                    'note': 'Generated from error handling analysis (fallback)'
                })
            
            return jsonify({
                'success': True,
                'generated_cases': suggestions,
                'message': f'Used fallback analysis. RAG error: {result.get("error")}',
                'analysis': {
                    'flows_found': len(flows),
                    'existing_cases': len(existing_test_cases),
                    'patterns_detected': len(suggestions),
                    'rag_error': result.get('error')
                }
            })
        
    except Exception as e:
        logger.error(f"Error generating test cases: {e}")
        return jsonify(ErrorHandler.handle_generic_error(e)), 500

@app.route('/embed-documents', methods=['POST'])
def embed_documents():
    """Embed test case documents into vector store"""
    try:
        # Initialize RAG service if not already done
        if not rag_service.is_initialized:
            if not rag_service.initialize():
                return jsonify({'success': False, 'error': 'Failed to initialize RAG service'}), 500
        
        # Start embedding process
        result = rag_service.embed_documents()
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error embedding documents: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rag-status')
def rag_status():
    """Get RAG service status"""
    try:
        if not rag_service.is_initialized:
            rag_service.initialize()
        
        status = rag_service.get_status()
        return jsonify({'success': True, 'status': status})
        
    except Exception as e:
        logger.error(f"Error getting RAG status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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

@app.route('/data-cleaning')
def data_cleaning():
    """Data cleaning interface"""
    return render_template('data_cleaning.html')

@app.route('/api/analyze_excel', methods=['POST'])
def api_analyze_excel():
    """Analyze uploaded Excel files"""
    try:
        if 'files' not in request.files:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files or all(f.filename == '' for f in files):
            return jsonify({'success': False, 'error': 'No files selected'}), 400
        
        # Create uploads directory
        upload_dir = os.path.join(app.config.get('UPLOAD_FOLDER', 'uploads'))
        os.makedirs(upload_dir, exist_ok=True)
        
        analyzed_files = {}
        
        for file in files:
            if file and file.filename:
                # Secure filename and save
                filename = secure_filename(file.filename)
                file_key = str(uuid.uuid4())
                file_path = os.path.join(upload_dir, f"{file_key}_{filename}")
                file.save(file_path)
                
                # Analyze the file
                analysis = analyze_excel_structure(file_path)
                analysis['file_path'] = file_path
                analysis['file_key'] = file_key
                
                # Store in memory (use database in production)
                uploaded_files[file_key] = {
                    'file_path': file_path,
                    'filename': filename,
                    'analysis': analysis
                }
                
                analyzed_files[file_key] = analysis
        
        return jsonify({
            'success': True,
            'files': analyzed_files,
            'message': f'Analyzed {len(analyzed_files)} files successfully'
        })
        
    except Exception as e:
        logger.error(f"Error analyzing Excel files: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_sheet_data', methods=['POST'])
def api_get_sheet_data():
    """Get data for a specific sheet"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        sheet_data = excel_processor.get_sheet_data(file_path, sheet_name)
        
        if 'error' in sheet_data:
            return jsonify({'success': False, 'error': sheet_data['error']}), 500
        
        return jsonify({
            'success': True,
            'sheet_data': sheet_data
        })
        
    except Exception as e:
        logger.error(f"Error getting sheet data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract_data', methods=['POST'])
def api_extract_data():
    """Extract data based on selections"""
    try:
        data = request.json
        file_key = data.get('file_key')
        selections = data.get('selections', [])
        
        if not file_key or not selections:
            return jsonify({'success': False, 'error': 'File key and selections required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        
        # Create selection config
        selection_config = {
            'sheets': []
        }
        
        # Group selections by sheet
        sheets_dict = {}
        for selection in selections:
            sheet_name = selection['sheet_name']
            if sheet_name not in sheets_dict:
                sheets_dict[sheet_name] = []
            sheets_dict[sheet_name].append(selection)
        
        # Format for processor
        for sheet_name, sheet_selections in sheets_dict.items():
            selection_config['sheets'].append({
                'name': sheet_name,
                'selections': sheet_selections
            })
        
        # Extract data
        extracted_data = excel_processor.extract_data_with_selection(file_path, selection_config)
        
        return jsonify({
            'success': True,
            'extracted_data': extracted_data,
            'count': len(extracted_data)
        })
        
    except Exception as e:
        logger.error(f"Error extracting data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_extracted_data', methods=['POST'])
def api_save_extracted_data():
    """Save extracted data as test cases"""
    try:
        data = request.json
        test_cases_data = data.get('test_cases', [])
        
        if not test_cases_data:
            return jsonify({'success': False, 'error': 'No test cases to save'}), 400
        
        saved_count = 0
        errors = []
        
        for tc_data in test_cases_data:
            try:
                # Use upsert to handle duplicates
                test_case = test_case_service.upsert_test_case(tc_data)
                saved_count += 1
            except Exception as e:
                errors.append(f"Error saving test case {tc_data.get('id', 'unknown')}: {str(e)}")
        
        return jsonify({
            'success': True,
            'saved_count': saved_count,
            'errors': errors,
            'message': f'Saved {saved_count} test cases successfully'
        })
        
    except Exception as e:
        logger.error(f"Error saving extracted data: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test-case-manager')
def test_case_manager():
    """Test case management interface"""
    return render_template('test_case_manager.html')

@app.route('/api/test_cases')
def api_get_test_cases():
    """Get all test cases with statistics"""
    try:
        test_cases = test_case_service.get_all_test_cases()
        stats = test_case_service.get_statistics()
        
        return jsonify({
            'success': True,
            'test_cases': [tc.to_dict() for tc in test_cases],
            'statistics': stats.to_dict()
        })
    except Exception as e:
        logger.error(f"Error getting test cases: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_cases/<case_id>', methods=['PUT'])
def api_update_test_case(case_id):
    """Update a test case"""
    try:
        updates = request.json
        if not updates:
            return jsonify({'success': False, 'error': 'No update data provided'}), 400
        
        updated_case = test_case_service.update_test_case(case_id, updates)
        
        return jsonify({
            'success': True,
            'test_case': updated_case.to_dict(),
            'message': f'Test case {case_id} updated successfully'
        })
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error updating test case {case_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test_cases/<case_id>', methods=['DELETE'])
def api_delete_test_case(case_id):
    """Delete a test case"""
    try:
        purpose = request.args.get('purpose')
        
        if test_case_service.delete_test_case(case_id, purpose):
            return jsonify({
                'success': True,
                'message': f'Test case {case_id} deleted successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'Test case not found'}), 404
            
    except Exception as e:
        logger.error(f"Error deleting test case {case_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/save_config', methods=['POST'])
def api_save_config():
    """Save selection configuration"""
    try:
        config = request.json
        config_name = config.get('name')
        
        if not config_name:
            return jsonify({'success': False, 'error': 'Configuration name required'}), 400
        
        success = excel_processor.save_selection_config(config_name, config)
        
        return jsonify({
            'success': success,
            'message': 'Configuration saved successfully' if success else 'Failed to save configuration'
        })
        
    except Exception as e:
        logger.error(f"Error saving configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/get_configs')
def api_get_configs():
    """Get available configurations"""
    try:
        configs = excel_processor.get_available_configs()
        config_details = []
        
        for config_name in configs:
            config = excel_processor.load_selection_config(config_name)
            if config:
                config_details.append(config)
        
        return jsonify({
            'success': True,
            'configs': config_details
        })
        
    except Exception as e:
        logger.error(f"Error getting configurations: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/load_config', methods=['POST'])
def api_load_config():
    """Load a saved configuration"""
    try:
        data = request.json
        config_name = data.get('name')
        
        if not config_name:
            return jsonify({'success': False, 'error': 'Configuration name required'}), 400
        
        config = excel_processor.load_selection_config(config_name)
        
        if not config:
            return jsonify({'success': False, 'error': 'Configuration not found'}), 404
        
        return jsonify({
            'success': True,
            'config': config
        })
        
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai_analyze_sheet', methods=['POST'])
def api_ai_analyze_sheet():
    """Get AI-enhanced analysis of a specific sheet"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        analysis = excel_processor.get_ai_enhanced_sheet_analysis(file_path, sheet_name)
        
        if 'error' in analysis:
            return jsonify({'success': False, 'error': analysis['error']}), 500
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        logger.error(f"Error in AI sheet analysis: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/ai_suggest_mapping', methods=['POST'])
def api_ai_suggest_mapping():
    """Get AI suggestions for field mapping"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        header_row = data.get('header_row', 0)
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        suggestions = excel_processor.get_ai_field_mapping_suggestions(file_path, sheet_name, header_row)
        
        if 'error' in suggestions:
            return jsonify({'success': False, 'error': suggestions['error']}), 500
        
        return jsonify({
            'success': True,
            'suggestions': suggestions
        })
        
    except Exception as e:
        logger.error(f"Error getting AI mapping suggestions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/generate_extraction_logic', methods=['POST'])
def api_generate_extraction_logic():
    """Generate AI-powered extraction logic for test cases"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        extraction_logic = excel_processor.generate_extraction_logic(file_path, sheet_name)
        
        if 'error' in extraction_logic:
            return jsonify({'success': False, 'error': extraction_logic['error']}), 500
        
        return jsonify({
            'success': True,
            'extraction_logic': extraction_logic
        })
        
    except Exception as e:
        logger.error(f"Error generating extraction logic: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/preview_smart_extraction', methods=['POST'])
def api_preview_smart_extraction():
    """Preview smart extraction results"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        extraction_logic = data.get('extraction_logic')
        max_rows = data.get('max_rows', 5)
        
        if not file_key or not sheet_name or not extraction_logic:
            return jsonify({'success': False, 'error': 'File key, sheet name, and extraction logic required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        preview_result = excel_processor.preview_smart_extraction(file_path, sheet_name, extraction_logic, max_rows)
        
        if 'error' in preview_result:
            return jsonify({'success': False, 'error': preview_result['error']}), 500
        
        return jsonify({
            'success': True,
            'preview': preview_result
        })
        
    except Exception as e:
        logger.error(f"Error previewing smart extraction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract_test_cases_smart', methods=['POST'])
def api_extract_test_cases_smart():
    """Extract test cases using AI-generated logic with merged cell handling"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        extraction_logic = data.get('extraction_logic')
        
        if not file_key or not sheet_name or not extraction_logic:
            return jsonify({'success': False, 'error': 'File key, sheet name, and extraction logic required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        extraction_result = excel_processor.extract_test_cases_smart(file_path, sheet_name, extraction_logic)
        
        if 'error' in extraction_result:
            return jsonify({'success': False, 'error': extraction_result['error']}), 500
        
        return jsonify({
            'success': True,
            'extraction_result': extraction_result
        })
        
    except Exception as e:
        logger.error(f"Error in smart test case extraction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/find_template_header', methods=['POST'])
def api_find_template_header():
    """Find the header row for template extraction"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        header_result = excel_processor.find_template_header(file_path, sheet_name)
        
        if 'error' in header_result:
            return jsonify({'success': False, 'error': header_result['error']}), 500
        
        return jsonify({
            'success': True,
            'header_result': header_result
        })
        
    except Exception as e:
        logger.error(f"Error finding template header: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/preview_template_extraction', methods=['POST'])
def api_preview_template_extraction():
    """Preview template extraction results"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        max_rows = data.get('max_rows', 5)
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        preview_result = excel_processor.preview_template_extraction(file_path, sheet_name, max_rows)
        
        if 'error' in preview_result:
            return jsonify({'success': False, 'error': preview_result['error']}), 500
        
        return jsonify({
            'success': True,
            'preview': preview_result
        })
        
    except Exception as e:
        logger.error(f"Error previewing template extraction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/extract_test_cases_template', methods=['POST'])
def api_extract_test_cases_template():
    """Extract test cases using template-based logic"""
    try:
        data = request.json
        file_key = data.get('file_key')
        sheet_name = data.get('sheet_name')
        
        if not file_key or not sheet_name:
            return jsonify({'success': False, 'error': 'File key and sheet name required'}), 400
        
        if file_key not in uploaded_files:
            return jsonify({'success': False, 'error': 'File not found'}), 404
        
        file_path = uploaded_files[file_key]['file_path']
        extraction_result = excel_processor.extract_test_cases_template(file_path, sheet_name)
        
        if 'error' in extraction_result:
            return jsonify({'success': False, 'error': extraction_result['error']}), 500
        
        return jsonify({
            'success': True,
            'extraction_result': extraction_result
        })
        
    except Exception as e:
        logger.error(f"Error in template test case extraction: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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