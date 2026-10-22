/**
 * frontend/js/advisor.js
 * Handles PocketWise Financial Advisor diagnostics, Health Score rendering,
 * Predictive Math (Linear Regression & WMA), Statistical Anomaly Detection,
 * Hybrid AI Smart Financial Audit (Gemini / Offline Fallback),
 * 50/30/20 rule analytics, and interactive purchase simulation.
 */

document.addEventListener('DOMContentLoaded', function() {
    loadAdvisorInsights();

    // Setup Purchase Simulator form
    const simForm = document.getElementById('simulatorForm');
    if (simForm) {
        simForm.addEventListener('submit', handleSimulatePurchase);
    }

    // Setup Smart Audit button
    const auditBtn = document.getElementById('generateAuditBtn');
    if (auditBtn) {
        auditBtn.addEventListener('click', runSmartAudit);
    }

    // Auto-run smart audit on load
    runSmartAudit();
});

async function loadAdvisorInsights() {
    try {
        const res = await fetch('/api/advisor/insights');
        if (res.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await res.json();
        if (!data.success) {
            console.error('Failed to load advisor insights:', data.message);
            return;
        }

        // 1. Month Label
        const monthLabel = document.getElementById('advisorMonthLabel');
        if (monthLabel) monthLabel.textContent = data.month_name;

        // 2. Health Score Card
        const scoreElem = document.getElementById('statHealthScore');
        const badgeElem = document.getElementById('statScoreBadge');
        if (scoreElem) scoreElem.textContent = data.health_score;
        if (badgeElem) {
            badgeElem.textContent = data.score_status;
            badgeElem.className = `badge bg-${data.score_color}`;
        }

        // 3. Predictive Math: Projected Next Month Spend
        if (data.prediction) {
            const pred = data.prediction;
            const predSpendElem = document.getElementById('statProjectedSpend');
            const predTrendElem = document.getElementById('statProjectedTrend');
            
            if (predSpendElem) {
                predSpendElem.textContent = `₹${pred.projected_spend.toLocaleString('en-IN', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
            }
            if (predTrendElem) {
                const isUp = pred.trend_direction === 'up';
                const isDown = pred.trend_direction === 'down';
                const arrow = isUp ? '▲ +' : (isDown ? '▼ ' : '— ');
                predTrendElem.textContent = `${arrow}${Math.abs(pred.trend_percent)}% MoM`;
                predTrendElem.className = `badge ${isUp ? 'bg-danger text-white' : (isDown ? 'bg-success text-white' : 'bg-secondary text-white')}`;
            }
        }

        // 4. Safe Daily & Burn Rate Cards
        const m = data.metrics;
        document.getElementById('statSafeDaily').textContent = `₹${m.safe_daily_limit.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;
        document.getElementById('statDaysLeftText').textContent = `${m.days_left} day${m.days_left === 1 ? '' : 's'} remaining in ${data.month_name.split(' ')[0]}`;

        document.getElementById('statActualBurn').textContent = `₹${m.actual_daily_burn.toLocaleString('en-IN', {minimumFractionDigits: 2})} / day`;
        document.getElementById('statRunwayText').textContent = m.remaining_balance > 0 ? `Runway: ~${m.runway_days} days at this velocity` : 'Budget depleted';

        // 5. Render Statistical Anomalies
        renderAnomalies(data.anomalies);

        // 6. Render Actionable Rule Recommendations
        renderRecommendations(data.recommendations, data.deductions);

        // 7. Render 50/30/20 Rule
        renderRule503020(data.rule_50_30_20);

    } catch (err) {
        console.error('Error fetching advisor insights:', err);
        const container = document.getElementById('recommendationsContainer');
        if (container) {
            container.innerHTML = '<div class="text-danger p-3">Failed to load financial diagnostic insights.</div>';
        }
    }
}

// ---------------------------------------------------------------------------
// Statistical Anomaly Detection Rendering
// ---------------------------------------------------------------------------
function renderAnomalies(anomalies) {
    const container = document.getElementById('anomaliesContainer');
    if (!container) return;

    if (!anomalies || anomalies.length === 0) {
        container.innerHTML = `
            <div class="alert alert-success border d-flex align-items-center gap-3 py-2 px-3 mb-0" style="border-radius: 8px;">
                <i class="bi bi-check-circle-fill text-success fs-4"></i>
                <div>
                    <h6 class="fw-bold mb-0 text-dark" style="font-size: 0.9rem;">Spending Baseline Stable</h6>
                    <small class="text-muted">All category expenditures are currently within normal baseline variation (&le;25% variance).</small>
                </div>
            </div>
        `;
        return;
    }

    let html = '';
    anomalies.forEach(a => {
        const borderClass = a.severity === 'danger' ? 'border-danger' : 'border-warning';
        const bgBadgeClass = a.severity === 'danger' ? 'bg-danger' : 'bg-warning text-dark';
        
        html += `
            <div class="alert alert-light border ${borderClass} d-flex align-items-start gap-3 p-3 mb-2" style="border-radius: 8px; background-color: #fff9f9;">
                <div class="p-2 rounded" style="background-color: ${a.color_code}15; color: ${a.color_code};">
                    <i class="bi ${a.icon} fs-4"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="d-flex flex-wrap align-items-center justify-content-between gap-1 mb-1">
                        <span class="fw-bold text-dark">${escapeHtml(a.category_name)}</span>
                        <span class="badge ${bgBadgeClass}">+${a.percent_increase}% Spike</span>
                    </div>
                    <div class="text-muted small mb-2">
                        Spent: <strong class="text-danger">₹${a.current_spent.toLocaleString('en-IN', {minimumFractionDigits: 2})}</strong> vs typical baseline of ₹${a.baseline_amount.toLocaleString('en-IN', {minimumFractionDigits: 2})}
                    </div>
                    <p class="mb-0 text-secondary" style="font-size: 0.84rem; line-height: 1.4;">
                        <i class="bi bi-arrow-right-circle text-primary me-1"></i>${escapeHtml(a.message)}
                    </p>
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Hybrid AI Smart Financial Audit (Google Gemini API with Local Fallback)
// ---------------------------------------------------------------------------
async function runSmartAudit() {
    const btn = document.getElementById('generateAuditBtn');
    const container = document.getElementById('smartAuditContainer');
    const badge = document.getElementById('auditSourceBadge');

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Auditing...';
    }

    if (container) {
        container.innerHTML = `
            <div class="text-center py-4 text-muted">
                <span class="spinner-border spinner-border-sm me-2 text-primary"></span>
                Evaluating budget velocity, category variances, and 50/30/20 balance...
            </div>
        `;
    }

    try {
        const res = await fetch('/api/advisor/smart-audit', { method: 'POST' });
        const data = await res.json();

        if (data.success && data.audit_points) {
            // Update source badge
            if (badge) {
                if (data.source === 'gemini') {
                    badge.className = 'badge bg-primary text-white border';
                    badge.innerHTML = '<i class="bi bi-stars me-1"></i>Powered by Gemini 2.5 Flash';
                } else {
                    badge.className = 'badge bg-light text-secondary border';
                    badge.innerHTML = '<i class="bi bi-shield-check text-success me-1"></i>Local Predictive Engine (Offline Safe)';
                }
            }

            // Render 3 concise actionable bullet cards
            let html = '<div class="row g-2">';
            data.audit_points.forEach((pt, idx) => {
                const icon = idx === 0 ? 'bi-speedometer2 text-danger' : (idx === 1 ? 'bi-exclamation-octagon text-warning' : 'bi-piggy-bank text-success');
                html += `
                    <div class="col-12">
                        <div class="p-3 border rounded bg-white shadow-sm h-100">
                            <div class="d-flex align-items-center justify-content-between mb-1">
                                <span class="fw-bold text-dark d-flex align-items-center gap-2">
                                    <i class="bi ${icon} fs-5"></i>
                                    <span>${escapeHtml(pt.title)}</span>
                                </span>
                                <span class="badge bg-light text-primary border" style="font-size: 0.72rem;">Action Item #${idx + 1}</span>
                            </div>
                            <p class="text-muted small mb-2" style="line-height: 1.45;">
                                ${escapeHtml(pt.advice)}
                            </p>
                            ${pt.impact ? `
                                <div class="d-inline-flex align-items-center gap-1 small text-success fw-semibold" style="font-size: 0.78rem;">
                                    <i class="bi bi-check2-circle"></i>
                                    <span><strong>Projected Impact:</strong> ${escapeHtml(pt.impact)}</span>
                                </div>
                            ` : ''}
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            if (container) container.innerHTML = html;
        } else {
            if (container) container.innerHTML = '<div class="text-muted p-3">Could not generate financial audit.</div>';
        }
    } catch (err) {
        if (container) container.innerHTML = '<div class="text-danger p-3">Failed to load financial audit.</div>';
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-stars me-1"></i>Generate Smart Audit';
        }
    }
}

// ---------------------------------------------------------------------------
// Actionable Rule Recommendations & Health Factors
// ---------------------------------------------------------------------------
function renderRecommendations(recommendations, deductions) {
    const container = document.getElementById('recommendationsContainer');
    if (!container) return;

    if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<div class="text-muted p-4 text-center">No diagnostic recommendations at this time.</div>';
        return;
    }

    let html = '';
    recommendations.forEach(rec => {
        html += `
            <div class="alert alert-${rec.type} border d-flex align-items-start gap-3 p-3 mb-2" style="border-radius: 8px;">
                <i class="bi ${rec.icon} fs-4 text-${rec.type} mt-1"></i>
                <div class="flex-grow-1">
                    <h6 class="fw-bold mb-1 text-dark">${escapeHtml(rec.title)}</h6>
                    <p class="mb-0 text-muted" style="font-size: 0.86rem; line-height: 1.4;">${escapeHtml(rec.text)}</p>
                </div>
            </div>
        `;
    });

    if (deductions && deductions.length > 0) {
        html += `
            <div class="p-3 bg-light border rounded mt-2">
                <div class="fw-semibold text-dark small mb-1">
                    <i class="bi bi-info-circle text-primary me-1"></i>Health Score Diagnostic Factors:
                </div>
                <ul class="mb-0 ps-3 text-muted small">
                    ${deductions.map(d => `<li>${escapeHtml(d)}</li>`).join('')}
                </ul>
            </div>
        `;
    }

    container.innerHTML = html;
}

// ---------------------------------------------------------------------------
// 50/30/20 Budgeting Rule Analytics
// ---------------------------------------------------------------------------
function renderRule503020(rule) {
    if (!rule) return;

    // Needs
    const needsBar = document.getElementById('needsProgressBar');
    const needsText = document.getElementById('needsPercentText');
    if (needsBar && needsText) {
        needsBar.style.width = `${Math.min(100, rule.needs_pct)}%`;
        needsText.textContent = `${rule.needs_pct}% (Target: 50%)`;
        needsBar.className = `progress-bar ${rule.needs_pct > 65 ? 'bg-danger' : (rule.needs_pct > 50 ? 'bg-warning' : 'bg-primary')}`;
    }

    // Wants
    const wantsBar = document.getElementById('wantsProgressBar');
    const wantsText = document.getElementById('wantsPercentText');
    if (wantsBar && wantsText) {
        wantsBar.style.width = `${Math.min(100, rule.wants_pct)}%`;
        wantsText.textContent = `${rule.wants_pct}% (Target: 30%)`;
        wantsBar.className = `progress-bar ${rule.wants_pct > 35 ? 'bg-danger' : 'bg-warning'}`;
    }

    // Buffer
    const bufferBar = document.getElementById('bufferProgressBar');
    const bufferText = document.getElementById('bufferPercentText');
    if (bufferBar && bufferText) {
        bufferBar.style.width = `${Math.min(100, rule.buffer_pct)}%`;
        bufferText.textContent = `${rule.buffer_pct}% (Target: 20%)`;
        bufferBar.className = `progress-bar ${rule.buffer_pct < 10 ? 'bg-danger' : (rule.buffer_pct < 20 ? 'bg-warning' : 'bg-success')}`;
    }
}

// ---------------------------------------------------------------------------
// "Can I Afford It?" Purchase Simulator
// ---------------------------------------------------------------------------
async function handleSimulatePurchase(event) {
    event.preventDefault();
    const resultBox = document.getElementById('simResultContainer');
    const btn = document.getElementById('simulateBtn');

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Evaluating...';

    const title = document.getElementById('simTitle').value.trim();
    const amount = parseFloat(document.getElementById('simAmount').value);

    try {
        const res = await fetch('/api/advisor/simulate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ title, amount })
        });
        const data = await res.json();

        if (data.success) {
            resultBox.classList.remove('d-none');
            resultBox.innerHTML = `
                <div class="alert alert-${data.verdict_color} border p-3">
                    <div class="d-flex align-items-center gap-2 mb-2">
                        <i class="bi ${data.verdict_icon} fs-5 text-${data.verdict_color}"></i>
                        <span class="badge bg-${data.verdict_color} text-uppercase">${escapeHtml(data.verdict)}</span>
                    </div>
                    <div class="fw-semibold text-dark mb-1" style="font-size: 0.9rem;">${escapeHtml(data.title)} (₹${data.purchase_amount.toLocaleString('en-IN')})</div>
                    <p class="small text-muted mb-2">${escapeHtml(data.message)}</p>

                    <div class="p-2 bg-white rounded border small">
                        <div class="d-flex justify-content-between mb-1">
                            <span>Pre-purchase Daily Limit:</span>
                            <strong>₹${data.current_daily_limit.toFixed(2)}/day</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Post-purchase Daily Limit:</span>
                            <strong class="${data.new_daily_limit < 100 ? 'text-danger' : 'text-success'}">₹${data.new_daily_limit.toFixed(2)}/day</strong>
                        </div>
                    </div>
                </div>
            `;
        } else {
            alert(data.message || 'Simulation failed.');
        }
    } catch (err) {
        alert('Server connection error.');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="bi bi-lightning-charge me-1"></i>Evaluate Affordability';
    }
}

function escapeHtml(str) {
    if (!str) return '';
    return str.toString().replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}
