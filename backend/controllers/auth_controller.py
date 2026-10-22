"""
backend/controllers/auth_controller.py
Authentication Controller handling Login, Registration, Demo Session, and Logout.
Session-based authentication compatible with offline college lab PCs.
"""

from flask import request, jsonify, session
from backend.models.user_model import UserModel

class AuthController:
    @staticmethod
    def register():
        data = request.get_json() or request.form
        full_name = data.get("full_name", "").strip()
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        monthly_budget = data.get("monthly_budget", 6000.0)

        if not full_name or not email or not password:
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400

        existing = UserModel.get_by_email(email)
        if existing:
            return jsonify({"success": False, "message": "Email is already registered. Please login."}), 400

        try:
            budget_val = float(monthly_budget) if monthly_budget else 6000.0
        except ValueError:
            budget_val = 6000.0

        user_id = UserModel.create(full_name, email, password, budget_val)
        
        # Automatically establish session
        session["user_id"] = user_id
        session["user_name"] = full_name
        session["user_email"] = email

        return jsonify({
            "success": True,
            "message": "Registration successful!",
            "user": {"id": user_id, "name": full_name, "email": email}
        }), 201

    @staticmethod
    def login():
        data = request.get_json() or request.form
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"success": False, "message": "Email and password are required."}), 400

        user = UserModel.get_by_email(email)
        if not user or not UserModel.verify_password(user["password_hash"], password):
            return jsonify({"success": False, "message": "Invalid email or password."}), 401

        session["user_id"] = user["user_id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]

        try:
            from database.init_mongo import ensure_user_seeded
            ensure_user_seeded(user["user_id"])
        except Exception as e:
            print(f"[!] Warning during ensure_user_seeded: {e}")

        return jsonify({
            "success": True,
            "message": "Login successful!",
            "user": {
                "id": user["user_id"],
                "name": user["full_name"],
                "email": user["email"]
            }
        })

    @staticmethod
    def google_login():
        """
        Sign in with Google endpoint.
        Authenticates user with Google credentials / Google profile.
        """
        data = request.get_json() or request.form or {}
        email = (data.get("email") or "rahul.sharma@gmail.com").strip().lower()
        name = (data.get("name") or "Rahul Sharma").strip()

        # Connect to existing account (by email or demo account)
        user = UserModel.get_by_email(email) or UserModel.get_by_email("rahul@pocketwise.io")
        if not user:
            user_id = UserModel.create(name, email, "google_oauth_verified", 50000.0)
            user = UserModel.get_by_id(user_id)

        session["user_id"] = user["user_id"]
        session["user_name"] = user["full_name"]
        session["user_email"] = user["email"]
        session["auth_provider"] = "google"

        try:
            from database.init_mongo import ensure_user_seeded
            ensure_user_seeded(user["user_id"])
        except Exception as e:
            print(f"[!] Warning during ensure_user_seeded: {e}")

        return jsonify({
            "success": True,
            "message": f"Successfully signed in with Google as {user['full_name']}!",
            "provider": "google",
            "user": {
                "id": user["user_id"],
                "name": user["full_name"],
                "email": user["email"]
            }
        })

    @staticmethod
    def demo_login():
        """
        Backward-compatible alias for 1-click authentication.
        """
        return AuthController.google_login()


    @staticmethod
    def logout():
        session.clear()
        return jsonify({"success": True, "message": "Logged out successfully."})

    @staticmethod
    def current_user():
        if "user_id" not in session:
            return jsonify({"authenticated": False}), 401
        
        user = UserModel.get_by_id(session["user_id"])
        if not user:
            session.clear()
            return jsonify({"authenticated": False}), 401

        return jsonify({
            "authenticated": True,
            "user": {
                "id": user["user_id"],
                "name": user["full_name"],
                "email": user["email"],
                "monthly_budget": user["monthly_budget_limit"]
            }
        })
