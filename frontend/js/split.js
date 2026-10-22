/**
 * frontend/js/split.js
 * Roommate & Hostel Equal Bill Splitter (Module C).
 * Live division calculator and 1-click settlement toggling.
 */

let currentSplitFilter = 'all';

document.addEventListener('DOMContentLoaded', async function() {
    // Set default date
    document.getElementById('splitDate').value = new Date().toISOString().split('T')[0];

    // Load categories
    await loadCategoriesForSplit();

    // Initial load of splits
    loadSplits();

    // Live calculator listeners
    document.getElementById('splitTotalAmount').addEventListener('input', updateLiveCalculator);
    document.getElementById('splitFriends').addEventListener('input', updateLiveCalculator);
    document.getElementById('includeSelfCheck').addEventListener('change', updateLiveCalculator);

    // Form submission
    document.getElementById('splitBillForm').addEventListener('submit', handleCreateSplit);
});

async function loadCategoriesForSplit() {
    try {
        const res = await fetch('/api/categories');
        const data = await res.json();
        if (data.success) {
            const select = document.getElementById('splitCategory');
            select.innerHTML = '<option value="">Select Category</option>';
            data.categories.forEach(c => {
                select.innerHTML += `<option value="${c.category_id}">${escapeHtml(c.category_name)}</option>`;
            });
            // Default to Food & Canteen if present
            if (data.categories.length > 0) {
                select.value = data.categories[0].category_id;
            }
        }
    } catch (err) {
        console.error('Failed to load categories for split:', err);
    }
}

