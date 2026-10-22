"""
backend/config/db.py
Database connection configuration and helper functions.
Ensures SQLite foreign key constraints are strictly enforced.
"""

import os
import sqlite3
from flask import g

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "database", "expenses.db")

def get_db():
    """
    Returns a thread-safe connection from Flask's request context 'g'.
    Configures Row factory for dictionary-like column access.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

def close_db(e=None):
    """Closes database connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False):
    """
    Convenience helper to execute SQL queries with parameterized inputs.
    Prevents SQL injection vulnerabilities.
    """
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def execute_db(query, args=()):
    """
    Convenience helper to execute INSERT, UPDATE, DELETE queries.
    Returns the lastrowid and rowcount.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute(query, args)
    db.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    return last_id, row_count
