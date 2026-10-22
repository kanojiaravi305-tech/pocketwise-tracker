"""
backend/controllers/split_controller.py
Controller for Roommate / Hostel Bill Splitter (Module C).
Flat equal bill splitting algorithm: Total Bill / N people -> creates pending records.
"""

from datetime import date
from flask import request, jsonify, session
from backend.models.expense_model import ExpenseModel
from backend.models.split_model import SplitModel

class SplitController:
    @staticmethod
    def list_splits():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        status = request.args.get("status", "all").strip().lower()
        if status not in ["pending", "settled"]:
            status = None

        splits_rows = SplitModel.get_user_splits(user_id, status)
        stats = SplitModel.get_split_stats(user_id)

        splits_list = [
            {
                "split_id": r["split_id"],
                "expense_id": r["expense_id"],
                "friend_name": r["friend_name"],
                "amount_owed": float(r["amount_owed"]),
                "is_settled": bool(r["is_settled"]),
                "settled_at": r["settled_at"],
                "expense_title": r["expense_title"],
                "total_bill_amount": float(r["total_bill_amount"]),
                "expense_date": r["expense_date"],
                "payment_mode": r["payment_mode"],
                "category_name": r["category_name"],
                "color_code": r["color_code"],
                "icon_name": r["icon_name"],
            }
            for r in splits_rows
        ]

        return jsonify({
            "success": True,
            "splits": splits_list,
            "stats": stats,
        })

    @staticmethod
    def create_split_bill():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = data.get("title", "").strip()
        amount_raw = data.get("total_amount")
        category_id = data.get("category_id")
        payment_mode = data.get("payment_mode", "UPI").strip()
        expense_date = data.get("expense_date", "").strip() or date.today().isoformat()
        notes = data.get("notes", "").strip()
        
        # Friends can be provided as a comma-separated string or array
        friends_raw = data.get("friends", "")
        if isinstance(friends_raw, str):
            friends_list = [f.strip() for f in friends_raw.split(",") if f.strip()]
        elif isinstance(friends_raw, list):
            friends_list = [str(f).strip() for f in friends_raw if str(f).strip()]
        else:
            friends_list = []

        # Validation
        if not title:
            return jsonify({"success": False, "message": "Bill description or title is required."}), 400

        try:
            total_amount = float(amount_raw)
            if total_amount <= 0:
                return jsonify({"success": False, "message": "Total bill must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical bill amount is required."}), 400

        if not category_id:
            return jsonify({"success": False, "message": "Category is required."}), 400

        if len(friends_list) == 0:
            return jsonify({"success": False, "message": "Please specify at least one contact/member to split with."}), 400

        # Whether to include the current user in the equal split
        # Default: True (User + Friends all share the bill equally)
        include_self = data.get("include_self", True)
        if isinstance(include_self, str):
            include_self = include_self.lower() in ["true", "1", "yes"]

        num_people = len(friends_list) + (1 if include_self else 0)
        split_per_person = round(total_amount / num_people, 2)

        # 1. Create parent expense record in expenses table
        notes_detail = f"Split among {num_people} people (INR {split_per_person:,.2f} each). " + (notes if notes else "")
        expense_id = ExpenseModel.create(
            user_id=user_id,
            category_id=category_id,
            title=title,
            amount=total_amount,
            payment_mode=payment_mode,
            expense_date=expense_date,
            notes=notes_detail,
        )

        # 2. Create pending records for each friend
        friend_splits = [(name, split_per_person) for name in friends_list]
        split_ids = SplitModel.create_splits(expense_id, friend_splits)

        return jsonify({
            "success": True,
            "message": f"Bill split successfully! Created {len(split_ids)} pending records at INR {split_per_person:,.2f} each.",
            "expense_id": expense_id,
            "split_ids": split_ids,
            "share_per_person": split_per_person,
            "total_friends": len(friends_list),
        }), 201

    @staticmethod
    def toggle_settle(split_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or {}
        # Target status: if provided, use it; otherwise toggle
        is_settled = data.get("is_settled", 1)
        try:
            is_settled_int = 1 if int(is_settled) == 1 else 0
        except (ValueError, TypeError):
            is_settled_int = 1

        success = SplitModel.toggle_settle(split_id, user_id, is_settled_int)
        if not success:
            return jsonify({"success": False, "message": "Split record not found or unauthorized."}), 404

        status_text = "Settled" if is_settled_int == 1 else "Marked as Pending"
        return jsonify({
            "success": True,
            "message": f"Payment successfully {status_text}!",
            "is_settled": bool(is_settled_int),
        })
