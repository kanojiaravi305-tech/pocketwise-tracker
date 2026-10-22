"""
backend/app.py
Main Flask application entry point.
Configures 3-Tier MVC architecture, session security, template routing, and static assets.
"""

import os
from functools import wraps
from flask import Flask, render_template, redirect, url_for, session
from backend.config.db import close_db
from backend.routes.api_routes import api_bp

# Resolve paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE_DIR = os.path.join(BASE_DIR, "frontend", "views")
STATIC_DIR = os.path.join(BASE_DIR, "frontend")

def create_app():
    app = Flask(
        __name__,
        template_folder=TEMPLATE_DIR,
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )

    # Secure session secret key
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "student_expense_tracker_fyp_2026_super_secret_key")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # Register database teardown
    app.teardown_appcontext(close_db)

    # Register API blueprint
    app.register_blueprint(api_bp)

    @app.context_processor
    def inject_db_info():
        from backend.config.mongodb import DB_ENGINE, is_atlas_connected
        if DB_ENGINE == "mongodb":
            db_label = "MongoDB Atlas (Cloud)" if is_atlas_connected() else "MongoDB (Local)"
        else:
            db_label = "SQLite RDBMS"
        return {"active_db_label": db_label}

    # Decorator to protect HTML routes requiring login
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login_page"))
            return f(*args, **kwargs)
        return decorated_function

    # --- HTML PAGE VIEW ROUTES (5 Core Pages) ---

    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("dashboard_page"))
        return redirect(url_for("login_page"))

    @app.route("/login")
    def login_page():
        if "user_id" in session:
            return redirect(url_for("dashboard_page"))
        return render_template("login.html")

    @app.route("/register")
    def register_page():
        if "user_id" in session:
            return redirect(url_for("dashboard_page"))
        return render_template("register.html")

    @app.route("/dashboard")
    @login_required
    def dashboard_page():
        return render_template(
            "dashboard.html",
            active_page="dashboard",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/transactions")
    @login_required
    def transactions_page():
        return render_template(
            "transactions.html",
            active_page="transactions",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/budgets")
    @login_required
    def budgets_page():
        return render_template(
            "budgets.html",
            active_page="budgets",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/recurring")
    @login_required
    def recurring_page():
        return render_template(
            "recurring.html",
            active_page="recurring",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/savings")
    @login_required
    def savings_page():
        return render_template(
            "savings.html",
            active_page="savings",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/split")
    @login_required
    def split_page():
        return render_template(
            "split.html",
            active_page="split",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/advisor")
    @login_required
    def advisor_page():
        return render_template(
            "advisor.html",
            active_page="advisor",
            user_name=session.get("user_name", "Student"),
            user_email=session.get("user_email", ""),
        )

    @app.route("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login_page"))

    return app

# Global Flask application instance for external WSGI servers (e.g., gunicorn backend.app:app)
app = create_app()

if __name__ == "__main__":
    print("Starting Student Expense Tracker on http://127.0.0.1:5000 ...")
    app.run(debug=True, host="127.0.0.1", port=5000)
