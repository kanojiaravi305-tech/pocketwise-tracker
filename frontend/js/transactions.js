/**
 * frontend/js/transactions.js
 * Handles Expense CRUD, multi-filter searching, pagination, and CSV Statement Export.
 */

let currentPage = 1;
const pageSize = 10;
let categoriesList = [];

// Bootstrap Modal instances
let expenseModalInstance = null;
let deleteModalInstance = null;

document.addEventListener('DOMContentLoaded', async function() {
    expenseModalInstance = new bootstrap.Modal(document.getElementById('expenseModal'));
    deleteModalInstance = new bootstrap.Modal(document.getElementById('deleteModal'));

    // Set today's date in add expense date picker
    document.getElementById('expenseDate').value = new Date().toISOString().split('T')[0];

    // Load categories for filter & modal dropdowns
    await loadCategories();

    // Initial expenses load
    loadExpenses(1);

    // Filter event listeners
    document.getElementById('filterMonth').addEventListener('change', () => loadExpenses(1));
    document.getElementById('filterCategory').addEventListener('change', () => loadExpenses(1));
    document.getElementById('filterMode').addEventListener('change', () => loadExpenses(1));
    
    // Debounce search input
    let searchTimeout = null;
    document.getElementById('filterSearch').addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => loadExpenses(1), 350);
    });

    document.getElementById('resetFiltersBtn').addEventListener('click', resetFilters);

    // Modal Add button click
    document.getElementById('openAddModalBtn').addEventListener('click', openAddModal);

    // Save Expense Form Submit
    document.getElementById('expenseForm').addEventListener('submit', handleSaveExpense);

    // Delete Confirmation
    document.getElementById('confirmDeleteBtn').addEventListener('click', handleConfirmDelete);

    // CSV Export button
    document.getElementById('exportCsvBtn').addEventListener('click', handleExportCsv);
});


async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        const data = await res.json();
        if (data.success) {
            categoriesList = data.categories;
            populateCategorySelects();
        }
    } catch (err) {
        console.error('Failed to load categories:', err);
    }
}

function populateCategorySelects() {
    const filterSelect = document.getElementById('filterCategory');
    const formSelect = document.getElementById('expenseCategory');

    filterSelect.innerHTML = '<option value="">All Categories</option>';
    formSelect.innerHTML = '<option value="">Select Category</option>';

    categoriesList.forEach(c => {
        filterSelect.innerHTML += `<option value="${c.category_id}">${escapeHtml(c.category_name)}</option>`;
        formSelect.innerHTML += `<option value="${c.category_id}">${escapeHtml(c.category_name)}</option>`;
    });
}

function resetFilters() {
    document.getElementById('filterMonth').value = '';
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterMode').value = '';
    document.getElementById('filterSearch').value = '';
    loadExpenses(1);
}

async function loadExpenses(page = 1) {
    currentPage = page;
    const tbody = document.getElementById('expensesTableBody');
    tbody.innerHTML = `
        <tr>
            <td colspan="7" class="text-center py-4 text-muted">
                <span class="spinner-border spinner-border-sm me-1"></span>Loading transaction records...
            </td>
        </tr>
    `;

    const month = document.getElementById('filterMonth').value;
    const category_id = document.getElementById('filterCategory').value;
    const payment_mode = document.getElementById('filterMode').value;
    const search = document.getElementById('filterSearch').value.trim();

    const params = new URLSearchParams({
        page: currentPage,
        page_size: pageSize
    });
    if (month) params.append('month', month);
    if (category_id) params.append('category_id', category_id);
    if (payment_mode) params.append('payment_mode', payment_mode);
    if (search) params.append('search', search);

    try {
        const res = await fetch(`/api/expenses?${params.toString()}`);
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!data.success) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Error: ${escapeHtml(data.message)}</td></tr>`;
            return;
        }

        renderTableRows(data.expenses);
        renderPagination(data.pagination);

    } catch (err) {
        console.error('Error loading expenses:', err);
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to connect to server.</td></tr>`;
    }
}

