"""
backend/controllers/advisor_controller.py
Student Financial Advisor & Budget Health Diagnostic Engine.
Analyzes spending velocity, 50/30/20 student budgeting rule,
roommate recovery opportunities, and provides an interactive "Can I Afford It?" purchase simulator.
"""

import calendar
from datetime import date
from flask import request, jsonify, session
from backend.models.user_model import UserModel
from backend.models.expense_model import ExpenseModel
from backend.models.category_model import CategoryModel
from backend.models.split_model import SplitModel

class AdvisorController:
    @staticmethod
    def get_financial_insights():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        today = date.today()
        current_month_str = today.strftime("%Y-%m")
        month_name = today.strftime("%B %Y")
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_passed = max(1, today.day)
        days_left = max(1, days_in_month - today.day)

        monthly_budget = float(user["monthly_budget_limit"])
        total_spent = ExpenseModel.get_monthly_total(user_id, current_month_str)
        remaining_balance = monthly_budget - total_spent
        percent_spent = round((total_spent / monthly_budget * 100.0), 1) if monthly_budget > 0 else 0.0

        # Burn Rate & Safe Daily Spending
        actual_daily_burn = round(total_spent / days_passed, 2)
        safe_daily_limit = round(max(0.0, remaining_balance / days_left), 2)
        
        # Projected month-end spend at current velocity
        projected_total_spent = round(actual_daily_burn * days_in_month, 2)
        runway_days = round(remaining_balance / actual_daily_burn, 1) if actual_daily_burn > 0 and remaining_balance > 0 else (0 if remaining_balance <= 0 else 99)

        # Roommate Debts (IOUs)
        split_stats = SplitModel.get_split_stats(user_id)
        total_pending_recovery = split_stats.get("total_pending", 0.0)
        pending_splits = SplitModel.get_user_splits(user_id, status="pending")
        debtor_names = list(set([s["friend_name"] for s in pending_splits]))

        # Category Breakdown
        categories_data = CategoryModel.get_spending_with_limits(user_id, current_month_str)

        # 50/30/20 Budgeting Rule Analysis:
        # Needs: Housing, Groceries, Commute & Fuel, Utilities & Bills, Healthcare
        # Wants: Shopping & Lifestyle, Miscellaneous
        # Savings / Buffer: Investments & Savings, plus unspent monthly balance
        needs_spent = 0.0
        wants_spent = 0.0
        savings_spent = 0.0
        for cat in categories_data:
            cname = cat["category_name"]
            amt = float(cat["spent_amount"])
            if any(n in cname for n in ["Housing", "Groceries", "Commute", "Utilities", "Healthcare"]):
                needs_spent += amt
            elif any(n in cname for n in ["Investments", "Savings"]):
                savings_spent += amt
            else:
                wants_spent += amt

        needs_pct = round((needs_spent / monthly_budget * 100.0), 1) if monthly_budget > 0 else 0.0
        wants_pct = round((wants_spent / monthly_budget * 100.0), 1) if monthly_budget > 0 else 0.0
        buffer_pct = round(max(0.0, 100.0 - needs_pct - wants_pct), 1)

        # Financial Health Score (0 - 100)
        health_score = 100
        deductions = []

        if percent_spent >= 100:
            health_score -= 40
            deductions.append("Exceeded total monthly budget limit (-40)")
        elif percent_spent >= 80:
            health_score -= 20
            deductions.append("Utilized over 80% of monthly budget (-20)")
        elif percent_spent >= 60:
            health_score -= 10
            deductions.append("Pacing fast: over 60% budget spent (-10)")

        if actual_daily_burn > (safe_daily_limit * 1.25) and days_left > 3:
            health_score -= 15
            deductions.append(f"High burn rate: spending ₹{actual_daily_burn:.0f}/day vs safe limit ₹{safe_daily_limit:.0f}/day (-15)")

        if total_pending_recovery >= (monthly_budget * 0.10):
            health_score -= 10
            deductions.append(f"High pending receivables: ₹{total_pending_recovery:.0f} tied up in shared expense splits (-10)")

        health_score = max(15, min(100, health_score))

        if health_score >= 80:
            score_status = "Disciplined & Healthy"
            score_color = "success"
        elif health_score >= 60:
            score_status = "Moderate Caution"
            score_color = "warning"
        else:
            score_status = "High Burn Alert"
            score_color = "danger"

        # Actionable Heuristic Recommendations
        recommendations = []

        # 1. Runway Recommendation
        if remaining_balance <= 0:
            recommendations.append({
                "type": "danger",
                "icon": "bi-exclamation-octagon-fill",
                "title": "Monthly Budget Depleted",
                "text": f"You have exceeded your monthly budget by ₹{abs(remaining_balance):,.2f}. Freeze discretionary dining and shopping spends until next month's salary/income arrives."
            })
        elif runway_days < days_left:
            deficit_days = round(days_left - runway_days, 1)
            recommendations.append({
                "type": "warning",
                "icon": "bi-speedometer2",
                "title": f"Runway Shortfall Warning ({deficit_days} Days Gap)",
                "text": f"At your current spending rate of ₹{actual_daily_burn:,.2f}/day, your remaining funds will last only ~{runway_days:.0f} days, but there are {days_left} days left in {today.strftime('%B')}. Reduce discretionary expenditure to ₹{safe_daily_limit:,.2f}/day to finish month-end comfortably."
            })
        else:
            recommendations.append({
                "type": "success",
                "icon": "bi-check-circle-fill",
                "title": "Spending Pacing Comfortably On Track",
                "text": f"You have ₹{safe_daily_limit:,.2f}/day of safe spending capacity for the remaining {days_left} days. Your cash flow is in a healthy surplus."
            })

        # 2. Shared Group Recovery Recommendation
        if total_pending_recovery > 0:
            debtors_str = ", ".join(debtor_names[:3])
            recommendations.append({
                "type": "info",
                "icon": "bi-people-fill",
                "title": f"Recover ₹{total_pending_recovery:,.2f} from Group Members",
                "text": f"You have pending expense claims from {debtors_str}{' and others' if len(debtor_names) > 3 else ''}. Following up on these repayments will boost your available cash balance by {round((total_pending_recovery / monthly_budget) * 100, 1)}%."
            })

        # 3. Category Overspend Recommendations
        overspent_categories = [c for c in categories_data if c["percent_used"] >= 90]
        if overspent_categories:
            top_over = overspent_categories[0]
            recommendations.append({
                "type": "warning",
                "icon": "bi-tag-fill",
                "title": f"Limit Reached: {top_over['category_name']}",
                "text": f"You have spent ₹{top_over['spent_amount']:,.2f} out of its ₹{top_over['monthly_limit']:,.2f} limit ({top_over['percent_used']}%). Keep discretionary purchases in this category paused for the rest of the month."
            })

        # 4. Professional Savings & Investment Tip
        # 5. Predictive Engine: Next Month Prediction & Statistical Anomaly Detection
        from backend.services.predictive_engine import predict_next_month_spend, detect_category_anomalies
        prediction = predict_next_month_spend(user_id, current_month_str)
        anomalies = detect_category_anomalies(user_id, current_month_str)

        return jsonify({
            "success": True,
            "month_name": month_name,
            "health_score": health_score,
            "score_status": score_status,
            "score_color": score_color,
            "deductions": deductions,
            "metrics": {
                "monthly_budget": monthly_budget,
                "total_spent": total_spent,
                "remaining_balance": remaining_balance,
                "percent_spent": percent_spent,
                "days_passed": days_passed,
                "days_left": days_left,
                "days_in_month": days_in_month,
                "actual_daily_burn": actual_daily_burn,
                "safe_daily_limit": safe_daily_limit,
                "projected_total_spent": projected_total_spent,
                "runway_days": runway_days,
                "total_pending_recovery": total_pending_recovery,
            },
            "rule_50_30_20": {
                "needs_spent": needs_spent,
                "needs_pct": needs_pct,
                "wants_spent": wants_spent,
                "wants_pct": wants_pct,
                "buffer_pct": buffer_pct,
            },
            "prediction": prediction,
            "anomalies": anomalies,
            "recommendations": recommendations,
        })


    @staticmethod
    def simulate_purchase():
        """
        Interactive 'Can I Afford It?' simulator.
        Calculates impact of an upcoming expense on daily budget runway.
        """
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        data = request.get_json() or request.form
        title = data.get("title", "").strip() or "Planned Purchase"
        try:
            purchase_amount = float(data.get("amount", 0.0))
            if purchase_amount <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical amount required."}), 400

        today = date.today()
        current_month_str = today.strftime("%Y-%m")
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        days_left = max(1, days_in_month - today.day)

        monthly_budget = float(user["monthly_budget_limit"])
        total_spent = ExpenseModel.get_monthly_total(user_id, current_month_str)
        current_remaining = monthly_budget - total_spent
        current_daily_limit = round(max(0.0, current_remaining / days_left), 2)

        new_remaining = current_remaining - purchase_amount
        new_daily_limit = round(max(0.0, new_remaining / days_left), 2)
        new_percent_spent = round(((total_spent + purchase_amount) / monthly_budget) * 100.0, 1)

        if new_remaining < 0:
            verdict = "NOT RECOMMENDED (Deficit Risk)"
            verdict_color = "danger"
            verdict_icon = "bi-x-octagon-fill"
            message = f"Buying this will exceed your monthly budget by ₹{abs(new_remaining):,.2f}. You will have ₹0/day for the remaining {days_left} days of this month."
        elif new_daily_limit < 100.0 and days_left > 3:
            verdict = "EXERCISE CAUTION (Tight Runway)"
            verdict_color = "warning"
            verdict_icon = "bi-exclamation-triangle-fill"
            message = f"You can technically afford it, but it will reduce your safe daily spending allowance from ₹{current_daily_limit:,.2f}/day down to ₹{new_daily_limit:,.2f}/day for {days_left} days."
        else:
            verdict = "SAFE TO PURCHASE"
            verdict_color = "success"
            verdict_icon = "bi-check-circle-fill"
            message = f"This purchase fits comfortably within your budget! You will still have ₹{new_daily_limit:,.2f}/day available for the remaining {days_left} days."

        return jsonify({
            "success": True,
            "title": title,
            "purchase_amount": purchase_amount,
            "current_remaining": current_remaining,
            "new_remaining": new_remaining,
            "current_daily_limit": current_daily_limit,
            "new_daily_limit": new_daily_limit,
            "new_percent_spent": new_percent_spent,
            "verdict": verdict,
            "verdict_color": verdict_color,
            "verdict_icon": verdict_icon,
            "message": message,
        })

    @staticmethod
    def generate_audit():
        """
        Triggers Hybrid Smart Financial Audit (Google Gemini API with local heuristic fallback).
        """
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        today = date.today()
        current_month_str = today.strftime("%Y-%m")

        from backend.services.predictive_engine import generate_smart_audit
        audit_result = generate_smart_audit(user_id, current_month_str)
        return jsonify(audit_result)

