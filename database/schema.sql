-- ====================================================================
-- Database Schema for PocketWise: Personal & Shared Expense Tracker
-- Classic 3-Tier Architecture (RDBMS Data Tier)
-- 4 Normalized Tables with Foreign Key Constraints
-- ====================================================================

PRAGMA foreign_keys = ON;

-- 1. USERS TABLE
DROP TABLE IF EXISTS split_records;
DROP TABLE IF EXISTS expenses;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    monthly_budget_limit REAL NOT NULL DEFAULT 50000.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. CATEGORIES TABLE
CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE,
    icon_name TEXT NOT NULL DEFAULT 'bi-tag',
    color_code TEXT NOT NULL DEFAULT '#0d6efd',
    monthly_limit REAL NOT NULL DEFAULT 5000.0
);

-- 3. EXPENSES TABLE
CREATE TABLE expenses (
    expense_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    amount REAL NOT NULL,
    payment_mode TEXT NOT NULL CHECK(payment_mode IN ('UPI', 'Cash', 'Card', 'Net Banking')),
    expense_date DATE NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

-- 4. SPLIT RECORDS TABLE (Shared Expenses & Group Splitter)
CREATE TABLE split_records (
    split_id INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id INTEGER NOT NULL,
    friend_name TEXT NOT NULL,
    amount_owed REAL NOT NULL,
    is_settled INTEGER NOT NULL DEFAULT 0 CHECK(is_settled IN (0, 1)),
    settled_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (expense_id) REFERENCES expenses (expense_id) ON DELETE CASCADE
);

-- Performance Indexes for search & filtering
CREATE INDEX idx_expenses_user_date ON expenses (user_id, expense_date);
CREATE INDEX idx_expenses_category ON expenses (category_id);
CREATE INDEX idx_split_expense ON split_records (expense_id);

