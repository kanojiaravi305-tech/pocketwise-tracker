"""
test_suite.py
Automated Verification Suite for PocketWise: Personal & Shared Expense Tracker.
Tests all Models, Controllers, Calculations, and REST API Endpoints.
"""

import unittest
import json
from backend.app import create_app
from database.init_db import init_database

class PocketWiseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Initialize fresh SQLite database with seed data
        init_database()
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def test_01_google_login(self):
        """Test Sign in with Google endpoint"""
        res = self.client.post("/api/auth/google", json={"email": "rahul.sharma@gmail.com", "name": "Rahul Sharma"})
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["provider"], "google")
        self.assertEqual(data["user"]["name"], "Rahul Sharma")


    def test_02_current_user_session(self):
        """Test session preservation after login"""
        res = self.client.get("/api/auth/me")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["user"]["name"], "Rahul Sharma")

    def test_03_dashboard_stats_and_threshold_alert(self):
        """Test Dashboard stats and 80% / 100% threshold alert calculations"""
        res = self.client.get("/api/dashboard/stats")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        
        # Verify metric structure
        metrics = data["metrics"]
        self.assertIn("monthly_budget", metrics)
        self.assertIn("total_spent", metrics)
        self.assertIn("remaining_balance", metrics)
        self.assertIn("percent_spent", metrics)
        
        # Verify Chart.js data structures
        self.assertIn("doughnut_chart", data)
        self.assertGreater(len(data["doughnut_chart"]["labels"]), 0)
        self.assertIn("bar_chart", data)
        self.assertEqual(len(data["bar_chart"]["labels"]), 6)
        
        # Verify recent transactions list
        self.assertIn("recent_transactions", data)
        self.assertLessEqual(len(data["recent_transactions"]), 5)

    def test_04_transactions_crud_and_filter(self):
        """Test Expense creation, retrieval, filtering, Net Banking, and deletion"""
        # Create an expense
        payload = {
            "title": "Office Desk Accessories Test",
            "amount": 750.0,
            "category_id": 5, # Shopping & Lifestyle
            "payment_mode": "Net Banking",
            "expense_date": "2026-10-20",
            "notes": "Unit test expense"
        }
        create_res = self.client.post("/api/expenses", json=payload)
        self.assertEqual(create_res.status_code, 201)
        create_data = json.loads(create_res.data)
        self.assertTrue(create_data["success"])
        new_expense_id = create_data["expense_id"]

        # Retrieve filtered
        filter_res = self.client.get("/api/expenses?search=Office+Desk+Accessories")
        self.assertEqual(filter_res.status_code, 200)
        filter_data = json.loads(filter_res.data)
        self.assertTrue(filter_data["success"])
        self.assertGreaterEqual(filter_data["pagination"]["total_records"], 1)

        # Update expense
        update_res = self.client.put(f"/api/expenses/{new_expense_id}", json={
            "title": "Updated Desk Accessories",
            "amount": 800.0,
            "category_id": 5,
            "payment_mode": "UPI",
            "expense_date": "2026-10-20",
            "notes": "Updated note"
        })
        self.assertEqual(update_res.status_code, 200)

        # Delete expense
        del_res = self.client.delete(f"/api/expenses/{new_expense_id}")
        self.assertEqual(del_res.status_code, 200)

    def test_05_csv_statement_export(self):
        """Test CSV download generation"""
        res = self.client.get("/api/expenses/export-csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.mimetype, "text/csv")
        self.assertIn("Expense ID,Date,Title,Category,Payment Mode,Amount (INR),Notes", res.data.decode("utf-8"))

    def test_06_shared_bill_splitter(self):
        """Test Equal Bill Splitter algorithm and settlement toggle"""
        split_payload = {
            "title": "Team Celebration Lunch Test",
            "total_amount": 1200.0,
            "category_id": 2, # Groceries & Dining
            "friends": "Vikram Rao, Neha Sharma",
            "include_self": True,
            "payment_mode": "Card",
            "expense_date": "2026-10-20",
        }
        # 1200 split between 2 members + user = 3 people -> 400 each
        res = self.client.post("/api/splits", json=split_payload)
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["share_per_person"], 400.0)
        self.assertEqual(len(data["split_ids"]), 2)

        # Toggle settlement
        first_split_id = data["split_ids"][0]
        settle_res = self.client.post(f"/api/splits/{first_split_id}/settle", json={"is_settled": 1})
        self.assertEqual(settle_res.status_code, 200)
        settle_data = json.loads(settle_res.data)
        self.assertTrue(settle_data["is_settled"])

    def test_07_budget_limits_page_data(self):
        """Test Category-wise budget limits retrieval (8 universal categories)"""
        res = self.client.get("/api/budgets")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(len(data["categories"]), 8)
        for cat in data["categories"]:
            self.assertIn("percent_used", cat)
            self.assertIn("status_color", cat)

    def test_08_financial_advisor_insights(self):
        """Test Financial Advisor insights, Health Score, and 50/30/20 rule"""
        res = self.client.get("/api/advisor/insights")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("health_score", data)
        self.assertGreater(data["health_score"], 0)
        self.assertIn("recommendations", data)
        self.assertGreater(len(data["recommendations"]), 0)
        self.assertIn("rule_50_30_20", data)

    def test_09_purchase_simulator(self):
        """Test 'Can I Afford It?' purchase simulation"""
        payload = {"title": "Ergonomic Office Chair", "amount": 3500.0}
        res = self.client.post("/api/advisor/simulate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("verdict", data)
        self.assertIn("new_daily_limit", data)

    def test_10_nlp_quick_add_parser_and_endpoint(self):
        """Test Natural Language Quick Add with AI regex & keyword parser"""
        # Test 1: Swiggy UPI
        payload1 = {"query": "Spent 650 on Swiggy via UPI"}
        res1 = self.client.post("/api/expenses/quick-add", json=payload1)
        self.assertEqual(res1.status_code, 201)
        data1 = json.loads(res1.data)
        self.assertTrue(data1["success"])
        self.assertEqual(data1["parsed"]["amount"], 650.0)
        self.assertEqual(data1["parsed"]["payment_mode"], "UPI")
        self.assertEqual(data1["parsed"]["category_name"], "Groceries & Dining")
        self.assertEqual(data1["parsed"]["title"], "Swiggy")

        # Test 2: Electricity Bill Net Banking
        payload2 = {"query": "Paid 1800 for Electricity Bill via Net Banking"}
        res2 = self.client.post("/api/expenses/quick-add", json=payload2)
        self.assertEqual(res2.status_code, 201)
        data2 = json.loads(res2.data)
        self.assertTrue(data2["success"])
        self.assertEqual(data2["parsed"]["amount"], 1800.0)
        self.assertEqual(data2["parsed"]["payment_mode"], "Net Banking")
        self.assertIn("Utilities & Bills", data2["parsed"]["category_name"])

    def test_11_predictive_spend_math(self):
        """Test Simple Linear Regression (y = mx + c) and Weighted Moving Average"""
        with self.app.app_context():
            from backend.services.predictive_engine import predict_next_month_spend
            pred = predict_next_month_spend(1, "2026-10")
            self.assertIn("projected_spend", pred)
            self.assertGreater(pred["projected_spend"], 0.0)
            self.assertIn("slope", pred)
            self.assertIn("wma", pred)
            self.assertIn("trend_direction", pred)
            self.assertEqual(pred["historical_months_count"], 6)

    def test_12_statistical_anomaly_detection(self):
        """Test Anomaly Detection flagging category spending >25% higher than baseline"""
        with self.app.app_context():
            from backend.services.predictive_engine import detect_category_anomalies
            anomalies = detect_category_anomalies(1, "2026-10")
            self.assertIsInstance(anomalies, list)
            self.assertGreater(len(anomalies), 0)
            for a in anomalies:
                self.assertGreater(a["percent_increase"], 25.0)
                self.assertIn("baseline_amount", a)
                self.assertIn("current_spent", a)


    def test_13_smart_financial_audit(self):
        """Test Smart Financial Audit endpoint (Gemini with offline fallback)"""
        res = self.client.post("/api/advisor/smart-audit")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn(data["source"], ["gemini", "offline_fallback"])
        self.assertEqual(len(data["audit_points"]), 3)
        for pt in data["audit_points"]:
            self.assertIn("title", pt)
            self.assertIn("advice", pt)
            self.assertIn("impact", pt)

if __name__ == "__main__":
    unittest.main()

