// Test Case Manager JavaScript

let currentTestCases = [];
let filteredTestCases = [];
let currentPage = 1;
const itemsPerPage = 20;

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    loadAllTestCases();
    setupEventListeners();
});

function setupEventListeners() {
    // Search input with debounce
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(searchTestCases, 300);
    });
    
    // Filter dropdowns
    document.getElementById('purposeFilter').addEventListener('change', searchTestCases);
    document.getElementById('testDataFilter').addEventListener('change', searchTestCases);
    
    // Enter key in search
    document.getElementById('searchInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchTestCases();
        }
    });
}

function loadAllTestCases() {
    showLoading();
    
    fetch('/api/test_cases')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                currentTestCases = data.test_cases;
                filteredTestCases = [...currentTestCases];
                updateStatistics(data.statistics);
                populateFilters();
                displayTestCases();
            } else {
                showError('Failed to load test cases: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error loading test cases:', error);
            showError('Error loading test cases: ' + error.message);
        });
}

function searchTestCases() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const purposeFilter = document.getElementById('purposeFilter').value;
    const testDataFilter = document.getElementById('testDataFilter').value;
    
    filteredTestCases = currentTestCases.filter(tc => {
        const matchesSearch = !searchTerm || 
            tc.id.toLowerCase().includes(searchTerm) ||
            tc.purpose.toLowerCase().includes(searchTerm) ||
            tc.scenerio.toLowerCase().includes(searchTerm) ||
            tc.test_data.toLowerCase().includes(searchTerm) ||
            tc.steps.some(step => step.toLowerCase().includes(searchTerm)) ||
            tc.expected.some(exp => exp.toLowerCase().includes(searchTerm)) ||
            tc.note.toLowerCase().includes(searchTerm);
        
        const matchesPurpose = !purposeFilter || tc.purpose === purposeFilter;
        const matchesTestData = !testDataFilter || tc.test_data === testDataFilter;
        
        return matchesSearch && matchesPurpose && matchesTestData;
    });
    
    currentPage = 1;
    displayTestCases();
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('purposeFilter').value = '';
    document.getElementById('testDataFilter').value = '';
    filteredTestCases = [...currentTestCases];
    currentPage = 1;
    displayTestCases();
}

function populateFilters() {
    // Populate purpose filter
    const purposes = [...new Set(currentTestCases.map(tc => tc.purpose))].sort();
    const purposeSelect = document.getElementById('purposeFilter');
    purposeSelect.innerHTML = '<option value="">All Purposes</option>';
    purposes.forEach(purpose => {
        const option = document.createElement('option');
        option.value = purpose;
        option.textContent = purpose;
        purposeSelect.appendChild(option);
    });
    
    // Populate test data filter
    const testDataSources = [...new Set(currentTestCases.map(tc => tc.test_data))].sort();
    const testDataSelect = document.getElementById('testDataFilter');
    testDataSelect.innerHTML = '<option value="">All Test Data</option>';
    testDataSources.forEach(source => {
        const option = document.createElement('option');
        option.value = source;
        option.textContent = source;
        testDataSelect.appendChild(option);
    });
}

function updateStatistics(stats) {
    document.getElementById('totalCases').textContent = stats.total_cases;
    document.getElementById('uniquePurposes').textContent = Object.keys(stats.purposes).length;
    document.getElementById('avgSteps').textContent = stats.avg_steps;
    document.getElementById('avgExpected').textContent = stats.avg_expected;
}

