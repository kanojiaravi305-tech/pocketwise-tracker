"""
database/init_mongo.py
Initializes MongoDB / MongoDB Atlas collections, performance indexes,
and seeds comprehensive PocketWise expense dummy data.
"""

import sys
import os
import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config.mongodb import get_mongo_db, MONGO_URI, is_atlas_connected

def init_mongo_database():
    target_type = "MongoDB Atlas (Cloud)" if is_atlas_connected() else "Local MongoDB"
    print(f"Connecting to {target_type} at: {MONGO_URI} ...")

    try:
        db = get_mongo_db()
        db.command("ping")
        print(f"[OK] Successfully authenticated and connected to {target_type}!")
    except Exception as e:
        print(f"[ERROR] Failed to connect to MongoDB: {e}")
        print("Please verify your MONGO_URI in .env")
        return False

    # 1. Drop existing collections to clean-seed
    db.users.drop()
    db.categories.drop()
    db.expenses.drop()
    db.split_records.drop()
    print("[OK] Cleared collections (users, categories, expenses, split_records).")

    # 2. Create Indexes
    db.users.create_index("email", unique=True)
    db.categories.create_index("category_name", unique=True)
    db.expenses.create_index([("user_id", 1), ("expense_date", -1)])
    db.expenses.create_index("category_id")
    db.split_records.create_index("expense_id")
    db.split_records.create_index("user_id")
    print("[OK] Created performance indexes and unique constraints.")

    # 3. Seed 8 Universal Categories
    categories_data = [
        {"category_name": "Housing & Rent", "icon_name": "bi-house-door-fill", "color_code": "#0d6efd", "monthly_limit": 15000.0},
        {"category_name": "Groceries & Dining", "icon_name": "bi-cart-fill", "color_code": "#fd7e14", "monthly_limit": 8000.0},
        {"category_name": "Commute & Fuel", "icon_name": "bi-fuel-pump-fill", "color_code": "#20c997", "monthly_limit": 4000.0},
        {"category_name": "Utilities & Bills (Electricity, Wi-Fi, Phone)", "icon_name": "bi-lightning-charge-fill", "color_code": "#6f42c1", "monthly_limit": 3500.0},
        {"category_name": "Shopping & Lifestyle", "icon_name": "bi-bag-heart-fill", "color_code": "#e83e8c", "monthly_limit": 5000.0},
        {"category_name": "Healthcare & Fitness", "icon_name": "bi-heart-pulse-fill", "color_code": "#dc3545", "monthly_limit": 3000.0},
        {"category_name": "Investments & Savings", "icon_name": "bi-graph-up-arrow", "color_code": "#198754", "monthly_limit": 10000.0},
        {"category_name": "Miscellaneous", "icon_name": "bi-three-dots", "color_code": "#6c757d", "monthly_limit": 2500.0},
    ]

    cat_id_map = {}
    for c in categories_data:
        res = db.categories.insert_one(c)
        cat_id_map[c["category_name"]] = res.inserted_id
    print(f"[OK] Seeded {len(categories_data)} universal categories.")

    # 4. Seed Demo User (Rahul Sharma)
    user_res = db.users.insert_one({
        "full_name": "Rahul Sharma",
        "email": "rahul@pocketwise.io",
        "password_hash": generate_password_hash("student123"),
        "monthly_budget_limit": 50000.0,
        "created_at": datetime.datetime.now(datetime.timezone.utc),
    })
    user_id = user_res.inserted_id
    print(f"[OK] Created demo user: Rahul Sharma (rahul@pocketwise.io / student123), Budget: INR 50,000")

    # 5. Generate Past 5 Months + Current Month Expenses
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

    past_expenses = [
        # 5 months ago
        ("Housing & Rent", "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(5, 1), "Monthly rent transfer"),
        ("Groceries & Dining", "Monthly Supermarket Stockup", 6800.0, "Card", get_month_date(5, 5), "Groceries & pantry"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Broadband & Power Bill", 2650.0, "Net Banking", get_month_date(5, 8), "Electricity & fiber"),
        ("Commute & Fuel", "Petrol Tank Full", 2800.0, "UPI", get_month_date(5, 12), "Vehicle fuel"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 5000.0, "Net Banking", get_month_date(5, 15), "Monthly automated SIP"),

        # 4 months ago
        ("Housing & Rent", "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(4, 1), "Monthly rent transfer"),
        ("Groceries & Dining", "Supermarket & Weekend Cafe", 7100.0, "Card", get_month_date(4, 6), "Food & grocery bills"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity & Water Bill", 2400.0, "Net Banking", get_month_date(4, 10), "Utility bill payment"),
        ("Commute & Fuel", "Fuel & Fastag Recharge", 3100.0, "UPI", get_month_date(4, 14), "Daily highway commute"),
        ("Shopping & Lifestyle", "Formal Office Apparel", 3450.0, "Card", get_month_date(4, 20), "Shirts & trousers"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 5000.0, "Net Banking", get_month_date(4, 25), "Automated mutual fund SIP"),

        # 3 months ago
        ("Housing & Rent", "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(3, 1), "Monthly rent transfer"),
        ("Groceries & Dining", "Groceries & Gourmet Dining", 7450.0, "Card", get_month_date(3, 7), "Household provisions"),
        ("Healthcare & Fitness", "Quarterly Gym Membership", 3000.0, "UPI", get_month_date(3, 11), "Fitness center renewal"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity Bill - ₹1,850", 1850.0, "Net Banking", get_month_date(3, 15), "State electricity board"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 6000.0, "Net Banking", get_month_date(3, 18), "Stepped-up monthly SIP"),
        ("Commute & Fuel", "Petrol & Metro Smart Card", 3200.0, "UPI", get_month_date(3, 22), "Transit & fuel"),

        # 2 months ago
        ("Housing & Rent", "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(2, 1), "Updated lease rent"),
        ("Groceries & Dining", "Supermarket Groceries & Snacks", 7200.0, "Card", get_month_date(2, 6), "Provisions & fruits"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Monthly Wi-Fi Bill", 999.0, "UPI", get_month_date(2, 10), "Airtel Xstream Fiber"),
        ("Commute & Fuel", "Car Servicing & Fuel", 4200.0, "Card", get_month_date(2, 16), "Routine vehicle maintenance"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 6000.0, "Net Banking", get_month_date(2, 20), "Monthly automated SIP"),
        ("Shopping & Lifestyle", "Noise-Cancelling Headphones", 4500.0, "Card", get_month_date(2, 25), "Remote work equipment"),

        # 1 month ago
        ("Housing & Rent", "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(1, 1), "Monthly rent"),
        ("Groceries & Dining", "Supermarket Groceries & Dining", 7600.0, "Card", get_month_date(1, 6), "Monthly provisions"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity Bill", 1920.0, "Net Banking", get_month_date(1, 11), "Monthly power bill"),
        ("Commute & Fuel", "Petrol & Toll Tax", 3350.0, "UPI", get_month_date(1, 16), "Fuel & transit"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 7000.0, "Net Banking", get_month_date(1, 20), "Investment portfolio allocation"),
        ("Healthcare & Fitness", "Family Medical Health Checkup", 2200.0, "Card", get_month_date(1, 25), "Diagnostic lab tests"),
    ]

    current_expenses = [
        ("Housing & Rent", "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(0, 1), "Transferred via NEFT to landlord"),
        ("Investments & Savings", "SIP Mutual Fund Investment", 5000.0, "Net Banking", get_month_date(0, 2), "Index Fund Growth Plan"),
        ("Investments & Savings", "PPF Voluntary Savings", 3000.0, "Net Banking", get_month_date(0, 10), "Public Provident Fund deposit"),
        ("Groceries & Dining", "Monthly Supermarket Stockup", 4200.0, "Card", get_month_date(0, 5), "Fresh organic produce & pantry"),
        ("Groceries & Dining", "Swiggy & Dining Out", 2450.0, "UPI", get_month_date(0, 14), "Weekend food orders"),
        ("Groceries & Dining", "Team Lunch Split", 1850.0, "Card", get_month_date(0, 18), "Celebration lunch with colleagues"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity Board Power Bill", 1850.0, "Net Banking", get_month_date(0, 3), "Online bill payment portal"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Monthly Wi-Fi Bill", 999.0, "UPI", get_month_date(0, 7), "High-speed broadband plan"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Mobile Postpaid Family Plan", 799.0, "UPI", get_month_date(0, 20), "Unlimited calling & shared data"),
        ("Commute & Fuel", "Petrol / Fuel Station", 2200.0, "UPI", get_month_date(0, 9), "Fuel station auto-cut pump"),
        ("Commute & Fuel", "Metro Card Transit Pass", 800.0, "UPI", get_month_date(0, 13), "Daily office express commute"),
        ("Healthcare & Fitness", "Monthly Gym Membership", 1500.0, "UPI", get_month_date(0, 12), "Fitness club access"),
        ("Healthcare & Fitness", "Pharmacy & Health Supplements", 450.0, "Card", get_month_date(0, 17), "Multivitamins & first aid kit"),
        ("Shopping & Lifestyle", "Home Workstation Accessories", 650.0, "Card", get_month_date(0, 16), "Work desk organizer"),
    ]

    all_seed_expenses = past_expenses + current_expenses
    team_lunch_eid = None
    broadband_eid = None

    for cat_name, title, amt, mode, exp_date, notes in all_seed_expenses:
        cid = cat_id_map.get(cat_name)
        cat_info = next((c for c in categories_data if c["category_name"] == cat_name), {})
        ins = db.expenses.insert_one({
            "user_id": user_id,
            "category_id": cid,
            "category_name": cat_name,
            "icon_name": cat_info.get("icon_name", "bi-tag"),
            "color_code": cat_info.get("color_code", "#0d6efd"),
            "title": title,
            "amount": float(amt),
            "payment_mode": mode,
            "expense_date": exp_date.isoformat(),
            "notes": notes,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
        if "Team Lunch Split" in title:
            team_lunch_eid = ins.inserted_id
        elif "Monthly Wi-Fi Bill" in title:
            broadband_eid = ins.inserted_id

    print(f"[OK] Seeded {len(all_seed_expenses)} everyday expenses in MongoDB.")

    # 6. Seed Shared Bill Splits
    if team_lunch_eid:
        db.split_records.insert_many([
            {"expense_id": team_lunch_eid, "user_id": user_id, "friend_name": "Vikram Rao", "amount_owed": 600.0, "is_settled": True, "settled_at": "2026-10-18 14:00:00", "created_at": datetime.datetime.now(datetime.timezone.utc)},
            {"expense_id": team_lunch_eid, "user_id": user_id, "friend_name": "Neha Sharma", "amount_owed": 625.0, "is_settled": False, "settled_at": None, "created_at": datetime.datetime.now(datetime.timezone.utc)},
        ])

    if broadband_eid:
        db.split_records.insert_many([
            {"expense_id": broadband_eid, "user_id": user_id, "friend_name": "Rohan Kulkarni (Flatmate)", "amount_owed": 333.0, "is_settled": True, "settled_at": "2026-10-08 10:30:00", "created_at": datetime.datetime.now(datetime.timezone.utc)},
            {"expense_id": broadband_eid, "user_id": user_id, "friend_name": "Amit Patel (Flatmate)", "amount_owed": 333.0, "is_settled": False, "settled_at": None, "created_at": datetime.datetime.now(datetime.timezone.utc)},
        ])

    print("[OK] Seeded shared group bill split records in MongoDB.")

    # 7. Seed Recurring Bills & Savings Goals
    from backend.models.mongo_models import MongoRecurringModel, MongoSavingsModel
    MongoRecurringModel.seed_defaults_if_empty(user_id)
    MongoSavingsModel.seed_defaults_if_empty(user_id)
    print("[OK] Seeded recurring bills and savings goals in MongoDB.")

    print("\n[SUCCESS] PocketWise MongoDB initialization complete!")
    return True


def ensure_user_seeded(user_id, force=False):
    """
    Guarantees that a user has:
    1. Monthly budget limit of INR 50,000.00
    2. Realistic October 2026 expenses totaling INR 40,748.00 (81.5% utilization)
    3. 6 months of historical data for the trend chart
    4. Sample recurring bills and savings goals
    """
    db = get_mongo_db()
    from bson import ObjectId
    uid = ObjectId(str(user_id)) if not isinstance(user_id, ObjectId) else user_id

    # Update user monthly budget limit to 50,000 if not set
    db.users.update_one(
        {"_id": uid},
        {"$set": {"monthly_budget_limit": 50000.0}}
    )

    current_count = db.expenses.count_documents({"user_id": uid})
    if current_count > 0 and not force:
        # Also ensure recurring bills and savings goals
        from backend.models.mongo_models import MongoRecurringModel, MongoSavingsModel
        MongoRecurringModel.seed_defaults_if_empty(uid)
        MongoSavingsModel.seed_defaults_if_empty(uid)
        return

    # If force, clear old expenses and splits for this user
    if force:
        db.expenses.delete_many({"user_id": uid})
        db.split_records.delete_many({"user_id": uid})
        db.recurring_bills.delete_many({"user_id": uid})
        db.savings_goals.delete_many({"user_id": uid})

    # Fetch categories
    cats = list(db.categories.find())
    cat_map = {c["category_name"]: c for c in cats}
    default_cat = cats[0] if cats else None

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

    past_expenses = [
        ("Housing & Rent", "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(5, 1), "Monthly rent transfer"),
        ("Groceries & Dining", "Monthly Supermarket Stockup", 6800.0, "Card", get_month_date(5, 5), "Groceries & pantry"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Broadband & Power Bill", 2650.0, "Net Banking", get_month_date(5, 8), "Electricity & fiber"),
        ("Commute & Fuel", "Petrol Tank Full", 2800.0, "UPI", get_month_date(5, 12), "Vehicle fuel"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 5000.0, "Net Banking", get_month_date(5, 15), "Monthly automated SIP"),

        ("Housing & Rent", "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(4, 1), "Monthly rent transfer"),
        ("Groceries & Dining", "Supermarket & Weekend Cafe", 7100.0, "Card", get_month_date(4, 6), "Food & grocery bills"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity & Water Bill", 2400.0, "Net Banking", get_month_date(4, 10), "Utility bill payment"),
        ("Commute & Fuel", "Fuel & Fastag Recharge", 3100.0, "UPI", get_month_date(4, 14), "Daily highway commute"),
        ("Shopping & Lifestyle", "Formal Office Apparel", 3450.0, "Card", get_month_date(4, 20), "Shirts & trousers"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 5000.0, "Net Banking", get_month_date(4, 25), "Automated mutual fund SIP"),

        ("Housing & Rent", "Apartment Monthly Rent", 14500.0, "Net Banking", get_month_date(3, 1), "Monthly rent transfer"),
        ("Groceries & Dining", "Groceries & Gourmet Dining", 7450.0, "Card", get_month_date(3, 7), "Household provisions"),
        ("Healthcare & Fitness", "Quarterly Gym Membership", 3000.0, "UPI", get_month_date(3, 11), "Fitness center renewal"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity Bill - ₹1,850", 1850.0, "Net Banking", get_month_date(3, 15), "State electricity board"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 6000.0, "Net Banking", get_month_date(3, 18), "Stepped-up monthly SIP"),
        ("Commute & Fuel", "Petrol & Metro Smart Card", 3200.0, "UPI", get_month_date(3, 22), "Transit & fuel"),

        ("Housing & Rent", "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(2, 1), "Updated lease rent"),
        ("Groceries & Dining", "Supermarket Groceries & Snacks", 7200.0, "Card", get_month_date(2, 6), "Provisions & fruits"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Monthly Wi-Fi Bill", 999.0, "UPI", get_month_date(2, 10), "Airtel Xstream Fiber"),
        ("Commute & Fuel", "Car Servicing & Fuel", 4200.0, "Card", get_month_date(2, 16), "Routine vehicle maintenance"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 6000.0, "Net Banking", get_month_date(2, 20), "Monthly automated SIP"),
        ("Shopping & Lifestyle", "Noise-Cancelling Headphones", 4500.0, "Card", get_month_date(2, 25), "Remote work equipment"),

        ("Housing & Rent", "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(1, 1), "Monthly rent"),
        ("Groceries & Dining", "Supermarket Groceries & Dining", 7600.0, "Card", get_month_date(1, 6), "Monthly provisions"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity Bill", 1920.0, "Net Banking", get_month_date(1, 11), "Monthly power bill"),
        ("Commute & Fuel", "Petrol & Toll Tax", 3350.0, "UPI", get_month_date(1, 16), "Fuel & transit"),
        ("Investments & Savings", "Mutual Fund Equity SIP", 7000.0, "Net Banking", get_month_date(1, 20), "Investment portfolio allocation"),
        ("Healthcare & Fitness", "Family Medical Health Checkup", 2200.0, "Card", get_month_date(1, 25), "Diagnostic lab tests"),
    ]

    current_expenses = [
        ("Housing & Rent", "Apartment Monthly Rent", 15000.0, "Net Banking", get_month_date(0, 1), "Transferred via NEFT to landlord"),
        ("Investments & Savings", "SIP Mutual Fund Investment", 5000.0, "Net Banking", get_month_date(0, 2), "Index Fund Growth Plan"),
        ("Investments & Savings", "PPF Voluntary Savings", 3000.0, "Net Banking", get_month_date(0, 10), "Public Provident Fund deposit"),
        ("Groceries & Dining", "Monthly Supermarket Stockup", 4200.0, "Card", get_month_date(0, 5), "Fresh organic produce & pantry"),
        ("Groceries & Dining", "Swiggy & Dining Out", 2450.0, "UPI", get_month_date(0, 14), "Weekend food orders"),
        ("Groceries & Dining", "Team Lunch Split", 1850.0, "Card", get_month_date(0, 18), "Celebration lunch with colleagues"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Electricity Board Power Bill", 1850.0, "Net Banking", get_month_date(0, 3), "Online bill payment portal"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Monthly Wi-Fi Bill", 999.0, "UPI", get_month_date(0, 7), "High-speed broadband plan"),
        ("Utilities & Bills (Electricity, Wi-Fi, Phone)", "Mobile Postpaid Family Plan", 799.0, "UPI", get_month_date(0, 20), "Unlimited calling & shared data"),
        ("Commute & Fuel", "Petrol / Fuel Station", 2200.0, "UPI", get_month_date(0, 9), "Fuel station auto-cut pump"),
        ("Commute & Fuel", "Metro Card Transit Pass", 800.0, "UPI", get_month_date(0, 13), "Daily office express commute"),
        ("Healthcare & Fitness", "Monthly Gym Membership", 1500.0, "UPI", get_month_date(0, 12), "Fitness club access"),
        ("Healthcare & Fitness", "Pharmacy & Health Supplements", 450.0, "Card", get_month_date(0, 17), "Multivitamins & first aid kit"),
        ("Shopping & Lifestyle", "Home Workstation Accessories", 650.0, "Card", get_month_date(0, 16), "Work desk organizer"),
    ]

    all_seed = past_expenses + current_expenses
    team_lunch_eid = None
    broadband_eid = None

    for cat_name, title, amt, mode, exp_date, notes in all_seed:
        cat_info = cat_map.get(cat_name) or default_cat or {}
        cid = cat_info.get("_id")
        ins = db.expenses.insert_one({
            "user_id": uid,
            "category_id": cid,
            "category_name": cat_name,
            "icon_name": cat_info.get("icon_name", "bi-tag"),
            "color_code": cat_info.get("color_code", "#0d6efd"),
            "title": title,
            "amount": float(amt),
            "payment_mode": mode,
            "expense_date": exp_date.isoformat(),
            "notes": notes,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
        if "Team Lunch Split" in title:
            team_lunch_eid = ins.inserted_id
        elif "Monthly Wi-Fi Bill" in title:
            broadband_eid = ins.inserted_id

    if team_lunch_eid:
        db.split_records.insert_many([
            {"expense_id": team_lunch_eid, "user_id": uid, "friend_name": "Vikram Rao", "amount_owed": 600.0, "is_settled": True, "settled_at": "2026-10-18 14:00:00", "created_at": datetime.datetime.now(datetime.timezone.utc)},
            {"expense_id": team_lunch_eid, "user_id": uid, "friend_name": "Neha Sharma", "amount_owed": 625.0, "is_settled": False, "settled_at": None, "created_at": datetime.datetime.now(datetime.timezone.utc)},
        ])

    if broadband_eid:
        db.split_records.insert_many([
            {"expense_id": broadband_eid, "user_id": uid, "friend_name": "Rohan Kulkarni (Flatmate)", "amount_owed": 333.0, "is_settled": True, "settled_at": "2026-10-08 10:30:00", "created_at": datetime.datetime.now(datetime.timezone.utc)},
            {"expense_id": broadband_eid, "user_id": uid, "friend_name": "Amit Patel (Flatmate)", "amount_owed": 333.0, "is_settled": False, "settled_at": None, "created_at": datetime.datetime.now(datetime.timezone.utc)},
        ])

    from backend.models.mongo_models import MongoRecurringModel, MongoSavingsModel
    MongoRecurringModel.seed_defaults_if_empty(uid)
    MongoSavingsModel.seed_defaults_if_empty(uid)


if __name__ == "__main__":
    init_mongo_database()
