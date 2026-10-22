/**
 * frontend/js/recurring.js
 * Handles Recurring Bills data fetching, modal management, and "Mark Paid" expense logging.
 */

let cachedCategories = [];
let allBills = [];

document.addEventListener('DOMContentLoaded', function() {
    loadCategoriesForModal();
    loadBills();

    const form = document.getElementById('billForm');
    if (form) {
        form.addEventListener('submit', handleSaveBill);
    }
});

async function loadCategoriesForModal() {
    try {
        const res = await fetch('/api/categories');
        const data = await res.json();
        if (data.success && data.categories) {
            cachedCategories = data.categories;
            const select = document.getElementById('billCategory');
            if (select) {
                select.innerHTML = data.categories.map(c => 
                    `<option value="${c.category_id}">${escapeHtml(c.category_name)}</option>`
                ).join('');
            }
        }
    } catch (err) {
        console.error('Error loading categories:', err);
    }
}

async function loadBills() {
    try {
        const res = await fetch('/api/recurring-bills');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!data.success) {
            showAlert(data.message || 'Failed to load recurring bills', 'danger');
            return;
        }

        allBills = data.bills || [];

        // 1. Update Metrics
        const m = data.metrics || {};
        document.getElementById('metricTotalBills').textContent = `₹${(m.total_monthly_amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('metricTotalCount').textContent = `${m.total_bills || 0} monthly bills configured`;

        document.getElementById('metricPaidAmount').textContent = `₹${(m.paid_amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('metricPaidCount').textContent = `${m.paid_count || 0} settled this month`;

        document.getElementById('metricPendingAmount').textContent = `₹${(m.pending_amount || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('metricPendingCount').textContent = `${m.pending_count || 0} pending payment`;

        // 2. Render Table
        renderBillsTable(allBills);

    } catch (err) {
        console.error('Error fetching recurring bills:', err);
        showAlert('Could not connect to server.', 'danger');
    }
}

function renderBillsTable(bills) {
    const tbody = document.getElementById('recurringTableBody');
    if (!tbody) return;

    if (!bills || bills.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-5 text-muted">
                    <i class="bi bi-calendar-x fs-2 d-block mb-2"></i>
                    No recurring bills found. Click "+ Add Recurring Bill" above to track your monthly obligations.
                </td>
            </tr>
        `;
        return;
    }

    let rowsHtml = '';
    bills.forEach(b => {
        const modeClass = b.payment_mode === 'UPI' ? 'badge-mode-upi' : (b.payment_mode === 'Cash' ? 'badge-mode-cash' : 'badge-mode-card');
        const dueSuffix = getOrdinalSuffix(b.due_day);

        // Mark Paid button or Paid status badge
        let actionBtn = '';
        if (b.is_paid) {
            actionBtn = `
                <button class="btn btn-sm btn-light text-success border fw-medium px-2 py-1" disabled title="Already logged in Expenses for current month">
                    <i class="bi bi-check2-circle me-1"></i>Paid
                </button>
            `;
        } else {
            actionBtn = `
                <button class="btn btn-sm btn-success fw-medium px-2 py-1" onclick="markBillPaid('${b.bill_id}', '${escapeHtml(b.title)}')" title="Mark as paid and record to expenses">
                    <i class="bi bi-check-lg me-1"></i>Mark Paid
                </button>
            `;
        }

        rowsHtml += `
            <tr>
                <td>
                    <div class="fw-semibold text-dark">${escapeHtml(b.title)}</div>
                    ${b.notes ? `<small class="text-muted text-truncate d-block" style="max-width: 200px;">${escapeHtml(b.notes)}</small>` : ''}
                </td>
                <td>
                    <span class="badge-category" style="background-color: #0d6efd15; color: #0d6efd;">
                        <i class="bi ${b.icon_name || 'bi-tag'}"></i> ${escapeHtml(b.category_name)}
                    </span>
                </td>
                <td>
                    <div class="fw-medium text-dark"><i class="bi bi-calendar-day me-1 text-primary"></i>${b.due_day}${dueSuffix} of month</div>
                    <small class="text-muted">${escapeHtml(b.frequency || 'Monthly')}</small>
                </td>
                <td>
                    <span class="badge-mode ${modeClass}">${escapeHtml(b.payment_mode)}</span>
                </td>
                <td class="fw-bold text-dark text-nowrap">
                    ₹${b.amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                </td>
                <td>
                    <span class="badge bg-${b.status_color}-subtle text-${b.status_color} border border-${b.status_color}-subtle px-2 py-1">
                        ${b.status_badge}
                    </span>
                </td>
                <td class="text-end text-nowrap">
                    <div class="d-inline-flex align-items-center gap-1">
                        ${actionBtn}
                        <button class="btn btn-sm btn-outline-secondary p-1 px-2" title="Edit Bill" onclick="openEditBillModal('${b.bill_id}')">
                            <i class="bi bi-pencil"></i>
                        </button>
                        <button class="btn btn-sm btn-outline-danger p-1 px-2" title="Delete Bill" onclick="deleteBill('${b.bill_id}', '${escapeHtml(b.title)}')">
                            <i class="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
}

async function markBillPaid(billId, title) {
    if (!confirm(`Mark "${title}" as paid? This will immediately log the payment into your MongoDB expenses collection.`)) {
        return;
    }

    try {
        const res = await fetch(`/api/recurring-bills/${billId}/pay`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`✓ ${data.message}`, 'success');
            loadBills();
        } else {
            showAlert(data.message || 'Failed to mark bill as paid.', 'danger');
        }
    } catch (err) {
        console.error('Error marking bill paid:', err);
        showAlert('Network error while marking bill paid.', 'danger');
    }
}

function openAddBillModal() {
    document.getElementById('billModalLabel').innerHTML = '<i class="bi bi-calendar-plus text-primary me-2"></i>Add Recurring Bill';
    document.getElementById('billId').value = '';
    document.getElementById('billTitle').value = '';
    document.getElementById('billAmount').value = '';
    document.getElementById('billDueDay').value = '5';
    document.getElementById('billFrequency').value = 'Monthly';
    document.getElementById('billPaymentMode').value = 'UPI';
    document.getElementById('billNotes').value = '';
}

function openEditBillModal(billId) {
    const bill = allBills.find(b => String(b.bill_id) === String(billId));
    if (!bill) return;

    document.getElementById('billModalLabel').innerHTML = '<i class="bi bi-pencil-square text-primary me-2"></i>Edit Recurring Bill';
    document.getElementById('billId').value = bill.bill_id;
    document.getElementById('billTitle').value = bill.title;
    document.getElementById('billAmount').value = bill.amount;
    document.getElementById('billDueDay').value = bill.due_day;
    document.getElementById('billFrequency').value = bill.frequency || 'Monthly';
    document.getElementById('billPaymentMode').value = bill.payment_mode || 'UPI';
    document.getElementById('billNotes').value = bill.notes || '';

    if (bill.category_id && document.getElementById('billCategory')) {
        document.getElementById('billCategory').value = bill.category_id;
    }

    const modal = new bootstrap.Modal(document.getElementById('billModal'));
    modal.show();
}

async function handleSaveBill(e) {
    e.preventDefault();
    const saveBtn = document.getElementById('saveBillBtn');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

    const billId = document.getElementById('billId').value;
    const isEdit = Boolean(billId);

    const payload = {
        title: document.getElementById('billTitle').value.trim(),
        amount: parseFloat(document.getElementById('billAmount').value),
        due_day: parseInt(document.getElementById('billDueDay').value),
        category_id: document.getElementById('billCategory').value,
        frequency: document.getElementById('billFrequency').value,
        payment_mode: document.getElementById('billPaymentMode').value,
        notes: document.getElementById('billNotes').value.trim()
    };

    const url = isEdit ? `/api/recurring-bills/${billId}` : '/api/recurring-bills';
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`✓ ${data.message}`, 'success');
            const modalEl = document.getElementById('billModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            loadBills();
        } else {
            alert(data.message || 'Failed to save bill.');
        }
    } catch (err) {
        console.error('Error saving recurring bill:', err);
        alert('Server error occurred while saving bill.');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-check2 me-1"></i>Save Bill';
    }
}

async function deleteBill(billId, title) {
    if (!confirm(`Are you sure you want to delete the recurring bill "${title}"?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/recurring-bills/${billId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`✓ ${data.message}`, 'success');
            loadBills();
        } else {
            showAlert(data.message || 'Failed to delete bill.', 'danger');
        }
    } catch (err) {
        console.error('Error deleting bill:', err);
        showAlert('Error deleting bill.', 'danger');
    }
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('recurringAlertContainer');
    if (!container) return;

    container.innerHTML = `
        <div class="alert alert-${type} alert-dismissible fade show border py-2 px-3 shadow-sm d-flex align-items-center justify-content-between" role="alert">
            <div class="d-flex align-items-center gap-2">
                <i class="bi ${type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-exclamation-triangle-fill text-danger'}"></i>
                <span>${message}</span>
            </div>
            <button type="button" class="btn-close btn-sm" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    `;

    setTimeout(() => {
        if (container) container.innerHTML = '';
    }, 6000);
}

function getOrdinalSuffix(day) {
    const j = day % 10, k = day % 100;
    if (j === 1 && k !== 11) return "st";
    if (j === 2 && k !== 12) return "nd";
    if (j === 3 && k !== 13) return "rd";
    return "th";
}

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