function renderTableRows(expenses) {
    const tbody = document.getElementById('expensesTableBody');
    if (!expenses || expenses.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-5 text-muted">
                    <i class="bi bi-inbox fs-2 d-block mb-2"></i>
                    No expense records found matching current filters.
                </td>
            </tr>
        `;
        return;
    }

    let html = '';
    expenses.forEach(e => {
        const modeClass = e.payment_mode === 'UPI' ? 'badge-mode-upi' : (e.payment_mode === 'Cash' ? 'badge-mode-cash' : 'badge-mode-card');
        html += `
            <tr>
                <td class="text-nowrap text-secondary">${e.expense_date}</td>
                <td class="fw-semibold text-dark">${escapeHtml(e.title)}</td>
                <td>
                    <span class="badge-category" style="background-color: ${e.color_code}15; color: ${e.color_code};">
                        <i class="bi ${e.icon_name || 'bi-tag'}"></i> ${escapeHtml(e.category_name)}
                    </span>
                </td>
                <td>
                    <span class="badge-mode ${modeClass}">${e.payment_mode}</span>
                </td>
                <td class="text-muted small">${escapeHtml(e.notes || '-')}</td>
                <td class="text-end fw-bold text-dark text-nowrap">
                    ₹${e.amount.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
                <td class="text-center text-nowrap">
                    <button class="btn btn-sm btn-outline-primary py-0 px-2 me-1" onclick="openEditModal('${e.expense_id}')" title="Edit">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger py-0 px-2" onclick="openDeleteModal('${e.expense_id}')" title="Delete">
                        <i class="bi bi-trash3"></i>
                    </button>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function renderPagination(pagination) {
    const recordBadge = document.getElementById('recordCountBadge');
    const pageInfo = document.getElementById('pageInfoText');
    const summary = document.getElementById('paginationSummary');
    const controls = document.getElementById('paginationControls');

    const totalRecords = pagination.total_records;
    const totalPages = pagination.total_pages;
    const page = pagination.page;

    recordBadge.textContent = `${totalRecords} record${totalRecords === 1 ? '' : 's'}`;
    pageInfo.textContent = `Page ${page} of ${totalPages || 1}`;

    const startEntry = totalRecords === 0 ? 0 : (page - 1) * pageSize + 1;
    const endEntry = Math.min(page * pageSize, totalRecords);
    summary.textContent = `Showing ${startEntry} to ${endEntry} of ${totalRecords} entries`;

    if (totalPages <= 1) {
        controls.innerHTML = '';
        return;
    }

    let ctrlHtml = '';
    // Previous button
    ctrlHtml += `
        <li class="page-item ${page === 1 ? 'disabled' : ''}">
            <button class="page-link" onclick="loadExpenses(${page - 1})">Previous</button>
        </li>
    `;

    // Pages
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= page - 1 && i <= page + 1)) {
            ctrlHtml += `
                <li class="page-item ${i === page ? 'active' : ''}">
                    <button class="page-link" onclick="loadExpenses(${i})">${i}</button>
                </li>
            `;
        } else if (i === page - 2 || i === page + 2) {
            ctrlHtml += `<li class="page-item disabled"><span class="page-link">...</span></li>`;
        }
    }

    // Next button
    ctrlHtml += `
        <li class="page-item ${page === totalPages ? 'disabled' : ''}">
            <button class="page-link" onclick="loadExpenses(${page + 1})">Next</button>
        </li>
    `;

    controls.innerHTML = ctrlHtml;
}

