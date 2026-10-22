"""
backend/routes/api_routes.py
Flask Blueprint mapping REST API routes to corresponding controllers.
Clean, standard RESTful design.
"""

from flask import Blueprint, jsonify
from backend.controllers.auth_controller import AuthController
from backend.controllers.expense_controller import ExpenseController
from backend.controllers.budget_controller import BudgetController
from backend.controllers.split_controller import SplitController
from backend.models.category_model import CategoryModel

api_bp = Blueprint("api", __name__, url_prefix="/api")

# --- AUTHENTICATION ROUTES ---
@api_bp.route("/auth/register", methods=["POST"])
def register():
    return AuthController.register()

@api_bp.route("/auth/login", methods=["POST"])
def login():
    return AuthController.login()

@api_bp.route("/auth/google", methods=["POST", "GET"])
def google_login():
    return AuthController.google_login()

@api_bp.route("/auth/demo-login", methods=["POST"])
def demo_login():
    return AuthController.demo_login()


@api_bp.route("/auth/logout", methods=["POST"])
def logout():
    return AuthController.logout()

@api_bp.route("/auth/me", methods=["GET"])
def current_user():
    return AuthController.current_user()

# --- CATEGORY ROUTES ---
@api_bp.route("/categories", methods=["GET"])
def get_categories():
    categories = CategoryModel.get_all()
    return jsonify({
        "success": True,
        "categories": [
            {
                "category_id": c["category_id"],
                "category_name": c["category_name"],
                "icon_name": c["icon_name"],
                "color_code": c["color_code"],
                "monthly_limit": float(c["monthly_limit"]),
            }
            for c in categories
        ]
    })

@api_bp.route("/categories/<category_id>/limit", methods=["POST", "PUT"])
def update_category_limit(category_id):
    return BudgetController.update_category_limit(category_id)

# --- EXPENSE & TRANSACTION ROUTES ---
@api_bp.route("/expenses", methods=["GET"])
def list_expenses():
    return ExpenseController.list_expenses()

@api_bp.route("/expenses", methods=["POST"])
def create_expense():
    return ExpenseController.create_expense()

@api_bp.route("/expenses/quick-add", methods=["POST"])
def quick_add_expense():
    return ExpenseController.quick_add_expense()


@api_bp.route("/expenses/<expense_id>", methods=["GET"])
def get_expense(expense_id):
    return ExpenseController.get_expense(expense_id)

@api_bp.route("/expenses/<expense_id>", methods=["PUT", "POST"])
def update_expense(expense_id):
    return ExpenseController.update_expense(expense_id)

@api_bp.route("/expenses/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    return ExpenseController.delete_expense(expense_id)

@api_bp.route("/expenses/export-csv", methods=["GET"])
def export_csv():
    return ExpenseController.export_csv()

# --- DASHBOARD & BUDGET ROUTES ---
@api_bp.route("/dashboard/stats", methods=["GET"])
def dashboard_stats():
    return BudgetController.get_dashboard_stats()

@api_bp.route("/budgets", methods=["GET"])
def get_budgets():
    return BudgetController.get_category_budgets()

@api_bp.route("/budgets/monthly-limit", methods=["POST", "PUT"])
def update_monthly_budget():
    return BudgetController.update_monthly_budget()

# --- BILL SPLITTER ROUTES ---
@api_bp.route("/splits", methods=["GET"])
def list_splits():
    return SplitController.list_splits()

@api_bp.route("/splits", methods=["POST"])
def create_split():
    return SplitController.create_split_bill()

@api_bp.route("/splits/<split_id>/settle", methods=["POST"])
def toggle_settle(split_id):
    return SplitController.toggle_settle(split_id)

# --- FINANCIAL ADVISOR ROUTES ---
@api_bp.route("/advisor/insights", methods=["GET"])
def advisor_insights():
    from backend.controllers.advisor_controller import AdvisorController
    return AdvisorController.get_financial_insights()

@api_bp.route("/advisor/simulate", methods=["POST"])
def advisor_simulate():
    from backend.controllers.advisor_controller import AdvisorController
    return AdvisorController.simulate_purchase()

@api_bp.route("/advisor/smart-audit", methods=["POST"])
def advisor_smart_audit():
    from backend.controllers.advisor_controller import AdvisorController
    return AdvisorController.generate_audit()

# --- RECURRING BILLS ROUTES (MONGODB ATLAS) ---
@api_bp.route("/recurring-bills", methods=["GET"])
def list_recurring_bills():
    from backend.controllers.recurring_controller import RecurringController
    return RecurringController.list_bills()

@api_bp.route("/recurring-bills", methods=["POST"])
def create_recurring_bill():
    from backend.controllers.recurring_controller import RecurringController
    return RecurringController.create_bill()

@api_bp.route("/recurring-bills/<bill_id>", methods=["PUT", "POST"])
def update_recurring_bill(bill_id):
    from backend.controllers.recurring_controller import RecurringController
    return RecurringController.update_bill(bill_id)

@api_bp.route("/recurring-bills/<bill_id>", methods=["DELETE"])
def delete_recurring_bill(bill_id):
    from backend.controllers.recurring_controller import RecurringController
    return RecurringController.delete_bill(bill_id)

@api_bp.route("/recurring-bills/<bill_id>/pay", methods=["POST"])
def pay_recurring_bill(bill_id):
    from backend.controllers.recurring_controller import RecurringController
    return RecurringController.pay_bill(bill_id)

# --- SAVINGS GOALS ROUTES (MONGODB ATLAS) ---
@api_bp.route("/savings-goals", methods=["GET"])
def list_savings_goals():
    from backend.controllers.savings_controller import SavingsController
    return SavingsController.list_goals()

@api_bp.route("/savings-goals", methods=["POST"])
def create_savings_goal():
    from backend.controllers.savings_controller import SavingsController
    return SavingsController.create_goal()

@api_bp.route("/savings-goals/<goal_id>/add-funds", methods=["POST"])
def add_savings_funds(goal_id):
    from backend.controllers.savings_controller import SavingsController
    return SavingsController.add_funds(goal_id)

@api_bp.route("/savings-goals/<goal_id>", methods=["PUT", "POST"])
def update_savings_goal(goal_id):
    from backend.controllers.savings_controller import SavingsController
    return SavingsController.update_goal(goal_id)

@api_bp.route("/savings-goals/<goal_id>", methods=["DELETE"])
def delete_savings_goal(goal_id):
    from backend.controllers.savings_controller import SavingsController
    return SavingsController.delete_goal(goal_id)


