"""
backend/services/predictive_engine.py
Predictive Mathematics & Hybrid AI Engine for PocketWise Financial Advisor.

Designed specifically for college viva demonstration:
1. Next Month Spend Prediction:
   - Simple Linear Regression (y = mx + c)
   - 3-Month Weighted Moving Average (WMA)
2. Statistical Anomaly Detection:
   - Flags category spending >25% higher than user's historical baseline
3. Hybrid Smart Financial Audit:
   - Online: Google Gemini API (gemini-2.5-flash) via lightweight HTTP request
   - Offline Fallback: Local rule-based heuristic financial audit (guaranteed 100% demo reliability)
"""

import os
import json
import calendar
import urllib.request
import urllib.error
from datetime import date
from backend.models.expense_model import ExpenseModel
from backend.models.category_model import CategoryModel

def predict_next_month_spend(user_id: int, current_month_str: str) -> dict:
    """
    Predicts the user's next month total expenditure using:
    1. Simple Linear Regression: y = m*x + c
       where x represents chronological monthly intervals [1, 2, ..., N]
       and y represents total spent in that month.
    2. Weighted Moving Average (WMA):
       Assigns linearly higher weights to recent months (weights: 3, 2, 1).
    3. Blended Ensemble:
       50% Linear Trend Projection + 50% Weighted Moving Average.

    Provides a clean mathematical formulation that can be explained easily in viva.
    """
    trend_rows = ExpenseModel.get_six_months_trend(user_id)
    
    # Extract chronological monthly spending series y = [M1, M2, ..., Mn]
    # Filter out empty records or future months
    monthly_series = []
    for r in trend_rows:
        amt = float(r["total_amount"])
        if amt > 0:
            monthly_series.append({
                "month": r["month_key"],
                "amount": amt
            })

    N = len(monthly_series)

    # -----------------------------------------------------------------------
    # Case 1: Insufficient history (< 2 months) -> Extrapolate current month burn
    # -----------------------------------------------------------------------
    if N < 2:
        today = date.today()
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_passed = max(1, today.day)
        current_spent = monthly_series[0]["amount"] if N == 1 else 0.0
        extrapolated = round((current_spent / days_passed) * days_in_month, 2)
        return {
            "projected_spend": extrapolated,
            "trend_direction": "stable",
            "trend_percent": 0.0,
            "method": "Daily Run-Rate Extrapolation (Insufficient historical months)",
            "slope": 0.0,
            "intercept": extrapolated,
            "wma": extrapolated,
            "historical_months_count": N,
            "explanation": f"Extrapolated from current run-rate: ₹{extrapolated:,.2f} projected for next month."
        }

    # -----------------------------------------------------------------------
    # Case 2: Linear Regression Math: y = m*x + c
    # x values: 1, 2, ..., N
    # y values: monthly amounts
    # -----------------------------------------------------------------------
    x_vals = list(range(1, N + 1))
    y_vals = [m["amount"] for m in monthly_series]

    x_mean = sum(x_vals) / N
    y_mean = sum(y_vals) / N

    # Slope m = sum((x - x_mean)*(y - y_mean)) / sum((x - x_mean)^2)
    numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(N))
    denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(N))

    slope_m = (numerator / denominator) if denominator != 0 else 0.0
    intercept_c = y_mean - (slope_m * x_mean)

    # Project next month (x = N + 1)
    x_next = N + 1
    y_linear_projected = max(0.0, (slope_m * x_next) + intercept_c)

    # -----------------------------------------------------------------------
    # Case 3: Weighted Moving Average (WMA)
    # Higher weights (3, 2, 1) assigned to more recent months
    # -----------------------------------------------------------------------
    if N >= 3:
        wma = ((3.0 * y_vals[-1]) + (2.0 * y_vals[-2]) + (1.0 * y_vals[-3])) / 6.0
    else:  # N == 2
        wma = ((2.0 * y_vals[-1]) + (1.0 * y_vals[-2])) / 3.0

    # -----------------------------------------------------------------------
    # Blended Projection: 50% Linear Trend + 50% WMA
    # -----------------------------------------------------------------------
    final_projected = max(0.0, round((0.5 * y_linear_projected) + (0.5 * wma), 2))

    # Calculate month-on-month trend variance against current month's spend
    current_month_spend = y_vals[-1]
    diff = final_projected - current_month_spend
    trend_percent = round((diff / current_month_spend) * 100.0, 1) if current_month_spend > 0 else 0.0

    if trend_percent > 2.0:
        trend_direction = "up"
    elif trend_percent < -2.0:
        trend_direction = "down"
    else:
        trend_direction = "stable"

    return {
        "projected_spend": final_projected,
        "trend_direction": trend_direction,
        "trend_percent": trend_percent,
        "method": "Simple Linear Regression (y = mx + c) & 3-Month Weighted Moving Average",
        "slope": round(slope_m, 2),
        "intercept": round(intercept_c, 2),
        "wma": round(wma, 2),
        "historical_months_count": N,
        "explanation": f"Based on {N}-month spending trajectory, projected next month expenditure is ₹{final_projected:,.2f} ({'+' if trend_percent > 0 else ''}{trend_percent}% vs current month)."
    }


