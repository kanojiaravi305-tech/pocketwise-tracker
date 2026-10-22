"""
backend/controllers/savings_controller.py
Controller handling Savings Goals CRUD and "+ Add Funds" contributions.
"""

from flask import request, jsonify, session
from backend.models.savings_model import SavingsModel

class SavingsController:
    @staticmethod
    def list_goals():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        goals = SavingsModel.get_all(user_id)

        # Aggregate metrics
        total_target = sum(g["target_amount"] for g in goals)
        total_saved = sum(g["current_amount"] for g in goals)
        overall_progress = min(100.0, round((total_saved / total_target * 100), 1)) if total_target > 0 else 0.0
        completed_count = sum(1 for g in goals if g["is_completed"])

        return jsonify({
            "success": True,
            "goals": goals,
            "metrics": {
                "total_goals": len(goals),
                "completed_goals": completed_count,
                "total_target": total_target,
                "total_saved": total_saved,
                "total_remaining": max(0.0, total_target - total_saved),
                "overall_progress": overall_progress,
            }
        })

    @staticmethod
    def create_goal():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = (data.get("title") or "").strip()
        target_amount_raw = data.get("target_amount")
        current_amount_raw = data.get("current_amount", 0.0)
        target_date = (data.get("target_date") or "").strip()
        category_icon = data.get("category_icon", "bi-piggy-bank")
        color_code = data.get("color_code", "#059669")
        notes = (data.get("notes") or "").strip()

        if not title:
            return jsonify({"success": False, "message": "Goal title is required."}), 400

        try:
            target_amount = float(target_amount_raw)
            if target_amount <= 0:
                return jsonify({"success": False, "message": "Target amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical target amount is required."}), 400

        try:
            current_amount = float(current_amount_raw) if current_amount_raw else 0.0
            if current_amount < 0:
                current_amount = 0.0
        except (ValueError, TypeError):
            current_amount = 0.0

        goal_id = SavingsModel.create(
            user_id=user_id,
            title=title,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            category_icon=category_icon,
            color_code=color_code,
            notes=notes
        )

        return jsonify({
            "success": True,
            "message": f"Savings goal '{title}' created successfully!",
            "goal_id": str(goal_id)
        }), 201

    @staticmethod
    def add_funds(goal_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        amount_raw = data.get("amount")
        note = (data.get("note") or "").strip()

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return jsonify({"success": False, "message": "Deposit amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical deposit amount is required."}), 400

        success, err = SavingsModel.add_funds(goal_id, user_id, amount, note)
        if err or not success:
            return jsonify({"success": False, "message": err or "Goal not found."}), 400

        return jsonify({
            "success": True,
            "message": f"Successfully added ₹{amount:,.2f} to savings goal!"
        })

    @staticmethod
    def update_goal(goal_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = (data.get("title") or "").strip()
        target_amount_raw = data.get("target_amount")
        target_date = (data.get("target_date") or "").strip()
        category_icon = data.get("category_icon", "bi-piggy-bank")
        color_code = data.get("color_code", "#059669")
        notes = (data.get("notes") or "").strip()

        if not title:
            return jsonify({"success": False, "message": "Goal title is required."}), 400

        try:
            target_amount = float(target_amount_raw)
            if target_amount <= 0:
                return jsonify({"success": False, "message": "Target amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical target amount is required."}), 400

        success = SavingsModel.update(
            goal_id=goal_id,
            user_id=user_id,
            title=title,
            target_amount=target_amount,
            target_date=target_date,
            category_icon=category_icon,
            color_code=color_code,
            notes=notes
        )

        if not success:
            return jsonify({"success": False, "message": "Goal not found or update failed."}), 404

        return jsonify({"success": True, "message": "Savings goal updated successfully!"})

    @staticmethod
    def delete_goal(goal_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        success = SavingsModel.delete(goal_id, user_id)
        if not success:
            return jsonify({"success": False, "message": "Goal not found or delete failed."}), 404

        return jsonify({"success": True, "message": "Savings goal deleted successfully!"})
