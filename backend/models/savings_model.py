"""
backend/models/savings_model.py
Repository interface for Savings Goals Module.
Supports dual-engine: MongoDB Atlas (NoSQL) & SQLite fallback.
"""

from backend.config.mongodb import DB_ENGINE
from backend.config.db import query_db, execute_db
import datetime

class SavingsModel:
    @staticmethod
    def _init_sqlite_table():
        execute_db("""
            CREATE TABLE IF NOT EXISTS savings_goals (
                goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL NOT NULL DEFAULT 0.0,
                target_date DATE NULL,
                category_icon TEXT NOT NULL DEFAULT 'bi-piggy-bank',
                color_code TEXT NOT NULL DEFAULT '#059669',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    @staticmethod
    def get_all(user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSavingsModel
            return MongoSavingsModel.get_all(user_id)

        SavingsModel._init_sqlite_table()
        count_row = query_db("SELECT COUNT(*) as cnt FROM savings_goals WHERE user_id = ?", (user_id,), one=True)
        if count_row and count_row["cnt"] == 0:
            SavingsModel._seed_sqlite_defaults(user_id)

        rows = query_db("""
            SELECT * FROM savings_goals
            WHERE user_id = ?
            ORDER BY target_date ASC
        """, (user_id,))

        today = datetime.date.today()
        results = []
        for r in rows:
            target = float(r["target_amount"])
            current = float(r["current_amount"])
            pct = min(100.0, round((current / target * 100), 1)) if target > 0 else 0.0
            remaining = max(0.0, target - current)
            is_completed = current >= target

            target_date_str = r["target_date"] or ""
            days_left = None
            if target_date_str:
                try:
                    td = datetime.date.fromisoformat(target_date_str)
                    days_left = (td - today).days
                except Exception:
                    pass

            results.append({
                "goal_id": r["goal_id"],
                "title": r["title"],
                "target_amount": target,
                "current_amount": current,
                "progress_percent": pct,
                "remaining_amount": remaining,
                "is_completed": is_completed,
                "target_date": target_date_str,
                "days_left": days_left,
                "category_icon": r["category_icon"],
                "color_code": r["color_code"],
                "notes": r["notes"] or "",
            })
        return results

    @staticmethod
    def _seed_sqlite_defaults(user_id):
        defaults = [
            (user_id, "Emergency Fund (6 Months)", 100000.0, 65000.0, "2026-12-31", "bi-shield-shaded", "#059669", "Safety reserve"),
            (user_id, "MacBook M-Series Upgrade", 85000.0, 42500.0, "2026-11-30", "bi-laptop", "#0284c7", "Workstation upgrade"),
            (user_id, "Annual Vacation & Travel", 30000.0, 18500.0, "2026-12-15", "bi-airplane", "#7c3aed", "Holiday travel with friends"),
            (user_id, "Certifications & Upskilling", 15000.0, 12000.0, "2026-11-15", "bi-mortarboard", "#d97706", "Professional certifications"),
        ]
        for d in defaults:
            execute_db("""
                INSERT INTO savings_goals (user_id, title, target_amount, current_amount, target_date, category_icon, color_code, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, d)

    @staticmethod
    def get_by_id(goal_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSavingsModel
            return MongoSavingsModel.get_by_id(goal_id, user_id)

        SavingsModel._init_sqlite_table()
        row = query_db("SELECT * FROM savings_goals WHERE goal_id = ? AND user_id = ?", (goal_id, user_id), one=True)
        if not row:
            return None
        r = dict(row)
        target = float(r["target_amount"])
        current = float(r["current_amount"])
        r["progress_percent"] = min(100.0, round((current / target * 100), 1)) if target > 0 else 0.0
        r["remaining_amount"] = max(0.0, target - current)
        return r

    @staticmethod
    def create(user_id, title, target_amount, current_amount=0.0, target_date="", category_icon="bi-piggy-bank", color_code="#059669", notes=""):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSavingsModel
            return MongoSavingsModel.create(user_id, title, target_amount, current_amount, target_date, category_icon, color_code, notes)

        SavingsModel._init_sqlite_table()
        last_id, _ = execute_db("""
            INSERT INTO savings_goals (user_id, title, target_amount, current_amount, target_date, category_icon, color_code, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (user_id, title.strip(), float(target_amount), float(current_amount or 0.0), target_date, category_icon, color_code, notes.strip() if notes else ""))
        return last_id

    @staticmethod
    def add_funds(goal_id, user_id, amount, note="Manual deposit"):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSavingsModel
            return MongoSavingsModel.add_funds(goal_id, user_id, amount, note)

        SavingsModel._init_sqlite_table()
        amt = float(amount)
        if amt <= 0:
            return False, "Amount must be greater than zero."
        _, rowcount = execute_db("""
            UPDATE savings_goals
            SET current_amount = current_amount + ?
            WHERE goal_id = ? AND user_id = ?;
        """, (amt, goal_id, user_id))
        return rowcount > 0, None

    @staticmethod
    def update(goal_id, user_id, title, target_amount, target_date="", category_icon="bi-piggy-bank", color_code="#059669", notes=""):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSavingsModel
            return MongoSavingsModel.update(goal_id, user_id, title, target_amount, target_date, category_icon, color_code, notes)

        SavingsModel._init_sqlite_table()
        _, rowcount = execute_db("""
            UPDATE savings_goals
            SET title = ?, target_amount = ?, target_date = ?, category_icon = ?, color_code = ?, notes = ?
            WHERE goal_id = ? AND user_id = ?;
        """, (title.strip(), float(target_amount), target_date, category_icon, color_code, notes.strip() if notes else "", goal_id, user_id))
        return rowcount > 0

    @staticmethod
    def delete(goal_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSavingsModel
            return MongoSavingsModel.delete(goal_id, user_id)

        SavingsModel._init_sqlite_table()
        _, rowcount = execute_db("DELETE FROM savings_goals WHERE goal_id = ? AND user_id = ?;", (goal_id, user_id))
        return rowcount > 0
