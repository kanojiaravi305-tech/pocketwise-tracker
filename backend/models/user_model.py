"""
backend/models/user_model.py
Data Access Object (DAO) for users table.
Uses parameterized queries to safeguard against SQL Injection.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from backend.config.mongodb import DB_ENGINE
from backend.config.db import query_db, execute_db

class UserModel:
    @staticmethod
    def get_by_id(user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoUserModel
            return MongoUserModel.get_by_id(user_id)
        return query_db(
            "SELECT user_id, full_name, email, monthly_budget_limit, created_at FROM users WHERE user_id = ?;",
            (user_id,),
            one=True,
        )

    @staticmethod
    def get_by_email(email):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoUserModel
            return MongoUserModel.get_by_email(email)
        return query_db(
            "SELECT user_id, full_name, email, password_hash, monthly_budget_limit FROM users WHERE email = ?;",
            (email.strip().lower(),),
            one=True,
        )

    @staticmethod
    def create(full_name, email, password, monthly_budget_limit=6500.0):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoUserModel
            return MongoUserModel.create(full_name, email, password, monthly_budget_limit)
        hashed = generate_password_hash(password)
        last_id, _ = execute_db(
            """
            INSERT INTO users (full_name, email, password_hash, monthly_budget_limit)
            VALUES (?, ?, ?, ?);
            """,
            (full_name.strip(), email.strip().lower(), hashed, float(monthly_budget_limit)),
        )
        return last_id

    @staticmethod
    def update_budget_limit(user_id, new_limit):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoUserModel
            return MongoUserModel.update_budget_limit(user_id, new_limit)
        _, rowcount = execute_db(
            "UPDATE users SET monthly_budget_limit = ? WHERE user_id = ?;",
            (float(new_limit), user_id),
        )
        return rowcount > 0

    @staticmethod
    def verify_password(stored_hash, candidate_password):
        return check_password_hash(stored_hash, candidate_password)