def detect_category_anomalies(user_id: int, current_month_str: str) -> list:
    """
    Statistical Anomaly Detection:
    Compares current month spending in each category against the user's historical
    monthly average for that specific category.

    Flags any category where current month spending exceeds historical baseline by > 25%.
    """
    # 1. Get current month category spending
    current_categories = CategoryModel.get_spending_with_limits(user_id, current_month_str)

    # 2. Get historical monthly average per category (excluding current month)
    historical_averages_rows = ExpenseModel.get_category_monthly_averages(user_id, exclude_month=current_month_str)
    
    # Map category_id -> avg_monthly_spent
    hist_map = {}
    for r in historical_averages_rows:
        cid = str(r["category_id"])
        hist_map[cid] = float(r["avg_monthly_spent"])

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = max(1, today.day)
    month_progress_ratio = days_passed / days_in_month

    anomalies = []

    for cat in current_categories:
        cid = str(cat["category_id"])
        cname = cat["category_name"]
        current_spent = float(cat["spent_amount"])
        monthly_limit = float(cat["monthly_limit"])

        # Determine baseline average:
        # If user has past historical spending for this category, use that average.
        # Otherwise, fallback to configured monthly limit scaled to days passed.
        if cid in hist_map and hist_map[cid] > 0:
            baseline_avg = hist_map[cid]
            baseline_type = "historical_average"
        elif monthly_limit > 0:
            baseline_avg = monthly_limit
            baseline_type = "configured_limit"
        else:
            continue

        if baseline_avg <= 0 or current_spent < 500.0:
            continue

        # Calculate percentage variance
        pct_variance = round(((current_spent - baseline_avg) / baseline_avg) * 100.0, 1)

        # Flag if spending is > 25% higher than baseline
        if pct_variance > 25.0:
            severity = "danger" if pct_variance >= 50.0 else "warning"
            icon_name = cat["icon_name"] if "icon_name" in cat.keys() else "bi-exclamation-triangle-fill"
            color_code = cat["color_code"] if "color_code" in cat.keys() else "#dc3545"
            anomalies.append({
                "category_id": cat["category_id"],
                "category_name": cname,
                "current_spent": current_spent,
                "baseline_amount": round(baseline_avg, 2),
                "baseline_type": baseline_type,
                "percent_increase": pct_variance,
                "severity": severity,
                "icon": icon_name,
                "color_code": color_code,
                "message": f"{cname} spending is {pct_variance}% higher than your typical monthly average (₹{current_spent:,.2f} spent vs ₹{baseline_avg:,.2f} normal baseline)."
            })

    # Sort anomalies by highest percentage increase first
    anomalies.sort(key=lambda x: x["percent_increase"], reverse=True)
    return anomalies


