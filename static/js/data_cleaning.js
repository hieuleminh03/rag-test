// Simplified Data Cleaning Interface JavaScript

let uploadedFiles = {};
let currentFileKey = null;
let selectedSheets = new Set();
let extractedTestCases = [];

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // File input change
    document.getElementById('excelFiles').addEventListener('change', function() {
        const uploadBtn = document.querySelector('button[onclick="uploadFiles()"]');
        if (uploadBtn) {
            uploadBtn.disabled = this.files.length === 0;
        }
    });
}

function uploadFiles() {
    const fileInput = document.getElementById('excelFiles');
    const files = fileInput.files;
    
    if (files.length === 0) {
        showError('Please select at least one file');
        return;
    }
    
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    
    showLoading('Analyzing files...');
    
    fetch('/api/analyze_excel', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Response data:', data);
        console.log('Data.success:', data.success);
        console.log('Data.files:', data.files);
        
        // Always hide loading first
        hideLoading();
        
        if (data && (data.success === true || data.files)) {
            uploadedFiles = data.files || {};
            console.log('uploadedFiles set to:', uploadedFiles);
            displayFileAnalysis(data.files || {});
            showSheetSelection();
        } else {
            console.error('API response indicates failure:', data);
            showError('Error analyzing files: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error uploading files:', error);
        hideLoading();
        showError('Error uploading files: ' + error.message);
    });
}

function displayFileAnalysis(files) {
    const resultsDiv = document.getElementById('analysisResults');
    const fileAnalysisDiv = document.getElementById('fileAnalysis');
    
    let html = '<div class="row">';
    
    Object.keys(files).forEach(fileKey => {
        const file = files[fileKey];
        
        if (file.error) {
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-danger">
                        <div class="card-header bg-danger text-white">
                            <h6><i class="fas fa-exclamation-triangle"></i> Error: ${escapeHtml(file.filename || 'Unknown file')}</h6>
                        </div>
                        <div class="card-body">
                            <p class="text-danger">${escapeHtml(file.error)}</p>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // Handle the simplified structure from analyze_excel_structure
            const sheets = file.sheets || [];
            html += `
                <div class="col-md-6 mb-3">
                    <div class="card border-success">
                        <div class="card-header bg-success text-white">
                            <h6><i class="fas fa-file-excel"></i> ${escapeHtml(file.filename)}</h6>
                        </div>
                        <div class="card-body">
                            <p><strong>Sheets:</strong> ${sheets.length}</p>
                            <p><strong>File Type:</strong> ${escapeHtml(file.file_type || 'Excel/ODS')}</p>
                            ${sheets.length > 0 ? `
                                <p><strong>Sheet Names:</strong></p>
                                <ul class="list-unstyled">
                                    ${sheets.map(sheet => `<li><i class="fas fa-table"></i> ${escapeHtml(sheet.name)} (${sheet.rows} rows)</li>`).join('')}
                                </ul>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }
    });
    
    html += '</div>';
    resultsDiv.innerHTML = html;
    fileAnalysisDiv.style.display = 'block';
}

function showSheetSelection() {
    const sheetSelectionDiv = document.getElementById('sheetSelection');
    const fileSelector = document.getElementById('fileSelector');
    
    // Populate file selector
    fileSelector.innerHTML = '<option value="">Select a file...</option>';
    Object.keys(uploadedFiles).forEach(fileKey => {
        const file = uploadedFiles[fileKey];
        const analysis = file.analysis || file;
        if (!analysis.error && analysis.sheets && analysis.sheets.length > 0) {
            const option = document.createElement('option');
            option.value = fileKey;
            option.textContent = analysis.filename || file.filename;
            fileSelector.appendChild(option);
        }
    });
    
    sheetSelectionDiv.style.display = 'block';
    
    // Auto-select first file if only one
    const validFiles = Object.keys(uploadedFiles).filter(key => {
        const file = uploadedFiles[key];
        const analysis = file.analysis || file;
        return !analysis.error && analysis.sheets && analysis.sheets.length > 0;
    });
    if (validFiles.length === 1) {
        fileSelector.value = validFiles[0];
        switchFile();
    }
}

