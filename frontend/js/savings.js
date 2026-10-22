/**
 * frontend/js/savings.js
 * Handles Savings Goals card rendering, progress bars, and "+ Add Funds" deposits.
 */

let allGoals = [];

document.addEventListener('DOMContentLoaded', function() {
    loadGoals();

    const goalForm = document.getElementById('goalForm');
    if (goalForm) goalForm.addEventListener('submit', handleSaveGoal);

    const addFundsForm = document.getElementById('addFundsForm');
    if (addFundsForm) addFundsForm.addEventListener('submit', handleSaveFunds);

    // Quick fund amount buttons
    document.querySelectorAll('.quick-fund-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const amt = this.getAttribute('data-amt');
            const input = document.getElementById('fundsAmount');
            if (input) input.value = amt;
        });
    });
});

async function loadGoals() {
    try {
        const res = await fetch('/api/savings-goals');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!data.success) {
            showAlert(data.message || 'Failed to load savings goals', 'danger');
            return;
        }

        allGoals = data.goals || [];

        // 1. Update Metrics
        const m = data.metrics || {};
        document.getElementById('metricTotalTarget').textContent = `₹${(m.total_target || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('metricGoalCount').textContent = `${m.total_goals || 0} active goals`;

        document.getElementById('metricTotalSaved').textContent = `₹${(m.total_saved || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('metricTotalRemaining').textContent = `₹${(m.total_remaining || 0).toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

        document.getElementById('metricOverallProgress').textContent = `${m.overall_progress || 0}%`;
        document.getElementById('metricCompletedCount').textContent = `${m.completed_goals || 0} goals reached`;

        // 2. Render Grid
        renderGoalsGrid(allGoals);

    } catch (err) {
        console.error('Error fetching savings goals:', err);
        showAlert('Could not load savings goals from server.', 'danger');
    }
}

function renderGoalsGrid(goals) {
    const container = document.getElementById('goalsContainer');
    if (!container) return;

    if (!goals || goals.length === 0) {
        container.innerHTML = `
            <div class="col-12 text-center py-5 text-muted">
                <i class="bi bi-piggy-bank fs-1 d-block mb-2 text-primary opacity-50"></i>
                <h6 class="fw-semibold">No savings goals yet</h6>
                <p class="small text-muted mb-3">Create your first goal jar like an Emergency Fund or Laptop Upgrade.</p>
                <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#goalModal" onclick="openAddGoalModal()">
                    <i class="bi bi-plus-circle me-1"></i>Create Goal
                </button>
            </div>
        `;
        return;
    }

    let cardsHtml = '';
    goals.forEach(g => {
        const color = g.color_code || '#059669';
        const isDone = g.is_completed;
        const pct = g.progress_percent || 0;

        let dateBadge = '';
        if (isDone) {
            dateBadge = `<span class="badge bg-success-subtle text-success border border-success-subtle"><i class="bi bi-check2-all me-1"></i>Goal Reached!</span>`;
        } else if (g.days_left !== null && g.days_left !== undefined) {
            if (g.days_left < 0) {
                dateBadge = `<span class="badge bg-danger-subtle text-danger border border-danger-subtle"><i class="bi bi-exclamation-circle me-1"></i>Target date passed</span>`;
            } else {
                dateBadge = `<span class="badge bg-light text-muted border"><i class="bi bi-hourglass-split me-1"></i>${g.days_left} days left</span>`;
            }
        }

        cardsHtml += `
            <div class="col-12 col-md-6 col-xl-6">
                <div class="card-custom h-100 p-4 border shadow-sm position-relative" style="border-left: 5px solid ${color} !important; border-radius: 12px; background: #ffffff;">
                    <div class="d-flex align-items-start justify-content-between mb-3">
                        <div class="d-flex align-items-center gap-3">
                            <div class="rounded-3 d-flex align-items-center justify-content-center" style="width: 48px; height: 48px; background-color: ${color}15; color: ${color}; font-size: 1.4rem;">
                                <i class="bi ${g.category_icon || 'bi-piggy-bank'}"></i>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-1 text-dark" style="font-size: 1.05rem;">${escapeHtml(g.title)}</h6>
                                ${dateBadge}
                            </div>
                        </div>

                        <div class="dropdown">
                            <button class="btn btn-sm btn-link text-muted p-0" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                                <i class="bi bi-three-dots-vertical fs-5"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-sm">
                                <li>
                                    <a class="dropdown-item small" href="#" onclick="openEditGoalModal('${g.goal_id}'); return false;">
                                        <i class="bi bi-pencil me-2 text-secondary"></i>Edit Goal
                                    </a>
                                </li>
                                <li>
                                    <a class="dropdown-item small text-danger" href="#" onclick="deleteGoal('${g.goal_id}', '${escapeHtml(g.title)}'); return false;">
                                        <i class="bi bi-trash me-2"></i>Delete Goal
                                    </a>
                                </li>
                            </ul>
                        </div>
                    </div>

                    <!-- Amounts Display -->
                    <div class="d-flex align-items-baseline justify-content-between mb-2">
                        <div>
                            <span class="fs-4 fw-bold text-dark">₹${g.current_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                            <span class="text-muted small"> / ₹${g.target_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</span>
                        </div>
                        <span class="fw-bold fs-5" style="color: ${color};">${pct}%</span>
                    </div>

                    <!-- Progress Bar -->
                    <div class="progress mb-2" style="height: 10px; border-radius: 5px; background-color: #f1f5f9;">
                        <div class="progress-bar progress-bar-striped ${isDone ? 'bg-success' : ''}" 
                             role="progressbar" 
                             style="width: ${pct}%; background-color: ${isDone ? '#10b981' : color}; transition: width 0.8s ease;" 
                             aria-valuenow="${pct}" 
                             aria-valuemin="0" 
                             aria-valuemax="100">
                        </div>
                    </div>

                    <!-- Subtext / Remaining -->
                    <div class="d-flex align-items-center justify-content-between small text-muted mb-3">
                        <span>
                            ${isDone 
                                ? `<span class="text-success fw-semibold"><i class="bi bi-trophy-fill me-1"></i>Completed!</span>` 
                                : `<span>₹${g.remaining_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})} to go</span>`}
                        </span>
                        <span>${g.target_date ? `Target: ${g.target_date}` : 'Ongoing goal'}</span>
                    </div>

                    ${g.notes ? `<div class="p-2 rounded bg-light border text-muted small mb-3 fst-italic" style="font-size: 0.78rem;">${escapeHtml(g.notes)}</div>` : ''}

                    <!-- Action Button -->
                    <div class="d-flex justify-content-end mt-auto pt-2">
                        <button class="btn btn-sm btn-outline-success fw-semibold px-3 d-flex align-items-center gap-1 shadow-sm" onclick="openAddFundsModal('${g.goal_id}', '${escapeHtml(g.title)}')">
                            <i class="bi bi-plus-lg"></i>
                            <span>Add Funds</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    });

    container.innerHTML = cardsHtml;
}

function openAddFundsModal(goalId, title) {
    document.getElementById('addFundsGoalId').value = goalId;
    document.getElementById('addFundsGoalTitle').textContent = title;
    document.getElementById('fundsAmount').value = '2000';
    document.getElementById('fundsNote').value = '';

    const modal = new bootstrap.Modal(document.getElementById('addFundsModal'));
    modal.show();
    setTimeout(() => {
        const input = document.getElementById('fundsAmount');
        if (input) input.focus();
    }, 400);
}

async function handleSaveFunds(e) {
    e.preventDefault();
    const btn = document.getElementById('saveFundsBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Depositing...';

    const goalId = document.getElementById('addFundsGoalId').value;
    const amount = parseFloat(document.getElementById('fundsAmount').value);
    const note = document.getElementById('fundsNote').value.trim();

    try {
        const res = await fetch(`/api/savings-goals/${goalId}/add-funds`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: amount, note: note })
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`✓ ${data.message}`, 'success');
            const modalEl = document.getElementById('addFundsModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            loadGoals();
        } else {
            alert(data.message || 'Could not deposit funds.');
        }
    } catch (err) {
        console.error('Error adding funds:', err);
        alert('Server error occurred.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Deposit Funds';
    }
}

function openAddGoalModal() {
    document.getElementById('goalModalLabel').innerHTML = '<i class="bi bi-piggy-bank text-primary me-2"></i>New Savings Goal';
    document.getElementById('goalId').value = '';
    document.getElementById('goalTitle').value = '';
    document.getElementById('goalTargetAmount').value = '';
    document.getElementById('goalCurrentAmount').value = '';
    document.getElementById('goalTargetDate').value = '';
    document.getElementById('goalIcon').value = 'bi-piggy-bank';
    document.getElementById('goalColor').value = '#059669';
    document.getElementById('goalNotes').value = '';
}

function openEditGoalModal(goalId) {
    const goal = allGoals.find(g => String(g.goal_id) === String(goalId));
    if (!goal) return;

    document.getElementById('goalModalLabel').innerHTML = '<i class="bi bi-pencil-square text-primary me-2"></i>Edit Savings Goal';
    document.getElementById('goalId').value = goal.goal_id;
    document.getElementById('goalTitle').value = goal.title;
    document.getElementById('goalTargetAmount').value = goal.target_amount;
    document.getElementById('goalCurrentAmount').value = goal.current_amount;
    document.getElementById('goalTargetDate').value = goal.target_date || '';
    document.getElementById('goalIcon').value = goal.category_icon || 'bi-piggy-bank';
    document.getElementById('goalColor').value = goal.color_code || '#059669';
    document.getElementById('goalNotes').value = goal.notes || '';

    const modal = new bootstrap.Modal(document.getElementById('goalModal'));
    modal.show();
}

async function handleSaveGoal(e) {
    e.preventDefault();
    const btn = document.getElementById('saveGoalBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

    const goalId = document.getElementById('goalId').value;
    const isEdit = Boolean(goalId);

    const payload = {
        title: document.getElementById('goalTitle').value.trim(),
        target_amount: parseFloat(document.getElementById('goalTargetAmount').value),
        current_amount: parseFloat(document.getElementById('goalCurrentAmount').value || 0),
        target_date: document.getElementById('goalTargetDate').value,
        category_icon: document.getElementById('goalIcon').value,
        color_code: document.getElementById('goalColor').value,
        notes: document.getElementById('goalNotes').value.trim()
    };

    const url = isEdit ? `/api/savings-goals/${goalId}` : '/api/savings-goals';
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
            const modalEl = document.getElementById('goalModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            loadGoals();
        } else {
            alert(data.message || 'Failed to save goal.');
        }
    } catch (err) {
        console.error('Error saving savings goal:', err);
        alert('Server error occurred.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-check2 me-1"></i>Save Goal';
    }
}

async function deleteGoal(goalId, title) {
    if (!confirm(`Are you sure you want to delete the goal "${title}"?`)) {
        return;
    }

    try {
        const res = await fetch(`/api/savings-goals/${goalId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.success) {
            showAlert(`✓ ${data.message}`, 'success');
            loadGoals();
        } else {
            showAlert(data.message || 'Failed to delete goal.', 'danger');
        }
    } catch (err) {
        console.error('Error deleting goal:', err);
        showAlert('Error deleting goal.', 'danger');
    }
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('savingsAlertContainer');
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

function escapeHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
