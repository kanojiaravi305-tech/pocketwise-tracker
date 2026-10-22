"""
backend/controllers/budget_controller.py
Controller handling Budget Threshold Alerts (80% and 100%),
visual chart analytics (Chart.js), and category-wise limit tracking.
"""

from datetime import date
from flask import request, jsonify, session
from backend.models.user_model import UserModel
from backend.models.expense_model import ExpenseModel
from backend.models.category_model import CategoryModel

class BudgetController:
    @staticmethod
    def get_dashboard_stats():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        user = UserModel.get_by_id(user_id)
        if not user:
            return jsonify({"success": False, "message": "User not found"}), 404

        actual_uid = user["user_id"]
        session["user_id"] = actual_uid

        # Auto-seed if user budget is 0 or transactions are empty in MongoDB
        try:
            from database.init_mongo import ensure_user_seeded
            ensure_user_seeded(actual_uid)
            user = UserModel.get_by_id(actual_uid)
        except Exception as e:
            print(f"[!] Warning during ensure_user_seeded: {e}")

        today = date.today()
        current_month_str = today.strftime("%Y-%m")
        current_month_name = today.strftime("%B %Y")

        monthly_budget = float(user.get("monthly_budget_limit", 50000.0))
        if monthly_budget <= 0:
            monthly_budget = 50000.0
            UserModel.update_budget_limit(actual_uid, monthly_budget)

        total_spent = ExpenseModel.get_monthly_total(actual_uid, current_month_str)
        remaining_balance = monthly_budget - total_spent
        percent_spent = round((total_spent / monthly_budget * 100.0), 1) if monthly_budget > 0 else 0.0

        # Module B: 80% and 100% Threshold Alert Logic
        alert = None
        if percent_spent >= 100.0:
            over_amount = total_spent - monthly_budget
            alert = {
                "type": "danger",
                "badge": "CRITICAL ALERT",
                "icon": "bi-exclamation-triangle-fill",
                "title": f"Monthly Budget Exceeded by INR {over_amount:,.2f}!",
                "message": f"You have spent INR {total_spent:,.2f} of your INR {monthly_budget:,.2f} limit ({percent_spent}%). Please curtail non-essential expenses."
            }
        elif percent_spent >= 80.0:
            alert = {
                "type": "warning",
                "badge": "BUDGET WARNING",
                "icon": "bi-exclamation-circle-fill",
                "title": f"Approaching Budget Limit ({percent_spent}% Used)",
                "message": f"You have utilized INR {total_spent:,.2f} out of INR {monthly_budget:,.2f}. Only INR {remaining_balance:,.2f} remains for {current_month_name}."
            }

        # Doughnut Chart Data (Category Breakdown for current month)
        breakdown_rows = ExpenseModel.get_category_breakdown(actual_uid, current_month_str)
        doughnut_labels = [r["category_name"] for r in breakdown_rows]
        doughnut_data = [float(r["total_amount"]) for r in breakdown_rows]
        doughnut_colors = [r["color_code"] for r in breakdown_rows]

        # Month-on-Month 6-Month Trend Bar Chart Data
        trend_rows = ExpenseModel.get_six_months_trend(actual_uid)
        
        # Build month labels in format "MMM YYYY"
        trend_dict = {r["month_key"]: float(r["total_amount"]) for r in trend_rows}
        bar_labels = []
        bar_data = []

        # Iterate last 6 calendar months in chronological order
        for i in range(5, -1, -1):
            y = today.year
            m = today.month - i
            while m <= 0:
                m += 12
                y -= 1
            m_key = f"{y:04d}-{m:02d}"
            m_label = date(y, m, 1).strftime("%b %y")
            bar_labels.append(m_label)
            bar_data.append(trend_dict.get(m_key, 0.0))

        # Recent 5 Transactions
        recent_rows = ExpenseModel.get_filtered(actual_uid, limit=5)
        recent_list = [
            {
                "expense_id": r["expense_id"],
                "category_name": r["category_name"],
                "color_code": r["color_code"],
                "icon_name": r["icon_name"],
                "title": r["title"],
                "amount": float(r["amount"]),
                "payment_mode": r["payment_mode"],
                "expense_date": r["expense_date"],
            }
            for r in recent_rows
        ]

        return jsonify({
            "success": True,
            "month_name": current_month_name,
            "metrics": {
                "monthly_budget": monthly_budget,
                "total_spent": total_spent,
                "remaining_balance": remaining_balance,
                "percent_spent": percent_spent,
            },
            "alert": alert,
            "doughnut_chart": {
                "labels": doughnut_labels,
                "data": doughnut_data,
                "colors": doughnut_colors,
            },
            "bar_chart": {
                "labels": bar_labels,
                "data": bar_data,
            },
            "recent_transactions": recent_list,
        })

    @staticmethod
    def get_category_budgets():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        today = date.today()
        current_month_str = today.strftime("%Y-%m")
        categories_data = CategoryModel.get_spending_with_limits(user_id, current_month_str)

        user = UserModel.get_by_id(user_id)
        monthly_budget = float(user["monthly_budget_limit"])
        total_spent = ExpenseModel.get_monthly_total(user_id, current_month_str)

        items = []
        for row in categories_data:
            pct = float(row["percent_used"])
            # Determine bootstrap status color
            if pct >= 100:
                status_color = "danger"
            elif pct >= 80:
                status_color = "warning"
            else:
                status_color = "success"

            items.append({
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "icon_name": row["icon_name"],
                "color_code": row["color_code"],
                "monthly_limit": float(row["monthly_limit"]),
                "spent_amount": float(row["spent_amount"]),
                "percent_used": pct,
                "status_color": status_color,
            })

        return jsonify({
            "success": True,
            "month_name": today.strftime("%B %Y"),
            "total_budget": monthly_budget,
            "total_spent": total_spent,
            "overall_percent": round((total_spent / monthly_budget * 100.0), 1) if monthly_budget > 0 else 0.0,
            "categories": items,
        })

    @staticmethod
    def update_monthly_budget():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        try:
            new_limit = float(data.get("monthly_budget_limit", 0))
            if new_limit <= 0:
                return jsonify({"success": False, "message": "Budget limit must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical limit required."}), 400

        UserModel.update_budget_limit(user_id, new_limit)
        return jsonify({"success": True, "message": "Monthly budget limit updated successfully!"})

    @staticmethod
    def update_category_limit(category_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        try:
            new_limit = float(data.get("monthly_limit", 0))
            if new_limit <= 0:
                return jsonify({"success": False, "message": "Limit must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical limit required."}), 400

        success = CategoryModel.update_limit(category_id, new_limit)
        if not success:
            return jsonify({"success": False, "message": "Category not found."}), 404

        return jsonify({"success": True, "message": "Category budget limit updated successfully!"})
