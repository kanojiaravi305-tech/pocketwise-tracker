"""
backend/controllers/expense_controller.py
Controller handling Transaction CRUD, multi-criteria filtering, pagination, and CSV Export.
"""

import io
import csv
from datetime import date
from flask import request, jsonify, session, Response
from backend.models.expense_model import ExpenseModel
from backend.models.category_model import CategoryModel

class ExpenseController:
    @staticmethod
    def list_expenses():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        # Query filters
        month = request.args.get("month", "").strip() or None
        category_id = request.args.get("category_id", "").strip() or None
        payment_mode = request.args.get("payment_mode", "").strip() or None
        search = request.args.get("search", "").strip() or None
        
        # Pagination
        try:
            page = max(1, int(request.args.get("page", 1)))
            page_size = max(1, min(100, int(request.args.get("page_size", 10))))
        except ValueError:
            page = 1
            page_size = 10

        offset = (page - 1) * page_size
        total_count = ExpenseModel.count_filtered(user_id, month, category_id, payment_mode, search)
        expenses_rows = ExpenseModel.get_filtered(user_id, month, category_id, payment_mode, search, limit=page_size, offset=offset)

        expenses_list = [
            {
                "expense_id": row["expense_id"],
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "icon_name": row["icon_name"],
                "color_code": row["color_code"],
                "title": row["title"],
                "amount": float(row["amount"]),
                "payment_mode": row["payment_mode"],
                "expense_date": row["expense_date"],
                "notes": row["notes"] or "",
            }
            for row in expenses_rows
        ]

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 1

        return jsonify({
            "success": True,
            "expenses": expenses_list,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_records": total_count,
                "total_pages": total_pages,
            }
        })

    @staticmethod
    def get_expense(expense_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        expense = ExpenseModel.get_by_id(expense_id, user_id)
        if not expense:
            return jsonify({"success": False, "message": "Expense not found"}), 404

        return jsonify({
            "success": True,
            "expense": {
                "expense_id": expense["expense_id"],
                "category_id": expense["category_id"],
                "category_name": expense["category_name"],
                "title": expense["title"],
                "amount": float(expense["amount"]),
                "payment_mode": expense["payment_mode"],
                "expense_date": expense["expense_date"],
                "notes": expense["notes"] or "",
            }
        })

    @staticmethod
    def create_expense():
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = data.get("title", "").strip()
        amount_raw = data.get("amount")
        category_id = data.get("category_id")
        payment_mode = data.get("payment_mode", "UPI").strip()
        expense_date = data.get("expense_date", "").strip() or date.today().isoformat()
        notes = data.get("notes", "").strip()

        if not title:
            return jsonify({"success": False, "message": "Title is required."}), 400

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical amount is required."}), 400

        if not category_id:
            return jsonify({"success": False, "message": "Category is required."}), 400

        if payment_mode not in ["UPI", "Cash", "Card", "Net Banking"]:
            return jsonify({"success": False, "message": "Invalid payment mode. Choose UPI, Cash, Card, or Net Banking."}), 400

        expense_id = ExpenseModel.create(user_id, category_id, title, amount, payment_mode, expense_date, notes)

        return jsonify({
            "success": True,
            "message": "Expense added successfully!",
            "expense_id": expense_id
        }), 201

    @staticmethod
    def update_expense(expense_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        title = data.get("title", "").strip()
        amount_raw = data.get("amount")
        category_id = data.get("category_id")
        payment_mode = data.get("payment_mode", "UPI").strip()
        expense_date = data.get("expense_date", "").strip()
        notes = data.get("notes", "").strip()

        if not title:
            return jsonify({"success": False, "message": "Title is required."}), 400

        try:
            amount = float(amount_raw)
            if amount <= 0:
                return jsonify({"success": False, "message": "Amount must be greater than zero."}), 400
        except (ValueError, TypeError):
            return jsonify({"success": False, "message": "Valid numerical amount is required."}), 400

        if payment_mode not in ["UPI", "Cash", "Card", "Net Banking"]:
            return jsonify({"success": False, "message": "Invalid payment mode."}), 400

        success = ExpenseModel.update(expense_id, user_id, category_id, title, amount, payment_mode, expense_date, notes)
        if not success:
            return jsonify({"success": False, "message": "Expense not found or update failed."}), 404

        return jsonify({"success": True, "message": "Expense updated successfully!"})

    @staticmethod
    def delete_expense(expense_id):
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        success = ExpenseModel.delete(expense_id, user_id)
        if not success:
            return jsonify({"success": False, "message": "Expense not found or delete failed."}), 404

        return jsonify({"success": True, "message": "Expense deleted successfully!"})

    @staticmethod
    def export_csv():
        """
        Viva Standout Feature:
        Generates standard CSV file from filtered expenses.
        Professors love automated report & CSV export features!
        """
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        month = request.args.get("month", "").strip() or None
        category_id = request.args.get("category_id", "").strip() or None
        payment_mode = request.args.get("payment_mode", "").strip() or None
        search = request.args.get("search", "").strip() or None

        # Fetch all matching without pagination
        rows = ExpenseModel.get_filtered(user_id, month, category_id, payment_mode, search)

        output = io.StringIO()
        writer = csv.writer(output)
        
        # Standard CSV Headers
        writer.writerow(["Expense ID", "Date", "Title", "Category", "Payment Mode", "Amount (INR)", "Notes"])

        for r in rows:
            writer.writerow([
                r["expense_id"],
                r["expense_date"],
                r["title"],
                r["category_name"],
                r["payment_mode"],
                f"{float(r['amount']):.2f}",
                r["notes"] or ""
            ])

        output.seek(0)
        filename = f"expense_statement_{month or 'all'}.csv"
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    @staticmethod
    def quick_add_expense():
        """
        Natural Language Quick-Add endpoint.
        Extracts amount, payment mode, category, and merchant title from a free-text sentence
        and immediately records the expense in the database.
        """
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 401

        data = request.get_json() or request.form
        query_text = (data.get("query") or data.get("text") or "").strip()

        if not query_text:
            return jsonify({"success": False, "message": "Please enter an expense sentence (e.g. 'Spent 650 on Swiggy via UPI')."}), 400

        # Retrieve user's available categories for matching
        categories = CategoryModel.get_all()
        categories_list = [
            {"category_id": c["category_id"], "category_name": c["category_name"]}
            for c in categories
        ]

        from backend.services.nlp_parser import parse_natural_language_expense
        parsed = parse_natural_language_expense(query_text, categories_list)

        if not parsed.get("success"):
            return jsonify({
                "success": False,
                "message": parsed.get("message", "Could not parse expense sentence.")
            }), 400

        # Insert expense into database
        expense_id = ExpenseModel.create(
            user_id=user_id,
            category_id=parsed["category_id"],
            title=parsed["title"],
            amount=parsed["amount"],
            payment_mode=parsed["payment_mode"],
            expense_date=parsed["expense_date"],
            notes=parsed["notes"]
        )

        return jsonify({
            "success": True,
            "message": f"Logged ₹{parsed['amount']:,.2f} for '{parsed['title']}' under {parsed['category_name']} ({parsed['payment_mode']})",
            "expense_id": expense_id,
            "parsed": {
                "title": parsed["title"],
                "amount": parsed["amount"],
                "category_id": parsed["category_id"],
                "category_name": parsed["category_name"],
                "payment_mode": parsed["payment_mode"],
                "expense_date": parsed["expense_date"],
                "notes": parsed["notes"],
            }
        }), 201

