# PocketWise: Personal Finance & Shared Expense Tracker

A practical, robust **Personal Finance & Expense Tracker** with an integrated **Shared Expenses & Group Bill Splitter** built for working professionals, freelancers, and everyday users. Designed using a classic **Monolithic 3-Tier Architecture** with a clean, standard human-built Bootstrap 5 light-mode UI and dual-engine persistence (SQLite / MongoDB Atlas).

---

## 1. Project Overview & Problem Statement

Working professionals, roommates, freelancers, and families often struggle to balance monthly income and budgets across diverse daily expenditures—such as apartment rent, groceries, utility bills, fuel, healthcare, and group activities. Existing commercial apps are often heavily over-engineered, cluttered with advertisements and social feeds, or require continuous paid subscriptions.

**PocketWise** provides:
1. **Personal Budget Discipline:** Automatic **80% warning** and **100% critical alert banners** when monthly limits are approached or breached.
2. **Visual Analytics:** Month-on-month 6-month trends and current month category breakdown powered by Chart.js.
3. **Shared Expenses & Group Split:** Flat equal-split calculator for team lunches, flat rent/utilities, group trips, and shared bills with 1-click settlement toggling.
4. **Smart Financial Advisor:** Real-time health score (0–100), 50/30/20 rule diagnostics, daily burn velocity, and an interactive "Can I Afford It?" purchase simulator.
5. **Financial Statement Export:** 1-click CSV download for budgeting reviews, tax records, or accounting.
6. **Dual-Engine Flexibility:** Seamlessly runs on embedded zero-config SQLite or MongoDB Atlas (Cloud NoSQL) via `.env`.

---

## 2. System Architecture (Classic 3-Tier Monolith)

The system strictly follows the classic **3-Tier Monolithic Architecture** and the **Model-View-Controller (MVC)** design pattern.

```text
[ Browser / Client Tier ]         [ Application / Logic Tier ]          [ Database Tier ]
+-----------------------+         +--------------------------+         +-----------------+
| HTML5 + Vanilla CSS   |         | Flask REST API Routes    |         | SQLite 3 RDBMS  |
| Bootstrap 5 (Offline) | <=====> | Controllers (Auth/CRUD)  | <=====> | OR MongoDB      |
| Vanilla JS + Chart.js | (JSON)  | Repository Model Pattern | (DAO)   | Atlas Cloud     |
| Clean Light UI        |         | Session Auth (Werkzeug)  |         | (via .env)      |
+-----------------------+         +--------------------------+         +-----------------+
```

---

## 3. Universal Expense Categories (8 Core Domains)

1. **Housing & Rent**: Apartment monthly lease, society maintenance, home repair.
2. **Groceries & Dining**: Supermarket provisions, weekly restock, dining out, cafes.
3. **Commute & Fuel**: Petrol/diesel refills, metro transit cards, cab fares, tolls.
4. **Utilities & Bills**: Electricity, broadband Wi-Fi, mobile postpaid, piped gas, water.
5. **Shopping & Lifestyle**: Apparel, ergonomic home workspace equipment, electronics.
6. **Healthcare & Fitness**: Gym memberships, pharmacy, health insurance, diagnostics.
7. **Investments & Savings**: Mutual fund SIPs, index funds, emergency fund deposits.
8. **Miscellaneous**: Hardware repairs, contingencies, filter replacements.

---

## 4. Getting Started & Running Locally

### Step 1: Install Requirements
```bash
pip install -r requirements.txt
```

### Step 2: Database Configuration (`.env`)
By default, PocketWise is configured to run on **SQLite**:
```ini
DB_ENGINE=sqlite
```
*(To switch to MongoDB Atlas Cloud, set `DB_ENGINE=mongodb` and provide your `MONGO_URI`)*

### Step 3: Initialize Database & Seed Dummy Data
```bash
python database/init_db.py
```

### Step 4: Run the Application Server
```bash
python run.py
```
Open **`http://127.0.0.1:5000`** in your browser.

* **Standard Login:** `rahul@pocketwise.io` / `student123`
* **Google Sign-In:** Click the official **"Continue with Google"** button on the sign-in screen to authenticate instantly.


---

## 5. Practical AI & Predictive Capabilities (Viva Reference)

1. **Natural Language "Quick-Add" Expense Parser:**
   - Input sentence like *"Spent 650 on Swiggy via UPI"* or *"Paid 1800 for Electricity Bill via Net Banking"*.
   - Uses RegEx pattern extraction for amount and payment mode, stopword stripping for title extraction, and scored synonym keyword matching across 8 universal categories.
   - Logs expense immediately with zero external dependencies.

2. **Next Month Spend Prediction (Linear Regression & WMA):**
   - Applies Simple Linear Regression ($y = mx + c$) over historical monthly totals.
   - Computes 3-Month Weighted Moving Average ($WMA = \frac{3y_N + 2y_{N-1} + y_{N-2}}{6}$).
   - Displays projected next month spend and MoM percentage trend.

3. **Statistical Anomaly Detection (>25% Spike):**
   - Compares current month spending in each category against the user's historical average.
   - Automatically flags any category where expenditure has surged $>25\%$ higher than normal.

4. **Hybrid Smart Financial Audit:**
   - **Online Path:** Sends privacy-safe aggregated summary numbers to Google's Gemini 2.5 Flash API if `GEMINI_API_KEY` is provided.
   - **Offline Fallback:** If offline or without an API key, automatically generates 3 tailored, professional audit points using a local Python rule engine so the viva demo never crashes.

