"""
database/init_db.py
Database Initialization & Seed Data Script
PocketWise: Personal Finance & Expense Tracker
"""

import os
import sqlite3
import datetime
from werkzeug.security import generate_password_hash

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, "expenses.db")
SCHEMA_PATH = os.path.join(DB_DIR, "schema.sql")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_database():
    print(f"Initializing SQLite database at: {DB_PATH}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Read and execute schema
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    print("[OK] Schema created successfully (4 normalized tables).")

    # 1. Insert 8 Universal Categories for Everyday Professionals / Freelancers
    categories = [
        ("Housing & Rent", "bi-house-door-fill", "#0d6efd", 15000.0),
        ("Groceries & Dining", "bi-cart-fill", "#fd7e14", 8000.0),
        ("Commute & Fuel", "bi-fuel-pump-fill", "#20c997", 4000.0),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "bi-lightning-charge-fill", "#6f42c1", 3500.0),
        ("Shopping & Lifestyle", "bi-bag-heart-fill", "#e83e8c", 5000.0),
        ("Healthcare & Fitness", "bi-heart-pulse-fill", "#dc3545", 3000.0),
        ("Investments & Savings", "bi-graph-up-arrow", "#198754", 10000.0),
        ("Miscellaneous", "bi-three-dots", "#6c757d", 2500.0),
    ]
    cursor.executemany(
        """
        INSERT INTO categories (category_name, icon_name, color_code, monthly_limit)
        VALUES (?, ?, ?, ?);
        """,
        categories,
    )
    print(f"[OK] Inserted {len(categories)} universal categories.")

    # 2. Insert Demo User (Working Professional / Freelancer)
    password_hash = generate_password_hash("student123")
    cursor.execute(
        """
        INSERT INTO users (full_name, email, password_hash, monthly_budget_limit)
        VALUES (?, ?, ?, ?);
        """,
        ("Rahul Sharma", "rahul@pocketwise.io", password_hash, 50000.0),
    )
    user_id = cursor.lastrowid
    print(f"[OK] Created demo user: Rahul Sharma (rahul@pocketwise.io / student123), Budget: INR 50,000")

    # Retrieve category map
    cursor.execute("SELECT category_name, category_id FROM categories;")
    cat_map = {row["category_name"]: row["category_id"] for row in cursor.fetchall()}

    # 3. Seed Realistic Everyday Indian Expenses
    today = datetime.date.today()
    
    def get_month_date(months_back, day=15):
        year = today.year
        month = today.month - months_back
        while month <= 0:
            month += 12
            year -= 1
        if month in [4, 6, 9, 11] and day > 30:
            day = 30
        elif month == 2 and day > 28:
            day = 28
        return datetime.date(year, month, day)

    # Historical expenses for the previous 5 months (generates 6-month MoM trend)
    past_months_expenses = [
        # 5 months ago
        (cat_map["Housing & Rent"], "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(5, 1), "Monthly rent transfer"),
        (cat_map["Groceries & Dining"], "Monthly Supermarket Stockup", 6800.0, "Card", get_month_date(5, 5), "Groceries & pantry"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Broadband & Power Bill", 2650.0, "Net Banking", get_month_date(5, 8), "Electricity & fiber"),
        (cat_map["Commute & Fuel"], "Petrol Tank Full", 2800.0, "UPI", get_month_date(5, 12), "Vehicle fuel"),
        (cat_map["Investments & Savings"], "Mutual Fund Equity SIP", 5000.0, "Net Banking", get_month_date(5, 15), "Monthly automated SIP"),

        # 4 months ago
        (cat_map["Housing & Rent"], "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(4, 1), "Monthly rent transfer"),
        (cat_map["Groceries & Dining"], "Supermarket & Weekend Cafe", 7100.0, "Card", get_month_date(4, 6), "Food & grocery bills"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Electricity & Water Bill", 2400.0, "Net Banking", get_month_date(4, 10), "Utility bill payment"),
        (cat_map["Commute & Fuel"], "Fuel & Fastag Recharge", 3100.0, "UPI", get_month_date(4, 14), "Daily highway commute"),
        (cat_map["Shopping & Lifestyle"], "Formal Office Apparel", 3450.0, "Card", get_month_date(4, 20), "Shirts & trousers"),
        (cat_map["Investments & Savings"], "Mutual Fund Equity SIP", 5000.0, "Net Banking", get_month_date(4, 25), "Automated mutual fund SIP"),

        # 3 months ago
        (cat_map["Housing & Rent"], "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(3, 1), "Monthly rent transfer"),
        (cat_map["Groceries & Dining"], "Groceries & Gourmet Dining", 7450.0, "Card", get_month_date(3, 7), "Household provisions"),
        (cat_map["Healthcare & Fitness"], "Quarterly Gym Membership", 3000.0, "UPI", get_month_date(3, 11), "Fitness center renewal"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Electricity Bill - ₹1,850", 1850.0, "Net Banking", get_month_date(3, 15), "State electricity board"),
        (cat_map["Investments & Savings"], "Mutual Fund Equity SIP", 6000.0, "Net Banking", get_month_date(3, 18), "Stepped-up monthly SIP"),
        (cat_map["Commute & Fuel"], "Petrol & Metro Smart Card", 3200.0, "UPI", get_month_date(3, 22), "Transit & fuel"),

        # 2 months ago
        (cat_map["Housing & Rent"], "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(2, 1), "Updated lease rent"),
        (cat_map["Groceries & Dining"], "Supermarket Groceries & Snacks", 7200.0, "Card", get_month_date(2, 6), "Provisions & fruits"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Monthly Wi-Fi Bill", 999.0, "UPI", get_month_date(2, 10), "Airtel Xstream Fiber"),
        (cat_map["Commute & Fuel"], "Car Servicing & Fuel", 4200.0, "Card", get_month_date(2, 16), "Routine vehicle maintenance"),
        (cat_map["Investments & Savings"], "Mutual Fund Equity SIP", 6000.0, "Net Banking", get_month_date(2, 20), "Monthly automated SIP"),
        (cat_map["Shopping & Lifestyle"], "Noise-Cancelling Headphones", 4500.0, "Card", get_month_date(2, 25), "Remote work equipment"),

        # 1 month ago
        (cat_map["Housing & Rent"], "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(1, 1), "Monthly rent"),
        (cat_map["Groceries & Dining"], "Supermarket Groceries & Dining", 7600.0, "Card", get_month_date(1, 6), "Monthly provisions"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Electricity Bill", 1920.0, "Net Banking", get_month_date(1, 11), "Monthly power bill"),
        (cat_map["Commute & Fuel"], "Petrol & Toll Tax", 3350.0, "UPI", get_month_date(1, 16), "Fuel & transit"),
        (cat_map["Investments & Savings"], "Mutual Fund Equity SIP", 7000.0, "Net Banking", get_month_date(1, 20), "Investment portfolio allocation"),
        (cat_map["Healthcare & Fitness"], "Family Medical Health Checkup", 2200.0, "Card", get_month_date(1, 25), "Diagnostic lab tests"),
    ]

    for cat_id, title, amt, mode, exp_date, notes in past_months_expenses:
        cursor.execute(
            """
            INSERT INTO expenses (user_id, category_id, title, amount, payment_mode, expense_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (user_id, cat_id, title, amt, mode, exp_date.isoformat(), notes),
        )

    # Current Month Expenses (~₹39,800 spent out of ₹50,000 -> ~79.6% comfortably paced!)
    current_month_expenses = [
        (cat_map["Housing & Rent"], "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(0, 1), "Transferred via NEFT to landlord"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Electricity Bill - ₹1,850", 1850.0, "Net Banking", get_month_date(0, 3), "Online bill payment portal"),
        (cat_map["Groceries & Dining"], "Supermarket Groceries - ₹1,450", 1450.0, "Card", get_month_date(0, 5), "Fresh organic produce & pantry"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Monthly Wi-Fi Bill - ₹999", 999.0, "UPI", get_month_date(0, 7), "High-speed broadband plan"),
        (cat_map["Commute & Fuel"], "Petrol / Fuel - ₹500", 500.0, "UPI", get_month_date(0, 9), "Fuel station auto-cut pump"),
        (cat_map["Groceries & Dining"], "Team Lunch Split - ₹1,200", 1200.0, "Card", get_month_date(0, 10), "Quarterly celebration lunch with colleagues"),
        (cat_map["Investments & Savings"], "SIP Mutual Fund Investment", 5000.0, "Net Banking", get_month_date(0, 11), "Index Fund Growth Plan"),
        (cat_map["Healthcare & Fitness"], "Monthly Gym Membership", 1500.0, "UPI", get_month_date(0, 12), "Fitness club access"),
        (cat_map["Commute & Fuel"], "Metro Card Monthly Transit Pass", 800.0, "UPI", get_month_date(0, 13), "Daily office express commute"),
        (cat_map["Groceries & Dining"], "Weekly Supermarket Restock", 2350.0, "Card", get_month_date(0, 15), "Vegetables, dairy & snacks"),
        (cat_map["Shopping & Lifestyle"], "Work Desk Ergonomic Stand", 1200.0, "Card", get_month_date(0, 16), "Home workspace setup"),
        (cat_map["Healthcare & Fitness"], "Pharmacy & Wellness", 450.0, "UPI", get_month_date(0, 17), "Multivitamins & first aid kit"),
        (cat_map["Commute & Fuel"], "Weekend Road Trip Fuel Split", 1500.0, "UPI", get_month_date(0, 18), "Highway fuel split with friends"),
        (cat_map["Groceries & Dining"], "Weekend Dining Out", 1850.0, "Card", get_month_date(0, 19), "Family dinner at bistro"),
        (cat_map["Utilities & Bills (Electricity, Wi-Fi, Phone)"], "Mobile Postpaid Family Plan", 799.0, "UPI", get_month_date(0, 20), "Unlimited calling & shared data"),
        (cat_map["Miscellaneous"], "Home Water Purifier Filter Cartridge", 650.0, "Cash", get_month_date(0, 20), "RO system replacement filter"),
    ]

    team_lunch_expense_id = None
    broadband_expense_id = None
    roadtrip_expense_id = None

    for cat_id, title, amt, mode, exp_date, notes in current_month_expenses:
        cursor.execute(
            """
            INSERT INTO expenses (user_id, category_id, title, amount, payment_mode, expense_date, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (user_id, cat_id, title, amt, mode, exp_date.isoformat(), notes),
        )
        last_id = cursor.lastrowid
        if "Team Lunch Split" in title:
            team_lunch_expense_id = last_id
        elif "Monthly Wi-Fi Bill" in title:
            broadband_expense_id = last_id
        elif "Weekend Road Trip Fuel" in title:
            roadtrip_expense_id = last_id

    print(f"[OK] Inserted {len(past_months_expenses) + len(current_month_expenses)} realistic everyday expenses.")

    # 4. Seed Split Records for Shared Expenses & Group Splitter
    # Team Lunch: ₹1,200 split 3 ways = ₹400 each (Vikram Rao [Settled], Neha Sharma [Pending])
    if team_lunch_expense_id:
        cursor.execute(
            """
            INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP);
            """,
            (team_lunch_expense_id, "Vikram Rao", 400.0),
        )
        cursor.execute(
            """
            INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
            VALUES (?, ?, ?, 0, NULL);
            """,
            (team_lunch_expense_id, "Neha Sharma", 400.0),
        )

    # Monthly Broadband: ₹999 split 3 ways = ₹333 each (Flatmate Rohan [Settled], Flatmate Amit [Pending])
    if broadband_expense_id:
        cursor.execute(
            """
            INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP);
            """,
            (broadband_expense_id, "Rohan Kulkarni (Flatmate)", 333.0),
        )
        cursor.execute(
            """
            INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
            VALUES (?, ?, ?, 0, NULL);
            """,
            (broadband_expense_id, "Amit Patel (Flatmate)", 333.0),
        )

    # Weekend Road Trip Fuel: ₹1,500 split 3 ways = ₹500 each (Sameer [Pending], Pooja [Settled])
    if roadtrip_expense_id:
        cursor.execute(
            """
            INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
            VALUES (?, ?, ?, 0, NULL);
            """,
            (roadtrip_expense_id, "Sameer Deshmukh", 500.0),
        )
        cursor.execute(
            """
            INSERT INTO split_records (expense_id, friend_name, amount_owed, is_settled, settled_at)
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP);
            """,
            (roadtrip_expense_id, "Pooja Hegde", 500.0),
        )

    print("[OK] Inserted shared group split records (Vikram, Neha, Rohan, Amit, Sameer, Pooja).")

    conn.commit()
    conn.close()
    print("[OK] Database initialization complete! Ready for PocketWise application start.")

if __name__ == "__main__":
    init_database()