function switchFile() {
    const fileSelector = document.getElementById('fileSelector');
    const sheetList = document.getElementById('sheetList');
    const sheetPreview = document.getElementById('sheetPreview');
    
    currentFileKey = fileSelector.value;
    selectedSheets.clear();
    
    if (!currentFileKey || !uploadedFiles[currentFileKey]) {
        sheetList.innerHTML = '';
        sheetPreview.innerHTML = '<p class="text-muted">Select a file first</p>';
        updateExtractButton();
        return;
    }
    
    const file = uploadedFiles[currentFileKey];
    const analysis = file.analysis || file;
    if (!analysis.sheets || analysis.sheets.length === 0) {
        sheetList.innerHTML = '<p class="text-danger">No sheets found in this file</p>';
        sheetPreview.innerHTML = '<p class="text-danger">No sheets available</p>';
        updateExtractButton();
        return;
    }
    
    // Display sheets as checkboxes
    let html = '';
    analysis.sheets.forEach((sheet, index) => {
        html += `
            <div class="list-group-item">
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" id="sheet_${index}" 
                           value="${escapeHtml(sheet.name)}" onchange="toggleSheet('${escapeHtml(sheet.name)}')">
                    <label class="form-check-label" for="sheet_${index}">
                        <strong>${escapeHtml(sheet.name)}</strong>
                        <br><small class="text-muted">${sheet.rows} rows × ${sheet.cols || 'unknown'} columns</small>
                    </label>
                </div>
            </div>
        `;
    });
    
    sheetList.innerHTML = html;
    sheetPreview.innerHTML = '<p class="text-muted">Select sheets to extract test cases from multiple sheets at once.</p>';
    updateExtractButton();
}

function toggleSheet(sheetName) {
    if (selectedSheets.has(sheetName)) {
        selectedSheets.delete(sheetName);
    } else {
        selectedSheets.add(sheetName);
    }
    updateExtractButton();
    updateSheetPreview();
}

function updateExtractButton() {
    const extractBtn = document.getElementById('extractBtn');
    if (extractBtn) {
        extractBtn.disabled = selectedSheets.size === 0;
    }
}

function updateSheetPreview() {
    const sheetPreview = document.getElementById('sheetPreview');
    
    if (selectedSheets.size === 0) {
        sheetPreview.innerHTML = '<p class="text-muted">Select sheets from the left to extract test cases. Multiple sheets can be selected.</p>';
    } else {
        sheetPreview.innerHTML = `
            <div class="alert alert-info">
                <h6><i class="fas fa-info-circle"></i> Selected Sheets (${selectedSheets.size})</h6>
                <ul class="mb-0">
                    ${Array.from(selectedSheets).map(name => `<li>${escapeHtml(name)}</li>`).join('')}
                </ul>
                <hr class="my-2">
                <small>Click "Extract Test Cases" to process these sheets using rule-based extraction.</small>
            </div>
        `;
    }
}

function extractFromSelectedSheets() {
    if (!currentFileKey || selectedSheets.size === 0) {
        showError('Please select at least one sheet');
        return;
    }
    
    showLoading('Extracting test cases from selected sheets...');
    
    const requests = Array.from(selectedSheets).map(sheetName => {
        return fetch('/api/extract_test_cases_template', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_key: currentFileKey,
                sheet_name: sheetName
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                return {
                    sheet_name: sheetName,
                    test_cases: data.extraction_result.test_cases || [],
                    success: true
                };
            } else {
                return {
                    sheet_name: sheetName,
                    error: data.error,
                    success: false
                };
            }
        })
        .catch(error => {
            return {
                sheet_name: sheetName,
                error: error.message,
                success: false
            };
        });
    });
    
    Promise.all(requests)
        .then(results => {
            hideLoading();
            
            // Combine all successful extractions
            extractedTestCases = [];
            let successCount = 0;
            let errorCount = 0;
            let errors = [];
            
            results.forEach(result => {
                if (result.success) {
                    extractedTestCases.push(...result.test_cases);
                    successCount++;
                } else {
                    errorCount++;
                    errors.push(`${result.sheet_name}: ${result.error}`);
                }
            });
            
            if (extractedTestCases.length > 0) {
                displayExtractedTestCases();
                showSuccess(`Extracted ${extractedTestCases.length} test cases from ${successCount} sheets`);
                
                if (errorCount > 0) {
                    showError(`Failed to extract from ${errorCount} sheets:\n${errors.join('\n')}`);
                }
            } else {
                showError('No test cases were extracted. Please check your sheet format.');
                if (errors.length > 0) {
                    showError('Errors:\n' + errors.join('\n'));
                }
            }
        })
        .catch(error => {
            hideLoading();
            console.error('Error during extraction:', error);
            showError('Error during extraction: ' + error.message);
        });
}

