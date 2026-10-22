"""
backend/controllers/recurring_controller.py
Controller handling Recurring Bills CRUD and "Mark Paid" expense logging.
"""

from flask import request, jsonify, session
from backend.models.recurring_model import RecurringModel
from backend.models.category_model import CategoryModel

class RecurringController:
    @staticmethod
    def list_bills():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        bills = RecurringModel.get_all(user_id)
        
        # Calculate summary metrics
        total_monthly_amount = sum(b["amount"] for b in bills)
        paid_bills = [b for b in bills if b["is_paid"]]
        pending_bills = [b for b in bills if not b["is_paid"]]
        total_paid_amount = sum(b["amount"] for b in paid_bills)
        total_pending_amount = sum(b["amount"] for b in pending_bills)

        return jsonify({
            "success": True,
            "bills": bills,
            "metrics": {
                "total_bills": len(bills),
                "total_monthly_amount": total_monthly_amount,
                "paid_count": len(paid_bills),
                "paid_amount": total_paid_amount,
                "pending_count": len(pending_bills),
                "pending_amount": total_pending_amount,
            }
        })

    @staticmethod
    def create_bill():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = (data.get("title") or "").strip()
        amount_raw = data.get("amount")
        category_id = data.get("category_id")
        due_day = data.get("due_day", 1)
        frequency = data.get("frequency", "Monthly")
        payment_mode = data.get("payment_mode", "UPI")
        notes = (data.get("notes") or "").strip()

        if not title:
            return jsonify({"success": False, "message": "Bill title is required."}), 400

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical amount is required."}), 400

        try:
            due_day_int = int(due_day)
            if due_day_int < 1 or due_day_int > 31:
                return jsonify({"success": False, "message": "Due day must be between 1 and 31."}), 400
        except (ValueError, TypeError):
            due_day_int = 1

        bill_id = RecurringModel.create(
            user_id=user_id,
            title=title,
            amount=amount,
            category_id=category_id,
            due_day=due_day_int,
            frequency=frequency,
            payment_mode=payment_mode,
            notes=notes
        )

        return jsonify({
            "success": True,
            "message": f"Recurring bill '{title}' created successfully!",
            "bill_id": str(bill_id)
        }), 201

    @staticmethod
    def update_bill(bill_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = (data.get("title") or "").strip()
        amount_raw = data.get("amount")
        category_id = data.get("category_id")
        due_day = data.get("due_day", 1)
        frequency = data.get("frequency", "Monthly")
        payment_mode = data.get("payment_mode", "UPI")
        notes = (data.get("notes") or "").strip()

        if not title:
            return jsonify({"success": False, "message": "Bill title is required."}), 400

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical amount is required."}), 400

        success = RecurringModel.update(
            bill_id=bill_id,
            user_id=user_id,
            title=title,
            amount=amount,
            category_id=category_id,
            due_day=int(due_day),
            frequency=frequency,
            payment_mode=payment_mode,
            notes=notes
        )

        if not success:
            return jsonify({"success": False, "message": "Bill not found or update failed."}), 404

        return jsonify({"success": True, "message": "Recurring bill updated successfully!"})

    @staticmethod
    def delete_bill(bill_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        success = RecurringModel.delete(bill_id, user_id)
        if not success:
            return jsonify({"success": False, "message": "Bill not found or delete failed."}), 404

        return jsonify({"success": True, "message": "Recurring bill deleted successfully!"})

    @staticmethod
    def pay_bill(bill_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        expense_id, err = RecurringModel.mark_paid(bill_id, user_id)
        if err:
            return jsonify({"success": False, "message": err}), 400

        return jsonify({
            "success": True,
            "message": "Bill marked as paid! Expense logged in MongoDB expenses collection.",
            "expense_id": str(expense_id)
        })
