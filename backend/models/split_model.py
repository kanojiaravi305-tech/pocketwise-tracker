"""
backend/models/split_model.py
Data Access Object (DAO) for split_records table.
Supports dual-engine (SQLite & MongoDB Atlas).
"""

from backend.config.mongodb import DB_ENGINE
from backend.config.db import query_db, execute_db

class SplitModel:
    @staticmethod
    def create_splits(expense_id, friend_splits):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSplitModel
            return MongoSplitModel.create_splits(expense_id, friend_splits)
        db_records = []
        for name, amount in friend_splits:
            last_id, _ = execute_db(
                """
                INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
                VALUES (?, ?, ?, 0, NULL);
                """,
                (expense_id, name.strip(), float(amount)),
            )
            db_records.append(last_id)
        return db_records

    @staticmethod
    def get_user_splits(user_id, status=None):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSplitModel
            return MongoSplitModel.get_user_splits(user_id, status)
        sql = """
            SELECT 
                s.split_id,
                s.expense_id,
                s.friend_name,
                s.amount_owed,
                s.is_settled,
                s.settled_at,
                s.created_at AS split_created_at,
                e.title AS expense_title,
                e.amount AS total_bill_amount,
                e.expense_date,
                e.payment_mode,
                c.category_name,
                c.color_code,
                c.icon_name
            FROM split_records s
            JOIN expenses e ON s.expense_id = e.expense_id
            JOIN categories c ON e.category_id = c.category_id
            WHERE e.user_id = ?
        """
        params = [user_id]

        if status == "pending":
            sql += " AND s.is_settled = 0"
        elif status == "settled":
            sql += " AND s.is_settled = 1"

        sql += " ORDER BY s.is_settled ASC, s.created_at DESC;"
        return query_db(sql, params)

    @staticmethod
    def toggle_settle(split_id, user_id, is_settled):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSplitModel
            return MongoSplitModel.toggle_settle(split_id, user_id, is_settled)
        sql = """
            UPDATE split_records 
            SET is_settled = ?, settled_at = CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END
            WHERE split_id = ? 
              AND expense_id IN (SELECT expense_id FROM expenses WHERE user_id = ?);
        """
        _, rowcount = execute_db(sql, (int(is_settled), int(is_settled), split_id, user_id))
        return rowcount > 0

    @staticmethod
    def get_split_stats(user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoSplitModel
            return MongoSplitModel.get_split_stats(user_id)
        sql = """
            SELECT 
                COALESCE(SUM(s.amount_owed), 0.0) AS total_lent,
                COALESCE(SUM(CASE WHEN s.is_settled = 1 THEN s.amount_owed ELSE 0 END), 0.0) AS total_recovered,
                COALESCE(SUM(CASE WHEN s.is_settled = 0 THEN s.amount_owed ELSE 0 END), 0.0) AS total_pending,
                COUNT(s.split_id) AS total_records,
                SUM(CASE WHEN s.is_settled = 0 THEN 1 ELSE 0 END) AS pending_count
            FROM split_records s
            JOIN expenses e ON s.expense_id = e.expense_id
            WHERE e.user_id = ?;
        """
        row = query_db(sql, (user_id,), one=True)
        return {
            "total_lent": float(row["total_lent"]) if row else 0.0,
            "total_recovered": float(row["total_recovered"]) if row else 0.0,
            "total_pending": float(row["total_pending"]) if row else 0.0,
            "total_records": int(row["total_records"]) if row else 0,
            "pending_count": int(row["pending_count"]) if row and row["pending_count"] is not None else 0,
        }
