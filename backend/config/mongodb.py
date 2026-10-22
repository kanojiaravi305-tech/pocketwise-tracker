"""
backend/config/mongodb.py
MongoDB & MongoDB Atlas configuration and connection manager using PyMongo.
Supports both local MongoDB and MongoDB Atlas (Cloud) connection strings.
"""

import os
from pymongo import MongoClient
from urllib.parse import urlparse

# Default settings
DEFAULT_MONGO_URI = "mongodb://localhost:27017/student_expense_tracker"
DEFAULT_DB_NAME = "student_expense_tracker"

def load_env_variables():
    """Simple parser for .env file without external dependencies."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, ".env")
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip()
    return env_vars

ENV = load_env_variables()
MONGO_URI = os.environ.get("MONGO_URI", ENV.get("MONGO_URI", DEFAULT_MONGO_URI))
DB_ENGINE = os.environ.get("DB_ENGINE", ENV.get("DB_ENGINE", "mongodb")).lower()

_mongo_client = None

def get_mongo_client():
    """Returns singleton PyMongo client instance."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return _mongo_client

def get_mongo_db():
    """Returns active database instance for student expense tracker."""
    client = get_mongo_client()
    
    # Extract database name from URI if specified
    try:
        parsed = urlparse(MONGO_URI)
        db_name = parsed.path.lstrip("/")
        if not db_name or "?" in db_name:
            db_name = db_name.split("?")[0] if db_name else DEFAULT_DB_NAME
    except Exception:
        db_name = DEFAULT_DB_NAME

    if not db_name:
        db_name = DEFAULT_DB_NAME

    return client[db_name]

def is_atlas_connected():
    """Checks if the configured URI is an Atlas Cloud connection."""
    return "mongodb+srv" in MONGO_URI or "mongodb.net" in MONGO_URI