function displayTestCases() {
    const tbody = document.getElementById('testCasesTableBody');
    const resultsCount = document.getElementById('resultsCount');
    
    // Update results count
    resultsCount.textContent = `${filteredTestCases.length} results`;
    
    if (filteredTestCases.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center text-muted">
                    <i class="fas fa-search"></i> No test cases found
                </td>
            </tr>
        `;
        hidePagination();
        return;
    }
    
    // Calculate pagination
    const totalPages = Math.ceil(filteredTestCases.length / itemsPerPage);
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageTestCases = filteredTestCases.slice(startIndex, endIndex);
    
    // Generate table rows
    tbody.innerHTML = pageTestCases.map(tc => `
        <tr>
            <td>
                <code>${escapeHtml(tc.id)}</code>
            </td>
            <td>
                <span class="text-truncate d-inline-block" style="max-width: 200px;" title="${escapeHtml(tc.purpose)}">
                    ${escapeHtml(tc.purpose)}
                </span>
            </td>
            <td>
                <span class="text-truncate d-inline-block" style="max-width: 200px;" title="${escapeHtml(tc.scenerio)}">
                    ${escapeHtml(tc.scenerio)}
                </span>
            </td>
            <td>
                <span class="badge bg-secondary">${escapeHtml(tc.test_data)}</span>
            </td>
            <td>
                <span class="badge bg-info">${tc.steps.length} steps</span>
            </td>
            <td>
                <span class="badge bg-success">${tc.expected.length} expected</span>
            </td>
            <td>
                <small class="text-muted">${formatDate(tc.created_at)}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-primary" onclick="viewTestCase('${escapeHtml(tc.id)}', '${escapeHtml(tc.purpose)}')" title="View">
                        <i class="fas fa-eye"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="editTestCase('${escapeHtml(tc.id)}', '${escapeHtml(tc.purpose)}')" title="Edit">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteTestCase('${escapeHtml(tc.id)}', '${escapeHtml(tc.purpose)}')" title="Delete">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
    
    // Update pagination
    if (totalPages > 1) {
        updatePagination(totalPages);
    } else {
        hidePagination();
    }
}

function updatePagination(totalPages) {
    const pagination = document.getElementById('pagination');
    const paginationNav = document.getElementById('paginationNav');
    
    let paginationHTML = '';
    
    // Previous button
    paginationHTML += `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage - 1})">Previous</a>
        </li>
    `;
    
    // Page numbers
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(totalPages, currentPage + 2);
    
    if (startPage > 1) {
        paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(1)">1</a></li>`;
        if (startPage > 2) {
            paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        paginationHTML += `
            <li class="page-item ${i === currentPage ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>
        `;
    }
    
    if (endPage < totalPages) {
        if (endPage < totalPages - 1) {
            paginationHTML += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
        paginationHTML += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${totalPages})">${totalPages}</a></li>`;
    }
    
    // Next button
    paginationHTML += `
        <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${currentPage + 1})">Next</a>
        </li>
    `;
    
    pagination.innerHTML = paginationHTML;
    paginationNav.style.display = 'block';
}

function hidePagination() {
    document.getElementById('paginationNav').style.display = 'none';
}

function changePage(page) {
    const totalPages = Math.ceil(filteredTestCases.length / itemsPerPage);
    if (page >= 1 && page <= totalPages) {
        currentPage = page;
        displayTestCases();
    }
}

function viewTestCase(id, purpose) {
    window.open(`/test-case/${encodeURIComponent(id)}`, '_blank');
}

function editTestCase(id, purpose) {
    const testCase = currentTestCases.find(tc => tc.id === id && tc.purpose === purpose);
    if (!testCase) {
        showError('Test case not found');
        return;
    }
    
    // Populate edit form
    document.getElementById('editTestCaseId').value = testCase.id;
    document.getElementById('editTestCasePurpose').value = testCase.purpose;
    document.getElementById('editId').value = testCase.id;
    document.getElementById('editPurpose').value = testCase.purpose;
    document.getElementById('editScenario').value = testCase.scenerio;
    document.getElementById('editTestData').value = testCase.test_data;
    document.getElementById('editSteps').value = testCase.steps.join('\n');
    document.getElementById('editExpected').value = testCase.expected.join('\n');
    document.getElementById('editNote').value = testCase.note;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('editTestCaseModal'));
    modal.show();
}

function saveTestCase() {
    const id = document.getElementById('editTestCaseId').value;
    const purpose = document.getElementById('editTestCasePurpose').value;
    
    const updatedData = {
        scenerio: document.getElementById('editScenario').value.trim(),
        test_data: document.getElementById('editTestData').value.trim(),
        steps: document.getElementById('editSteps').value.split('\n').map(s => s.trim()).filter(s => s),
        expected: document.getElementById('editExpected').value.split('\n').map(s => s.trim()).filter(s => s),
        note: document.getElementById('editNote').value.trim()
    };
    
    // Validate
    if (!updatedData.scenerio || !updatedData.test_data || !updatedData.steps.length || !updatedData.expected.length) {
        showError('Please fill in all required fields');
        return;
    }
    
    fetch(`/api/test_cases/${encodeURIComponent(id)}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(updatedData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Test case updated successfully');
            bootstrap.Modal.getInstance(document.getElementById('editTestCaseModal')).hide();
            loadAllTestCases();
        } else {
            showError('Failed to update test case: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error updating test case:', error);
        showError('Error updating test case: ' + error.message);
    });
}

function deleteTestCase(id, purpose) {
    document.getElementById('deleteTestCaseId').textContent = id;
    document.getElementById('deleteTestCasePurpose').textContent = purpose;
    
    // Store for deletion
    window.deleteTestCaseData = { id, purpose };
    
    const modal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    modal.show();
}

function confirmDelete() {
    const { id, purpose } = window.deleteTestCaseData;
    
    fetch(`/api/test_cases/${encodeURIComponent(id)}?purpose=${encodeURIComponent(purpose)}`, {
        method: 'DELETE'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccess('Test case deleted successfully');
            bootstrap.Modal.getInstance(document.getElementById('deleteConfirmModal')).hide();
            loadAllTestCases();
        } else {
            showError('Failed to delete test case: ' + data.error);
        }
    })
    .catch(error => {
        console.error('Error deleting test case:', error);
        showError('Error deleting test case: ' + error.message);
    });
}

function showLoading() {
    const tbody = document.getElementById('testCasesTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="8" class="text-center">
                <i class="fas fa-spinner fa-spin"></i> Loading test cases...
            </td>
        </tr>
    `;
}

function showError(message) {
    // Create toast or alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-danger alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function showSuccess(message) {
    // Create toast or alert
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertDiv);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    } catch (e) {
        return dateString;
    }
}