function openAddModal() {
    document.getElementById('expenseForm').reset();
    document.getElementById('expenseId').value = '';
    document.getElementById('expenseDate').value = new Date().toISOString().split('T')[0];
    document.getElementById('expenseModalTitle').innerHTML = '<i class="bi bi-receipt text-primary me-2"></i>Add Expense';
    document.getElementById('saveExpenseBtn').innerHTML = '<i class="bi bi-check-lg me-1"></i>Save Expense';
    document.getElementById('modalAlert').classList.add('d-none');
}

async function openEditModal(expenseId) {
    document.getElementById('modalAlert').classList.add('d-none');
    try {
        const res = await fetch(`/api/expenses/${expenseId}`);
        const data = await res.json();
        if (!data.success) {
            alert(data.message || 'Error fetching expense details');
            return;
        }

        const e = data.expense;
        document.getElementById('expenseId').value = e.expense_id;
        document.getElementById('expenseTitle').value = e.title;
        document.getElementById('expenseAmount').value = e.amount;
        document.getElementById('expenseDate').value = e.expense_date;
        document.getElementById('expenseCategory').value = e.category_id;
        document.getElementById('expensePaymentMode').value = e.payment_mode;
        document.getElementById('expenseNotes').value = e.notes || '';

        document.getElementById('expenseModalTitle').innerHTML = '<i class="bi bi-pencil-square text-primary me-2"></i>Edit Expense Entry';
        document.getElementById('saveExpenseBtn').innerHTML = '<i class="bi bi-check-lg me-1"></i>Update Expense';

        expenseModalInstance.show();
    } catch (err) {
        console.error('Error loading expense for edit:', err);
    }
}

async function handleSaveExpense(event) {
    event.preventDefault();
    const alertBox = document.getElementById('modalAlert');
    alertBox.classList.add('d-none');

    const saveBtn = document.getElementById('saveExpenseBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

    const expenseId = document.getElementById('expenseId').value;
    const payload = {
        title: document.getElementById('expenseTitle').value.trim(),
        amount: parseFloat(document.getElementById('expenseAmount').value),
        expense_date: document.getElementById('expenseDate').value,
        category_id: document.getElementById('expenseCategory').value,
        payment_mode: document.getElementById('expensePaymentMode').value,
        notes: document.getElementById('expenseNotes').value.trim()
    };

    const isEdit = !!expenseId;
    const url = isEdit ? `/api/expenses/${expenseId}` : '/api/expenses';
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            expenseModalInstance.hide();
            loadExpenses(isEdit ? currentPage : 1);
        } else {
            alertBox.textContent = data.message || 'Failed to save expense.';
            alertBox.classList.remove('d-none');
        }
    } catch (err) {
        alertBox.textContent = 'Server connection error.';
        alertBox.classList.remove('d-none');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = isEdit ? '<i class="bi bi-check-lg me-1"></i>Update Expense' : '<i class="bi bi-check-lg me-1"></i>Save Expense';
    }
}

function openDeleteModal(expenseId) {
    document.getElementById('deleteExpenseId').value = expenseId;
    deleteModalInstance.show();
}

async function handleConfirmDelete() {
    const expenseId = document.getElementById('deleteExpenseId').value;
    const btn = document.getElementById('confirmDeleteBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Deleting...';

    try {
        const res = await fetch(`/api/expenses/${expenseId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.success) {
            deleteModalInstance.hide();
            loadExpenses(currentPage);
        } else {
            alert(data.message || 'Could not delete expense.');
        }
    } catch (err) {
        alert('Server connection error.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Delete';
    }
}

function handleExportCsv() {
    const month = document.getElementById('filterMonth').value;
    const category_id = document.getElementById('filterCategory').value;
    const payment_mode = document.getElementById('filterMode').value;
    const search = document.getElementById('filterSearch').value.trim();

    const params = new URLSearchParams();
    if (month) params.append('month', month);
    if (category_id) params.append('category_id', category_id);
    if (payment_mode) params.append('payment_mode', payment_mode);
    if (search) params.append('search', search);

    window.location.href = `/api/expenses/export-csv?${params.toString()}`;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