function updateLiveCalculator() {
    const totalAmount = parseFloat(document.getElementById('splitTotalAmount').value) || 0;
    const friendsStr = document.getElementById('splitFriends').value.trim();
    const includeSelf = document.getElementById('includeSelfCheck').checked;

    const friendsList = friendsStr ? friendsStr.split(',').map(f => f.trim()).filter(f => f.length > 0) : [];
    const numPeople = friendsList.length + (includeSelf ? 1 : 0);

    const countBadge = document.getElementById('splitPeopleCountBadge');
    const shareAmount = document.getElementById('splitShareAmount');
    const formulaText = document.getElementById('splitFormulaText');

    if (numPeople > 0 && totalAmount > 0) {
        const perPerson = (totalAmount / numPeople).toFixed(2);
        countBadge.textContent = `${numPeople} people (${friendsList.length} member${friendsList.length === 1 ? '' : 's'}${includeSelf ? ' + you' : ''})`;
        shareAmount.textContent = `₹${parseFloat(perPerson).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        formulaText.textContent = `Formula: ₹${totalAmount.toLocaleString('en-IN')} ÷ ${numPeople} = ₹${perPerson} per person`;
    } else {
        countBadge.textContent = '1 person';
        shareAmount.textContent = '₹0.00';
        formulaText.textContent = 'Enter total bill and member names above to calculate.';
    }
}

async function handleCreateSplit(event) {
    event.preventDefault();
    const alertBox = document.getElementById('splitFormAlert');
    alertBox.classList.add('d-none');

    const submitBtn = document.getElementById('createSplitBtn');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Creating Split Bill...';

    const payload = {
        title: document.getElementById('splitTitle').value.trim(),
        total_amount: parseFloat(document.getElementById('splitTotalAmount').value),
        category_id: document.getElementById('splitCategory').value,
        friends: document.getElementById('splitFriends').value.trim(),
        include_self: document.getElementById('includeSelfCheck').checked,
        payment_mode: document.getElementById('splitPaymentMode').value,
        expense_date: document.getElementById('splitDate').value || new Date().toISOString().split('T')[0],
    };

    try {
        const res = await fetch('/api/splits', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            // Reset form
            document.getElementById('splitBillForm').reset();
            document.getElementById('splitDate').value = new Date().toISOString().split('T')[0];
            document.getElementById('includeSelfCheck').checked = true;
            updateLiveCalculator();
            
            // Reload splits list & stats
            loadSplits();
        } else {
            alertBox.textContent = data.message || 'Could not create split bill.';
            alertBox.classList.remove('d-none');
        }
    } catch (err) {
        alertBox.textContent = 'Server connection error.';
        alertBox.classList.remove('d-none');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="bi bi-check2-all me-1"></i>Create Split Bill & Track Shares';
    }
}

function setSplitFilter(filter) {
    currentSplitFilter = filter;
    document.getElementById('filterSplitAll').className = `btn btn-outline-secondary ${filter === 'all' ? 'active' : ''}`;
    document.getElementById('filterSplitPending').className = `btn btn-outline-secondary ${filter === 'pending' ? 'active' : ''}`;
    document.getElementById('filterSplitSettled').className = `btn btn-outline-secondary ${filter === 'settled' ? 'active' : ''}`;
    loadSplits();
}

async function loadSplits() {
    const container = document.getElementById('splitsListContainer');
    try {
        const res = await fetch(`/api/splits?status=${currentSplitFilter}`);
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!data.success) {
            container.innerHTML = `<div class="text-danger p-3">${escapeHtml(data.message)}</div>`;
            return;
        }

        // Update Summary Cards
        const stats = data.stats;
        document.getElementById('statTotalLent').textContent = `₹${stats.total_lent.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('statTotalRecovered').textContent = `₹${stats.total_recovered.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('statTotalPending').textContent = `₹${stats.total_pending.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('statPendingCount').textContent = `${stats.pending_count} pending claim${stats.pending_count === 1 ? '' : 's'}`;

        renderSplitsList(data.splits);

    } catch (err) {
        console.error('Error fetching splits:', err);
        container.innerHTML = '<div class="text-danger p-3">Failed to load splits data.</div>';
    }
}

function renderSplitsList(splits) {
    const container = document.getElementById('splitsListContainer');
    if (!splits || splits.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5 text-muted">
                <i class="bi bi-check2-all fs-2 d-block mb-2 text-success"></i>
                No ${currentSplitFilter === 'all' ? 'bill split' : currentSplitFilter} records found.
            </div>
        `;
        return;
    }

    let html = '';
    splits.forEach(s => {
        const isSettled = s.is_settled;
        html += `
            <div class="split-card ${isSettled ? 'settled' : ''}">
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-2">
                    <div class="d-flex align-items-center gap-3">
                        <div class="rounded-circle d-flex align-items-center justify-content-center text-white" 
                             style="width: 40px; height: 40px; background-color: ${isSettled ? '#198754' : '#0d6efd'}; font-weight: 600; font-size: 0.95rem;">
                            ${escapeHtml(s.friend_name.charAt(0).toUpperCase())}
                        </div>
                        <div>
                            <div class="d-flex align-items-center gap-2">
                                <h6 class="mb-0 fw-bold text-dark">${escapeHtml(s.friend_name)}</h6>
                                <span class="badge ${isSettled ? 'bg-success' : 'bg-warning text-dark'} small">
                                    ${isSettled ? 'Settled (Paid)' : 'Pending'}
                                </span>
                            </div>
                            <div class="text-muted small">
                                For: <strong>${escapeHtml(s.expense_title)}</strong> &bull; Total Bill: ₹${s.total_bill_amount.toLocaleString('en-IN')} (${s.expense_date})
                            </div>
                        </div>
                    </div>

                    <div class="d-flex align-items-center gap-3 ms-auto">
                        <div class="text-end">
                            <span class="fs-5 fw-bold ${isSettled ? 'text-success' : 'text-danger'}">
                                ₹${s.amount_owed.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                            </span>
                            <div class="text-muted" style="font-size: 0.72rem;">
                                ${isSettled ? (s.settled_at ? 'Paid back ' + s.settled_at.split(' ')[0] : 'Settled') : 'Owed to you'}
                            </div>
                        </div>

                        <div>
                            ${isSettled ? `
                                <button class="btn btn-sm btn-outline-secondary py-1 px-2" 
                                        onclick="toggleSettlement('${s.split_id}', 0)" 
                                        title="Reopen Claim">
                                    <i class="bi bi-arrow-counterclockwise me-1"></i>Reopen
                                </button>
                            ` : `
                                <button class="btn btn-sm btn-success py-1 px-2 fw-semibold" 
                                        onclick="toggleSettlement('${s.split_id}', 1)" 
                                        title="Mark as Paid">
                                    <i class="bi bi-check-lg me-1"></i>Mark Settled
                                </button>
                            `}
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

async function toggleSettlement(splitId, targetStatus) {
    try {
        const res = await fetch(`/api/splits/${splitId}/settle`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ is_settled: targetStatus })
        });
        const data = await res.json();
        if (data.success) {
            loadSplits();
        } else {
            alert(data.message || 'Failed to update settlement status.');
        }
    } catch (err) {
        alert('Server error.');
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