function displayExtractedTestCases() {
    const extractedView = document.getElementById('extractedTestCasesView');
    const previewDiv = document.getElementById('extractedDataPreview');
    const statsSpan = document.getElementById('extractionStats');
    const saveBtn = document.getElementById('saveBtn');
    
    // Update stats
    statsSpan.textContent = `${extractedTestCases.length} test cases extracted`;
    
    // Enable save button
    saveBtn.disabled = false;
    
    // Display test cases in a table
    let html = `
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Purpose</th>
                        <th>Scenario</th>
                        <th>Test Data</th>
                        <th>Steps</th>
                        <th>Expected</th>
                        <th>Note</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    extractedTestCases.forEach((tc, index) => {
        html += `
            <tr>
                <td><code>${escapeHtml(tc.id || '')}</code></td>
                <td>${escapeHtml(tc.purpose || '')}</td>
                <td>${escapeHtml(tc.scenerio || '')}</td>
                <td><span class="badge bg-secondary">${escapeHtml(tc.test_data || '')}</span></td>
                <td>
                    <span class="badge bg-info">${(tc.steps || []).length} steps</span>
                    ${(tc.steps || []).length > 0 ? `
                        <button class="btn btn-sm btn-outline-info ms-1" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#steps_${index}">
                            <i class="fas fa-eye"></i>
                        </button>
                        <div class="collapse mt-2" id="steps_${index}">
                            <div class="small">
                                ${(tc.steps || []).map(step => `<div>${escapeHtml(step)}</div>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                </td>
                <td>
                    <span class="badge bg-success">${(tc.expected || []).length} expected</span>
                    ${(tc.expected || []).length > 0 ? `
                        <button class="btn btn-sm btn-outline-success ms-1" type="button" 
                                data-bs-toggle="collapse" data-bs-target="#expected_${index}">
                            <i class="fas fa-eye"></i>
                        </button>
                        <div class="collapse mt-2" id="expected_${index}">
                            <div class="small">
                                ${(tc.expected || []).map(exp => `<div>${escapeHtml(exp)}</div>`).join('')}
                            </div>
                        </div>
                    ` : ''}
                </td>
                <td>${escapeHtml(tc.note || '')}</td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
    `;
    
    previewDiv.innerHTML = html;
    extractedView.style.display = 'block';
}

function saveExtractedData() {
    if (extractedTestCases.length === 0) {
        showError('No test cases to save');
        return;
    }
    
    showLoading('Saving test cases to database...');
    
    fetch('/api/save_extracted_data', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            test_cases: extractedTestCases
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showSuccess(`Successfully saved ${data.saved_count} test cases to database`);
            if (data.errors && data.errors.length > 0) {
                showError('Some errors occurred:\n' + data.errors.join('\n'));
            }
            
            // Disable save button to prevent duplicate saves
            document.getElementById('saveBtn').disabled = true;
        } else {
            showError('Failed to save test cases: ' + data.error);
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Error saving test cases:', error);
        showError('Error saving test cases: ' + error.message);
    });
}

// Utility functions
function showLoading(message = 'Loading...') {
    console.log('showLoading() called with message:', message);
    // Create or update loading overlay
    let overlay = document.getElementById('loadingOverlay');
    if (!overlay) {
        console.log('Creating new loading overlay');
        overlay = document.createElement('div');
        overlay.id = 'loadingOverlay';
        overlay.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        overlay.style.cssText = 'background: rgba(0,0,0,0.5); z-index: 9999;';
        overlay.innerHTML = `
            <div class="bg-white p-4 rounded shadow">
                <div class="text-center">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <div class="mt-2" id="loadingMessage">${message}</div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
        console.log('Loading overlay created and added to body');
    } else {
        console.log('Updating existing loading overlay');
        document.getElementById('loadingMessage').textContent = message;
        overlay.style.display = 'flex';
        console.log('Loading overlay shown');
    }
}

function hideLoading() {
    console.log('hideLoading() called');
    const overlay = document.getElementById('loadingOverlay');
    console.log('Loading overlay element:', overlay);
    if (overlay) {
        overlay.style.display = 'none !important';
        overlay.style.visibility = 'hidden';
        overlay.remove(); // Just remove it completely
        console.log('Loading overlay hidden and removed');
    } else {
        console.log('No loading overlay found to hide');
    }
}

function showError(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i> ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 8000);
}

function showSuccess(message) {
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        <i class="fas fa-check-circle"></i> ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}