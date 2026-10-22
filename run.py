"""
run.py
Root launcher for Student & Shared Living Expense Tracker.
Supports both MongoDB (Local / Atlas Cloud) and SQLite engines.
Usage:
    python run.py
"""

import os
import sys

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.config.mongodb import DB_ENGINE, MONGO_URI, is_atlas_connected, get_mongo_db
from database.init_db import init_database, DB_PATH
from database.init_mongo import init_mongo_database
from backend.app import create_app

def main():
    print("=" * 68)
    print("  POCKETWISE: PERSONAL FINANCE & SHARED EXPENSE TRACKER")
    print("  Classic 3-Tier Monolithic Architecture (Presentation - Logic - Data)")
    print("=" * 68)

    if DB_ENGINE == "mongodb":
        target = "MongoDB Atlas (Cloud)" if is_atlas_connected() else "Local MongoDB"
        print(f"\n[+] Active Database Engine: {target}")
        print(f"    Connection String: {MONGO_URI}")
        try:
            db = get_mongo_db()
            user = db.users.find_one({"email": "rahul@pocketwise.io"})
            if not user or db.expenses.count_documents({"user_id": user["_id"]}) == 0:
                print("    Seeding MongoDB collections with comprehensive PocketWise data (INR 40,748 October target)...")
                init_mongo_database()
            else:
                print(f"    [OK] Connected. Found {db.expenses.count_documents({})} recorded expenses.")
        except Exception as e:
            print(f"    [!] MongoDB connection warning: {e}")
            print("    Please ensure MongoDB is running or verify your Atlas URI in .env")
    else:
        print(f"\n[+] Active Database Engine: SQLite RDBMS")
        if not os.path.exists(DB_PATH):
            print("    Database not detected. Initializing SQLite with seed data...")
            init_database()
        else:
            print(f"    Connected at: {DB_PATH}")

    app = create_app()

    print("\n[+] Web Application Server is starting...")
    print("    URL: http://127.0.0.1:5000")
    print("    Demo Account: rahul@pocketwise.io | Password: student123")
    print("    Press Ctrl+C to stop the server.\n")

    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)

if __name__ == "__main__":
    main()
