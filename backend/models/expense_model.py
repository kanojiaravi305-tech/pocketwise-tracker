"""
backend/models/expense_model.py
Data Access Object (DAO) for expenses table.
Supports dual-engine (SQLite & MongoDB Atlas).
"""

from backend.config.mongodb import DB_ENGINE
from backend.config.db import query_db, execute_db

class ExpenseModel:
    @staticmethod
    def get_filtered(user_id, month=None, category_id=None, payment_mode=None, search=None, limit=None, offset=None):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.get_filtered(user_id, month, category_id, payment_mode, search, limit, offset)
        sql = """
            SELECT 
                e.expense_id,
                e.user_id,
                e.category_id,
                c.category_name,
                c.icon_name,
                c.color_code,
                e.title,
                e.amount,
                e.payment_mode,
                e.expense_date,
                e.notes,
                e.created_at
            FROM expenses e
            JOIN categories c ON e.category_id = c.category_id
            WHERE e.user_id = ?
        """
        params = [user_id]

        if month:
            sql += " AND strftime('%Y-%m', e.expense_date) = ?"
            params.append(month)

        if category_id:
            sql += " AND e.category_id = ?"
            params.append(int(category_id))

        if payment_mode:
            sql += " AND e.payment_mode = ?"
            params.append(payment_mode)

        if search:
            sql += " AND (e.title LIKE ? OR e.notes LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        sql += " ORDER BY e.expense_date DESC, e.expense_id DESC"

        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
            if offset is not None:
                sql += " OFFSET ?"
                params.append(int(offset))

        return query_db(sql, params)

    @staticmethod
    def count_filtered(user_id, month=None, category_id=None, payment_mode=None, search=None):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.count_filtered(user_id, month, category_id, payment_mode, search)
        sql = "SELECT COUNT(*) as total FROM expenses e WHERE e.user_id = ?"
        params = [user_id]

        if month:
            sql += " AND strftime('%Y-%m', e.expense_date) = ?"
            params.append(month)

        if category_id:
            sql += " AND e.category_id = ?"
            params.append(int(category_id))

        if payment_mode:
            sql += " AND e.payment_mode = ?"
            params.append(payment_mode)

        if search:
            sql += " AND (e.title LIKE ? OR e.notes LIKE ?)"
            term = f"%{search.strip()}%"
            params.extend([term, term])

        row = query_db(sql, params, one=True)
        return row["total"] if row else 0

    @staticmethod
    def get_by_id(expense_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.get_by_id(expense_id, user_id)
        sql = """
            SELECT 
                e.expense_id,
                e.user_id,
                e.category_id,
                c.category_name,
                c.icon_name,
                c.color_code,
                e.title,
                e.amount,
                e.payment_mode,
                e.expense_date,
                e.notes,
                e.created_at
            FROM expenses e
            JOIN categories c ON e.category_id = c.category_id
            WHERE e.expense_id = ? AND e.user_id = ?;
        """
        return query_db(sql, (expense_id, user_id), one=True)

    @staticmethod
    def create(user_id, category_id, title, amount, payment_mode, expense_date, notes=""):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.create(user_id, category_id, title, amount, payment_mode, expense_date, notes)
        last_id, _ = execute_db(
            """
            INSERT INTO expenses (user_id, category_id, title, amount, payment_mode, expense_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (user_id, int(category_id), title.strip(), float(amount), payment_mode, expense_date, notes.strip() if notes else ""),
        )
        return last_id

    @staticmethod
    def update(expense_id, user_id, category_id, title, amount, payment_mode, expense_date, notes=""):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.update(expense_id, user_id, category_id, title, amount, payment_mode, expense_date, notes)
        _, rowcount = execute_db(
            """
            UPDATE expenses 
            SET category_id = ?, title = ?, amount = ?, payment_mode = ?, expense_date = ?, notes = ?
            WHERE expense_id = ? AND user_id = ?;
            """,
            (int(category_id), title.strip(), float(amount), payment_mode, expense_date, notes.strip() if notes else "", expense_id, user_id),
        )
        return rowcount > 0

    @staticmethod
    def delete(expense_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.delete(expense_id, user_id)
        _, rowcount = execute_db(
            "DELETE FROM expenses WHERE expense_id = ? AND user_id = ?;",
            (expense_id, user_id),
        )
        return rowcount > 0

    @staticmethod
    def get_monthly_total(user_id, year_month):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.get_monthly_total(user_id, year_month)
        sql = """
            SELECT COALESCE(SUM(amount), 0.0) AS total_spent 
            FROM expenses 
            WHERE user_id = ? AND strftime('%Y-%m', expense_date) = ?;
        """
        row = query_db(sql, (user_id, year_month), one=True)
        return float(row["total_spent"]) if row else 0.0

    @staticmethod
    def get_category_breakdown(user_id, year_month):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.get_category_breakdown(user_id, year_month)
        sql = """
            SELECT 
                c.category_name,
                c.color_code,
                c.icon_name,
                SUM(e.amount) AS total_amount
            FROM expenses e
            JOIN categories c ON e.category_id = c.category_id
            WHERE e.user_id = ? AND strftime('%Y-%m', e.expense_date) = ?
            GROUP BY c.category_id, c.category_name, c.color_code, c.icon_name
            HAVING total_amount > 0
            ORDER BY total_amount DESC;
        """
        return query_db(sql, (user_id, year_month))

    @staticmethod
    def get_six_months_trend(user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.get_six_months_trend(user_id)
        sql = """
            SELECT 
                strftime('%Y-%m', expense_date) AS month_key,
                SUM(amount) AS total_amount
            FROM expenses
            WHERE user_id = ? 
              AND expense_date >= date('now', 'start of month', '-5 months')
            GROUP BY month_key
            ORDER BY month_key ASC;
        """
        return query_db(sql, (user_id,))

    @staticmethod
    def get_category_monthly_averages(user_id, exclude_month=None):
        """
        Calculates historical average monthly spending per category (excluding specified current month).
        Used by the Anomaly Detection engine to establish baseline category norms.
        """
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoExpenseModel
            return MongoExpenseModel.get_category_monthly_averages(user_id, exclude_month)
        sql = """
            SELECT 
                c.category_id,
                c.category_name,
                AVG(monthly_sub.month_total) AS avg_monthly_spent
            FROM (
                SELECT 
                    category_id,
                    strftime('%Y-%m', expense_date) AS mkey,
                    SUM(amount) AS month_total
                FROM expenses
                WHERE user_id = ?
        """
        params = [user_id]
        if exclude_month:
            sql += " AND strftime('%Y-%m', expense_date) != ?"
            params.append(exclude_month)
        sql += """
                GROUP BY category_id, mkey
            ) monthly_sub
            JOIN categories c ON monthly_sub.category_id = c.category_id
            GROUP BY c.category_id, c.category_name;
        """
        return query_db(sql, params)

