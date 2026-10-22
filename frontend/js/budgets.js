/**
 * frontend/js/budgets.js
 * Renders monthly category budget limits and visual progress bars.
 */

let totalBudgetModal = null;
let categoryLimitModal = null;

document.addEventListener('DOMContentLoaded', function() {
    totalBudgetModal = new bootstrap.Modal(document.getElementById('editTotalBudgetModal'));
    categoryLimitModal = new bootstrap.Modal(document.getElementById('editCategoryLimitModal'));

    loadBudgetData();

    document.getElementById('editTotalBudgetForm').addEventListener('submit', handleUpdateTotalBudget);
    document.getElementById('editCategoryLimitForm').addEventListener('submit', handleUpdateCategoryLimit);
});

async function loadBudgetData() {
    const container = document.getElementById('categoryBudgetsContainer');
    try {
        const res = await fetch('/api/budgets');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!data.success) {
            container.innerHTML = `<div class="text-danger p-3">${escapeHtml(data.message)}</div>`;
            return;
        }

        // Update Overall Budget Card
        document.getElementById('budgetMonthLabel').textContent = data.month_name;
        document.getElementById('newTotalBudgetInput').value = data.total_budget;

        const overallPercent = Math.min(100, Math.max(0, data.overall_percent));
        const progressBar = document.getElementById('overallProgressBar');
        progressBar.style.width = `${overallPercent}%`;
        progressBar.className = `progress-bar bg-${data.overall_percent >= 100 ? 'danger' : (data.overall_percent >= 80 ? 'warning' : 'success')}`;

        document.getElementById('overallBudgetPercent').textContent = `${data.overall_percent}%`;
        document.getElementById('overallBudgetAmount').textContent = `₹${data.total_spent.toLocaleString('en-IN', {minimumFractionDigits: 2})} / ₹${data.total_budget.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

        const titleElem = document.getElementById('overallBudgetTitle');
        if (data.overall_percent >= 100) {
            titleElem.textContent = 'Budget Limit Exceeded!';
            titleElem.className = 'fw-bold mb-0 mt-1 text-danger';
        } else if (data.overall_percent >= 80) {
            titleElem.textContent = 'Attention: 80% Threshold Reached';
            titleElem.className = 'fw-bold mb-0 mt-1 text-warning text-dark';
        } else {
            titleElem.textContent = 'Disciplined Spending (On Track)';
            titleElem.className = 'fw-bold mb-0 mt-1 text-success';
        }

        // Render Category Progress Bars
        renderCategoryBudgets(data.categories);

    } catch (err) {
        console.error('Error fetching budget data:', err);
        container.innerHTML = '<div class="text-danger p-3">Failed to load budget data from server.</div>';
    }
}

function renderCategoryBudgets(categories) {
    const container = document.getElementById('categoryBudgetsContainer');
    if (!categories || categories.length === 0) {
        container.innerHTML = '<div class="text-muted p-4 text-center">No categories configured.</div>';
        return;
    }

    let html = '';
    categories.forEach(c => {
        const pctClamped = Math.min(100, Math.max(0, c.percent_used));
        const isOver = c.percent_used >= 100;
        const isWarn = c.percent_used >= 80 && !isOver;

        const badgeClass = isOver ? 'bg-danger' : (isWarn ? 'bg-warning text-dark' : 'bg-success');
        const barClass = isOver ? 'bg-danger' : (isWarn ? 'bg-warning' : 'bg-success');

        html += `
            <div class="budget-progress-container">
                <div class="d-flex align-items-center justify-content-between mb-2">
                    <div class="d-flex align-items-center gap-2">
                        <div class="d-inline-flex align-items-center justify-content-center rounded" 
                             style="width: 34px; height: 34px; background-color: ${c.color_code}15; color: ${c.color_code}; font-size: 1.1rem;">
                            <i class="bi ${c.icon_name || 'bi-tag'}"></i>
                        </div>
                        <div>
                            <span class="fw-bold text-dark">${escapeHtml(c.category_name)}</span>
                        </div>
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <span class="badge ${badgeClass}">${c.percent_used}%</span>
                        <button class="btn btn-sm btn-outline-secondary py-0 px-2" 
                                onclick="openCategoryModal('${c.category_id}', '${escapeHtml(c.category_name)}', ${c.monthly_limit})" 
                                title="Edit Limit">
                            <i class="bi bi-pencil" style="font-size: 0.78rem;"></i>
                        </button>
                    </div>
                </div>

                <div class="d-flex justify-content-between small text-muted mb-1">
                    <span>Spent: <strong class="text-dark">₹${c.spent_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong></span>
                    <span>Monthly Limit: <strong>₹${c.monthly_limit.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong></span>
                </div>

                <div class="progress" style="height: 8px;">
                    <div class="progress-bar ${barClass}" role="progressbar" style="width: ${pctClamped}%;" aria-valuenow="${pctClamped}" aria-valuemin="0" aria-valuemax="100"></div>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function openCategoryModal(categoryId, categoryName, currentLimit) {
    document.getElementById('editCategoryId').value = categoryId;
    document.getElementById('newCategoryLimitInput').value = currentLimit;
    document.getElementById('editCategoryModalTitle').innerHTML = `<i class="bi bi-tag text-primary me-2"></i>Limit: ${categoryName}`;
    categoryLimitModal.show();
}

async function handleUpdateTotalBudget(event) {
    event.preventDefault();
    const btn = document.getElementById('saveTotalBudgetBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

    const newLimit = parseFloat(document.getElementById('newTotalBudgetInput').value);

    try {
        const res = await fetch('/api/budgets/monthly-limit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ monthly_budget_limit: newLimit })
        });
        const data = await res.json();
        if (data.success) {
            totalBudgetModal.hide();
            loadBudgetData();
        } else {
            alert(data.message || 'Failed to update total budget.');
        }
    } catch (err) {
        alert('Server error.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Update';
    }
}

async function handleUpdateCategoryLimit(event) {
    event.preventDefault();
    const btn = document.getElementById('saveCategoryLimitBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Saving...';

    const categoryId = document.getElementById('editCategoryId').value;
    const newLimit = parseFloat(document.getElementById('newCategoryLimitInput').value);

    try {
        const res = await fetch(`/api/categories/${categoryId}/limit`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ monthly_limit: newLimit })
        });
        const data = await res.json();
        if (data.success) {
            categoryLimitModal.hide();
            loadBudgetData();
        } else {
            alert(data.message || 'Failed to update category limit.');
        }
    } catch (err) {
        alert('Server error.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Save Limit';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
