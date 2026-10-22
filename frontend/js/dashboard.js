/**
 * frontend/js/dashboard.js
 * Fetches dashboard analytics and initializes Chart.js Doughnut and Bar charts.
 */

document.addEventListener('DOMContentLoaded', function() {
    loadDashboardStats();
});

let categoryChart = null;
let trendChart = null;

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/dashboard/stats');
        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();
        if (!data.success) {
            console.error('Failed to load dashboard stats:', data.message);
            return;
        }

        // 1. Update Month Label
        const monthLabel = document.getElementById('currentMonthLabel');
        if (monthLabel) monthLabel.textContent = data.month_name;

        // 2. Update Metric Cards
        const m = data.metrics;
        document.getElementById('statTotalBudget').textContent = `₹${m.monthly_budget.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('statSpentMonth').textContent = `₹${m.total_spent.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('statRemainingBalance').textContent = `₹${m.remaining_balance.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        document.getElementById('statPercentSpent').textContent = `${m.percent_spent}% of monthly limit used`;

        // If remaining balance is negative, style with danger
        const balanceElem = document.getElementById('statRemainingBalance');
        if (m.remaining_balance < 0) {
            balanceElem.classList.remove('text-success');
            balanceElem.classList.add('text-danger');
        } else {
            balanceElem.classList.remove('text-danger');
            balanceElem.classList.add('text-success');
        }

        // 3. Render 80% / 100% Threshold Alerts (Module B)
        renderThresholdAlert(data.alert);

        // 4. Render Doughnut Chart
        renderDoughnutChart(data.doughnut_chart);

        // 5. Render 6-Month Bar Chart
        renderTrendBarChart(data.bar_chart);

        // 6. Render Recent Transactions
        renderRecentTransactions(data.recent_transactions);

    } catch (err) {
        console.error('Error fetching dashboard stats:', err);
    }
}

function renderThresholdAlert(alert) {
    const container = document.getElementById('alertBannerContainer');
    if (!container) return;

    if (!alert) {
        container.innerHTML = '';
        return;
    }

    const alertHtml = `
        <div class="alert alert-${alert.type} border shadow-sm d-flex align-items-center justify-content-between p-3" role="alert">
            <div class="d-flex align-items-center gap-3">
                <i class="bi ${alert.icon} fs-2 text-${alert.type}"></i>
                <div>
                    <span class="badge bg-${alert.type} text-uppercase mb-1" style="font-size: 0.72rem;">${alert.badge}</span>
                    <h6 class="fw-bold mb-1">${alert.title}</h6>
                    <div style="font-size: 0.85rem;" class="text-dark">${alert.message}</div>
                </div>
            </div>
            <a href="/budgets" class="btn btn-sm btn-outline-${alert.type} text-nowrap ms-3">
                Manage Budget
            </a>
        </div>
    `;
    container.innerHTML = alertHtml;
}

function renderDoughnutChart(chartData) {
    const canvas = document.getElementById('categoryDoughnutChart');
    const emptyMsg = document.getElementById('doughnutEmptyMsg');
    if (!canvas) return;

    if (!chartData || !chartData.labels || chartData.labels.length === 0) {
        canvas.style.display = 'none';
        if (emptyMsg) emptyMsg.classList.remove('d-none');
        return;
    }

    canvas.style.display = 'block';
    if (emptyMsg) emptyMsg.classList.add('d-none');

    if (categoryChart) {
        categoryChart.destroy();
    }

    categoryChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: chartData.labels,
            datasets: [{
                data: chartData.data,
                backgroundColor: chartData.colors && chartData.colors.length > 0 ? chartData.colors : [
                    '#0d6efd', '#198754', '#ffc107', '#0dcaf0', '#d63384', '#6c757d'
                ],
                borderWidth: 2,
                borderColor: '#ffffff',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '68%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        boxWidth: 12,
                        padding: 12,
                        font: { size: 11, family: 'inherit' }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const val = context.parsed || 0;
                            return ` ${context.label}: ₹${val.toLocaleString('en-IN')}`;
                        }
                    }
                }
            }
        }
    });
}

function renderTrendBarChart(barData) {
    const canvas = document.getElementById('monthlyTrendBarChart');
    if (!canvas) return;

    if (trendChart) {
        trendChart.destroy();
    }

    trendChart = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: barData.labels,
            datasets: [{
                label: 'Monthly Spending (INR)',
                data: barData.data,
                backgroundColor: '#0d6efd',
                hoverBackgroundColor: '#0b5ed7',
                borderRadius: 4,
                barPercentage: 0.55,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: '#f1f5f9' },
                    ticks: {
                        callback: function(value) {
                            return '₹' + value.toLocaleString('en-IN');
                        },
                        font: { size: 11 }
                    }
                },
                x: {
                    grid: { display: false },
                    ticks: { font: { size: 11 } }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return ` Spent: ₹${context.parsed.y.toLocaleString('en-IN')}`;
                        }
                    }
                }
            }
        }
    });
}

function renderRecentTransactions(transactions) {
    const tbody = document.getElementById('recentTransactionsTableBody');
    if (!tbody) return;

    if (!transactions || transactions.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="text-center py-4 text-muted">
                    No transactions recorded yet.
                </td>
            </tr>
        `;
        return;
    }

    let rowsHtml = '';
    transactions.forEach(t => {
        const modeClass = t.payment_mode === 'UPI' ? 'badge-mode-upi' : (t.payment_mode === 'Cash' ? 'badge-mode-cash' : 'badge-mode-card');
        rowsHtml += `
            <tr>
                <td class="text-nowrap text-secondary">${t.expense_date}</td>
                <td class="fw-semibold text-dark">${escapeHtml(t.title)}</td>
                <td>
                    <span class="badge-category" style="background-color: ${t.color_code}15; color: ${t.color_code};">
                        <i class="bi ${t.icon_name || 'bi-tag'}"></i> ${escapeHtml(t.category_name)}
                    </span>
                </td>
                <td>
                    <span class="badge-mode ${modeClass}">${t.payment_mode}</span>
                </td>
                <td class="text-end fw-bold text-dark text-nowrap">
                    ₹${t.amount.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                </td>
            </tr>
        `;
    });

    tbody.innerHTML = rowsHtml;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}


