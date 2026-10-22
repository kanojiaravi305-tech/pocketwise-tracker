"""
backend/models/recurring_model.py
Repository interface for Recurring Bills Module.
Supports dual-engine: MongoDB Atlas (NoSQL) & SQLite fallback.
"""

from backend.config.mongodb import DB_ENGINE
from backend.config.db import query_db, execute_db
import datetime

class RecurringModel:
    @staticmethod
    def _init_sqlite_table():
        execute_db("""
            CREATE TABLE IF NOT EXISTS recurring_bills (
                bill_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                amount REAL NOT NULL,
                category_id INTEGER NOT NULL,
                due_day INTEGER NOT NULL DEFAULT 1,
                frequency TEXT NOT NULL DEFAULT 'Monthly',
                payment_mode TEXT NOT NULL DEFAULT 'UPI',
                notes TEXT,
                last_paid_date DATE NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    @staticmethod
    def get_all(user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoRecurringModel
            return MongoRecurringModel.get_all(user_id)

        RecurringModel._init_sqlite_table()
        # Seed default for SQLite if empty
        count_row = query_db("SELECT COUNT(*) as cnt FROM recurring_bills WHERE user_id = ?", (user_id,), one=True)
        if count_row and count_row["cnt"] == 0:
            RecurringModel._seed_sqlite_defaults(user_id)

        today = datetime.date.today()
        current_ym = today.strftime("%Y-%m")
        current_day = today.day

        rows = query_db("""
            SELECT r.*, c.category_name, c.icon_name, c.color_code
            FROM recurring_bills r
            LEFT JOIN categories c ON r.category_id = c.category_id
            WHERE r.user_id = ?
            ORDER BY r.due_day ASC
        """, (user_id,))

        results = []
        for r in rows:
            last_paid = r["last_paid_date"]
            is_paid = bool(last_paid and str(last_paid).startswith(current_ym))
            due_day = int(r["due_day"])

            if is_paid:
                status = "Paid"
                status_color = "success"
                status_badge = "Paid This Month"
            elif current_day > due_day:
                status = "Overdue"
                status_color = "danger"
                status_badge = f"Overdue (Was due {due_day}th)"
            elif current_day == due_day:
                status = "Due Today"
                status_color = "warning"
                status_badge = "Due Today"
            else:
                days_left = due_day - current_day
                status = "Upcoming"
                status_color = "info"
                status_badge = f"Due in {days_left} day{'s' if days_left > 1 else ''}"

            results.append({
                "bill_id": r["bill_id"],
                "title": r["title"],
                "amount": float(r["amount"]),
                "category_id": r["category_id"],
                "category_name": r["category_name"] or "General",
                "icon_name": r["icon_name"] or "bi-calendar-check",
                "due_day": due_day,
                "frequency": r["frequency"],
                "payment_mode": r["payment_mode"],
                "notes": r["notes"] or "",
                "last_paid_date": last_paid,
                "is_paid": is_paid,
                "status": status,
                "status_color": status_color,
                "status_badge": status_badge,
            })
        return results

    @staticmethod
    def _seed_sqlite_defaults(user_id):
        defaults = [
            (user_id, "Flat Rent & Maintenance", 15000.0, 1, 5, "Monthly", "Net Banking", "Shared apartment rent transfer to landlord"),
            (user_id, "High-Speed Fiber Wi-Fi", 999.0, 4, 10, "Monthly", "UPI", "Airtel Xstream 200 Mbps broadband"),
            (user_id, "Electricity & Power Bill", 1850.0, 4, 15, "Monthly", "UPI", "State electricity board bill"),
            (user_id, "Nifty 50 Index Fund SIP", 5000.0, 7, 1, "Monthly", "Net Banking", "Automated monthly investment"),
        ]
        for d in defaults:
            execute_db("""
                INSERT INTO recurring_bills (user_id, title, amount, category_id, due_day, frequency, payment_mode, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, d)

    @staticmethod
    def get_by_id(bill_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoRecurringModel
            return MongoRecurringModel.get_by_id(bill_id, user_id)

        RecurringModel._init_sqlite_table()
        row = query_db("""
            SELECT r.*, c.category_name, c.icon_name
            FROM recurring_bills r
            LEFT JOIN categories c ON r.category_id = c.category_id
            WHERE r.bill_id = ? AND r.user_id = ?
        """, (bill_id, user_id), one=True)
        return dict(row) if row else None

    @staticmethod
    def create(user_id, title, amount, category_id, due_day=1, frequency="Monthly", payment_mode="UPI", notes=""):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoRecurringModel
            return MongoRecurringModel.create(user_id, title, amount, category_id, due_day, frequency, payment_mode, notes)

        RecurringModel._init_sqlite_table()
        last_id, _ = execute_db("""
            INSERT INTO recurring_bills (user_id, title, amount, category_id, due_day, frequency, payment_mode, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (user_id, title.strip(), float(amount), int(category_id), int(due_day), frequency, payment_mode, notes.strip() if notes else ""))
        return last_id

    @staticmethod
    def update(bill_id, user_id, title, amount, category_id, due_day=1, frequency="Monthly", payment_mode="UPI", notes=""):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoRecurringModel
            return MongoRecurringModel.update(bill_id, user_id, title, amount, category_id, due_day, frequency, payment_mode, notes)

        RecurringModel._init_sqlite_table()
        _, rowcount = execute_db("""
            UPDATE recurring_bills
            SET title = ?, amount = ?, category_id = ?, due_day = ?, frequency = ?, payment_mode = ?, notes = ?
            WHERE bill_id = ? AND user_id = ?;
        """, (title.strip(), float(amount), int(category_id), int(due_day), frequency, payment_mode, notes.strip() if notes else "", bill_id, user_id))
        return rowcount > 0

    @staticmethod
    def delete(bill_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoRecurringModel
            return MongoRecurringModel.delete(bill_id, user_id)

        RecurringModel._init_sqlite_table()
        _, rowcount = execute_db("DELETE FROM recurring_bills WHERE bill_id = ? AND user_id = ?;", (bill_id, user_id))
        return rowcount > 0

    @staticmethod
    def mark_paid(bill_id, user_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoRecurringModel
            return MongoRecurringModel.mark_paid(bill_id, user_id)

        RecurringModel._init_sqlite_table()
        bill = query_db("SELECT * FROM recurring_bills WHERE bill_id = ? AND user_id = ?;", (bill_id, user_id), one=True)
        if not bill:
            return None, "Recurring bill not found."

        today_str = datetime.date.today().isoformat()
        from backend.models.expense_model import ExpenseModel
        exp_id = ExpenseModel.create(
            user_id=user_id,
            category_id=bill["category_id"],
            title=f"Bill: {bill['title']}",
            amount=bill["amount"],
            payment_mode=bill["payment_mode"],
            expense_date=today_str,
            notes=f"Monthly recurring bill payment for {bill['title']}"
        )

        execute_db("UPDATE recurring_bills SET last_paid_date = ? WHERE bill_id = ?;", (today_str, bill_id))
        return exp_id, None