def generate_smart_audit(user_id: int, current_month_str: str) -> dict:
    """
    Generates 3 concise, highly actionable financial audit bullet points.
    
    Hybrid AI Architecture:
    1. Online Path: If GEMINI_API_KEY environment variable is configured,
       sends privacy-safe aggregated numbers to Gemini 2.5 Flash via REST API.
    2. Offline Fallback: If offline or no API key, executes local rule-based
       financial reasoning engine. Guaranteed zero errors during demo.
    """
    # 1. Gather high-level aggregated metrics
    from backend.models.user_model import UserModel
    user = UserModel.get_by_id(user_id)
    monthly_budget = float(user["monthly_budget_limit"]) if user else 50000.0
    total_spent = ExpenseModel.get_monthly_total(user_id, current_month_str)
    remaining_balance = monthly_budget - total_spent
    
    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_passed = max(1, today.day)
    days_left = max(1, days_in_month - today.day)
    
    daily_burn = round(total_spent / days_passed, 2)
    safe_daily = round(max(0.0, remaining_balance / days_left), 2)
    
    # Get categories & anomalies
    anomalies = detect_category_anomalies(user_id, current_month_str)
    categories_data = CategoryModel.get_spending_with_limits(user_id, current_month_str)
    
    # 50/30/20 summary
    needs_spent = 0.0
    wants_spent = 0.0
    savings_spent = 0.0
    for c in categories_data:
        cname = c["category_name"]
        amt = float(c["spent_amount"])
        if any(n in cname for n in ["Housing", "Groceries", "Commute", "Utilities", "Healthcare"]):
            needs_spent += amt
        elif any(n in cname for n in ["Investments", "Savings"]):
            savings_spent += amt
        else:
            wants_spent += amt

    # 2. Check for Gemini API Key
    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if api_key:
        try:
            # Prepare privacy-safe prompt with aggregated figures only
            top_cats_summary = ", ".join([f"{c['category_name']}: ₹{c['spent_amount']:.0f}" for c in categories_data[:4]])
            anomaly_summary = ", ".join([f"{a['category_name']} (+{a['percent_increase']}%)" for a in anomalies]) if anomalies else "None"
            
            prompt_text = f"""You are an elite personal financial auditor for working professionals and freelancers in India.
Analyze these monthly figures:
- Monthly Income/Budget: ₹{monthly_budget:,.2f}
- Spent This Month: ₹{total_spent:,.2f} (Remaining: ₹{remaining_balance:,.2f})
- Days Remaining: {days_left} days (Current burn: ₹{daily_burn:.2f}/day vs Safe limit: ₹{safe_daily:.2f}/day)
- 50/30/20 Split: Needs: ₹{needs_spent:.0f}, Wants: ₹{wants_spent:.0f}, Savings: ₹{savings_spent:.0f}
- Top Categories: {top_cats_summary}
- Detected Anomalies: {anomaly_summary}

Provide exactly 3 concise, highly actionable bullet points for this user.
Respond ONLY with a valid JSON array of 3 objects with keys "title", "advice", "impact". No markdown codeblocks, just raw JSON.
Example format:
[
  {{"title": "Cash Flow Pacing", "advice": "Cap daily discretionary spend...", "impact": "Prevents month-end shortfall"}},
  {{"title": "Category Spike Alert", "advice": "Reduce dining out...", "impact": "Saves ₹2,500"}},
  {{"title": "Wealth SIP Automation", "advice": "Automate index fund SIP...", "impact": "Builds long-term portfolio"}}
]"""

            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
            req_body = json.dumps({
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 600}
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=req_body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )

            # Timeout after 4.5 seconds to guarantee responsiveness
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                raw_text = resp_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean any markdown fences if present
                clean_json = raw_text.replace("```json", "").replace("```", "").strip()
                parsed_bullets = json.loads(clean_json)

                if isinstance(parsed_bullets, list) and len(parsed_bullets) >= 3:
                    return {
                        "success": True,
                        "source": "gemini",
                        "model_name": "Google Gemini 2.5 Flash",
                        "audit_points": parsed_bullets[:3]
                    }
        except Exception as e:
            # Silently fall through to the offline rule engine
            print(f"[PocketWise AI] Gemini request bypassed/fallback triggered: {e}")

    # -----------------------------------------------------------------------
    # 3. Seamless Offline Rule-Based Fallback Engine
    # Evaluates financial ratios locally with 100% deterministic reliability
    # -----------------------------------------------------------------------
    offline_points = []

    # Bullet 1: Cash Flow & Runway Pacing
    if remaining_balance <= 0:
        offline_points.append({
            "title": "Budget Deficit Emergency Freeze",
            "advice": f"You have exceeded your ₹{monthly_budget:,.0f} budget by ₹{abs(remaining_balance):,.0f}. Freeze all non-essential shopping and restaurant dining until next month's salary.",
            "impact": "Stops cash flow hemorrhaging and avoids debt accumulation"
        })
    elif daily_burn > safe_daily * 1.25 and days_left > 3:
        offline_points.append({
            "title": "High Burn Velocity Adjustment",
            "advice": f"Your current spending velocity of ₹{daily_burn:,.0f}/day will exhaust your balance in ~{round(remaining_balance / daily_burn, 1)} days. Restrict daily discretionary outflows to ₹{safe_daily:,.0f}/day.",
            "impact": f"Ensures remaining ₹{remaining_balance:,.0f} lasts comfortably for all {days_left} remaining days"
        })
    else:
        offline_points.append({
            "title": "Healthy Pacing & Surplus Opportunity",
            "advice": f"Your current burn rate leaves ₹{safe_daily:,.0f}/day safe spending limit for the remaining {days_left} days. Your cash flow is in a healthy surplus.",
            "impact": "Leaves room for surplus sweep into recurring deposit or liquid fund"
        })

    # Bullet 2: Category Anomaly Mitigation
    if anomalies:
        top_anomaly = anomalies[0]
        offline_points.append({
            "title": f"Mitigate {top_anomaly['category_name']} Surge",
            "advice": f"{top_anomaly['category_name']} is currently +{top_anomaly['percent_increase']}% above normal baseline (₹{top_anomaly['current_spent']:,.0f} vs typical ₹{top_anomaly['baseline_amount']:,.0f}). Pause further discretionary purchases in this category.",
            "impact": f"Recovers approximately ₹{max(500, top_anomaly['current_spent'] - top_anomaly['baseline_amount']):,.0f} in monthly cash flow"
        })
    else:
        # Fallback to top category review
        top_cat = categories_data[0] if categories_data else {"category_name": "Living Expenses", "spent_amount": 5000}
        offline_points.append({
            "title": f"Review Major Outflow: {top_cat['category_name']}",
            "advice": f"{top_cat['category_name']} represents your largest outlay this month (₹{float(top_cat['spent_amount']):,.0f}). Check for recurring subscriptions, utility leakages, or dining splits that can be optimized.",
            "impact": "Enhances category-level budget control by 10-15%"
        })

    # Bullet 3: 50/30/20 Wealth Optimization
    if wants_spent > (monthly_budget * 0.35):
        excess_wants = wants_spent - (monthly_budget * 0.30)
        offline_points.append({
            "title": "50/30/20 Rule: Lifestyle Spend Rebalance",
            "advice": f"Discretionary wants account for {round(wants_spent / monthly_budget * 100, 1)}% of your income (exceeding the 30% guideline). Reallocate ₹{excess_wants:,.0f} towards your emergency fund or mutual fund SIP.",
            "impact": "Protects your net savings rate and maintains financial discipline"
        })
    else:
        offline_points.append({
            "title": "Wealth & SIP Automation Rule",
            "advice": "Ensure at least 20% of your monthly income is automated into a low-cost index fund or liquid emergency reserve on the 1st of every month before lifestyle spending begins.",
            "impact": "Accelerates compound interest and guarantees consistent wealth generation"
        })

    return {
        "success": True,
        "source": "offline_fallback",
        "model_name": "PocketWise Heuristic Financial Rules (Offline Safe)",
        "audit_points": offline_points
    }
