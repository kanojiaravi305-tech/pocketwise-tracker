"""
backend/models/mongo_models.py
MongoDB Data Access Objects (DAO) implementing Repository Pattern.
Matches identical API contracts as SQLite models for seamless switching.
Compatible with both Local MongoDB and MongoDB Atlas (Cloud).
"""

import datetime
from bson import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from backend.config.mongodb import get_mongo_db

def _to_obj_id(val):
    if isinstance(val, ObjectId):
        return val
    try:
        return ObjectId(str(val))
    except Exception:
        return val

class MongoUserModel:
    @staticmethod
    def get_by_id(user_id):
        db = get_mongo_db()
        doc = None
        try:
            doc = db.users.find_one({"_id": _to_obj_id(user_id)})
        except Exception:
            pass
        if not doc:
            doc = db.users.find_one({"email": "rahul@pocketwise.io"}) or db.users.find_one({})
        if not doc:
            return None
        return {
            "user_id": str(doc["_id"]),
            "full_name": doc.get("full_name", ""),
            "email": doc.get("email", ""),
            "monthly_budget_limit": float(doc.get("monthly_budget_limit", 50000.0)),
            "created_at": doc.get("created_at"),
        }

    @staticmethod
    def get_by_email(email):
        db = get_mongo_db()
        doc = db.users.find_one({"email": email.strip().lower()})
        if not doc:
            return None
        return {
            "user_id": str(doc["_id"]),
            "full_name": doc.get("full_name", ""),
            "email": doc.get("email", ""),
            "password_hash": doc.get("password_hash", ""),
            "monthly_budget_limit": float(doc.get("monthly_budget_limit", 50000.0)),
        }

    @staticmethod
    def create(full_name, email, password, monthly_budget_limit=50000.0):
        db = get_mongo_db()
        res = db.users.insert_one({
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "password_hash": generate_password_hash(password),
            "monthly_budget_limit": float(monthly_budget_limit),
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
        return str(res.inserted_id)

    @staticmethod
    def update_budget_limit(user_id, new_limit):
        db = get_mongo_db()
        res = db.users.update_one(
            {"_id": _to_obj_id(user_id)},
            {"$set": {"monthly_budget_limit": float(new_limit)}},
        )
        return res.modified_count > 0

    @staticmethod
    def verify_password(stored_hash, candidate_password):
        return check_password_hash(stored_hash, candidate_password)

class MongoCategoryModel:
    @staticmethod
    def get_all():
        db = get_mongo_db()
        docs = db.categories.find().sort("category_name", 1)
        return [
            {
                "category_id": str(d["_id"]),
                "category_name": d["category_name"],
                "icon_name": d.get("icon_name", "bi-tag"),
                "color_code": d.get("color_code", "#0d6efd"),
                "monthly_limit": float(d.get("monthly_limit", 1500.0)),
            }
            for d in docs
        ]

    @staticmethod
    def get_by_id(category_id):
        db = get_mongo_db()
        d = db.categories.find_one({"_id": _to_obj_id(category_id)})
        if not d:
            return None
        return {
            "category_id": str(d["_id"]),
            "category_name": d["category_name"],
            "icon_name": d.get("icon_name", "bi-tag"),
            "color_code": d.get("color_code", "#0d6efd"),
            "monthly_limit": float(d.get("monthly_limit", 1500.0)),
        }

    @staticmethod
    def update_limit(category_id, new_limit):
        db = get_mongo_db()
        res = db.categories.update_one(
            {"_id": _to_obj_id(category_id)},
            {"$set": {"monthly_limit": float(new_limit)}},
        )
        return res.matched_count > 0

    @staticmethod
    def get_spending_with_limits(user_id, year_month):
        """
        Uses MongoDB Aggregation Pipeline to compute category spending
        versus monthly limits for the specified YYYY-MM.
        """
        db = get_mongo_db()
        categories = list(db.categories.find())
        
        # Aggregate expenses by category for current user and month
        pipeline = [
            {
                "$match": {
                    "user_id": _to_obj_id(user_id),
                    "expense_date": {"$regex": f"^{year_month}"}
                }
            },
            {
                "$group": {
                    "_id": "$category_id",
                    "total_spent": {"$sum": "$amount"}
                }
            }
        ]
        spending_map = {str(item["_id"]): float(item["total_spent"]) for item in db.expenses.aggregate(pipeline)}

        items = []
        for c in categories:
            cid_str = str(c["_id"])
            spent = spending_map.get(cid_str, 0.0)
            limit = float(c.get("monthly_limit", 1000.0))
            pct = round((spent / limit * 100.0), 1) if limit > 0 else 0.0
            items.append({
                "category_id": cid_str,
                "category_name": c["category_name"],
                "icon_name": c.get("icon_name", "bi-tag"),
                "color_code": c.get("color_code", "#0d6efd"),
                "monthly_limit": limit,
                "spent_amount": spent,
                "percent_used": pct,
            })

        items.sort(key=lambda x: x["spent_amount"], reverse=True)
        return items

class MongoExpenseModel:
    @staticmethod
    def _build_filter(user_id, month=None, category_id=None, payment_mode=None, search=None):
        query = {"user_id": _to_obj_id(user_id)}
        if month:
            query["expense_date"] = {"$regex": f"^{month}"}
        if category_id:
            query["category_id"] = _to_obj_id(category_id)
        if payment_mode:
            query["payment_mode"] = payment_mode
        if search:
            query["$or"] = [
                {"title": {"$regex": search.strip(), "$options": "i"}},
                {"notes": {"$regex": search.strip(), "$options": "i"}},
            ]
        return query

    @staticmethod
    def get_filtered(user_id, month=None, category_id=None, payment_mode=None, search=None, limit=None, offset=None):
        db = get_mongo_db()
        q = MongoExpenseModel._build_filter(user_id, month, category_id, payment_mode, search)
        cursor = db.expenses.find(q).sort([("expense_date", -1), ("_id", -1)])
        if offset is not None:
            cursor = cursor.skip(int(offset))
        if limit is not None:
            cursor = cursor.limit(int(limit))

        results = []
        for d in cursor:
            results.append({
                "expense_id": str(d["_id"]),
                "category_id": str(d.get("category_id", "")),
                "category_name": d.get("category_name", ""),
                "icon_name": d.get("icon_name", "bi-tag"),
                "color_code": d.get("color_code", "#0d6efd"),
                "title": d.get("title", ""),
                "amount": float(d.get("amount", 0.0)),
                "payment_mode": d.get("payment_mode", "UPI"),
                "expense_date": d.get("expense_date", ""),
                "notes": d.get("notes", ""),
                "created_at": d.get("created_at"),
            })
        return results

    @staticmethod
    def count_filtered(user_id, month=None, category_id=None, payment_mode=None, search=None):
        db = get_mongo_db()
        q = MongoExpenseModel._build_filter(user_id, month, category_id, payment_mode, search)
        return db.expenses.count_documents(q)

    @staticmethod
    def get_by_id(expense_id, user_id):
        db = get_mongo_db()
        d = db.expenses.find_one({"_id": _to_obj_id(expense_id), "user_id": _to_obj_id(user_id)})
        if not d:
            return None
        return {
            "expense_id": str(d["_id"]),
            "category_id": str(d.get("category_id", "")),
            "category_name": d.get("category_name", ""),
            "title": d.get("title", ""),
            "amount": float(d.get("amount", 0.0)),
            "payment_mode": d.get("payment_mode", "UPI"),
            "expense_date": d.get("expense_date", ""),
            "notes": d.get("notes", ""),
        }

    @staticmethod
    def create(user_id, category_id, title, amount, payment_mode, expense_date, notes=""):
        db = get_mongo_db()
        cat = db.categories.find_one({"_id": _to_obj_id(category_id)})
        cat_name = cat["category_name"] if cat else "General"
        icon_name = cat.get("icon_name", "bi-tag") if cat else "bi-tag"
        color_code = cat.get("color_code", "#0d6efd") if cat else "#0d6efd"

        res = db.expenses.insert_one({
            "user_id": _to_obj_id(user_id),
            "category_id": _to_obj_id(category_id),
            "category_name": cat_name,
            "icon_name": icon_name,
            "color_code": color_code,
            "title": title.strip(),
            "amount": float(amount),
            "payment_mode": payment_mode,
            "expense_date": expense_date,
            "notes": notes.strip() if notes else "",
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
        return str(res.inserted_id)

    @staticmethod
    def update(expense_id, user_id, category_id, title, amount, payment_mode, expense_date, notes=""):
        db = get_mongo_db()
        cat = db.categories.find_one({"_id": _to_obj_id(category_id)})
        cat_name = cat["category_name"] if cat else "General"
        icon_name = cat.get("icon_name", "bi-tag") if cat else "bi-tag"
        color_code = cat.get("color_code", "#0d6efd") if cat else "#0d6efd"

        res = db.expenses.update_one(
            {"_id": _to_obj_id(expense_id), "user_id": _to_obj_id(user_id)},
            {"$set": {
                "category_id": _to_obj_id(category_id),
                "category_name": cat_name,
                "icon_name": icon_name,
                "color_code": color_code,
                "title": title.strip(),
                "amount": float(amount),
                "payment_mode": payment_mode,
                "expense_date": expense_date,
                "notes": notes.strip() if notes else "",
            }}
        )
        return res.matched_count > 0

    @staticmethod
    def delete(expense_id, user_id):
        db = get_mongo_db()
        eid = _to_obj_id(expense_id)
        res = db.expenses.delete_one({"_id": eid, "user_id": _to_obj_id(user_id)})
        if res.deleted_count > 0:
            # Cascade delete associated splits
            db.split_records.delete_many({"expense_id": eid})
            return True
        return False

    @staticmethod
    def get_monthly_total(user_id, year_month):
        db = get_mongo_db()
        pipeline = [
            {"$match": {"user_id": _to_obj_id(user_id), "expense_date": {"$regex": f"^{year_month}"}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}}
        ]
        docs = list(db.expenses.aggregate(pipeline))
        return float(docs[0]["total"]) if docs else 0.0

    @staticmethod
    def get_category_breakdown(user_id, year_month):
        db = get_mongo_db()
        pipeline = [
            {"$match": {"user_id": _to_obj_id(user_id), "expense_date": {"$regex": f"^{year_month}"}}},
            {"$group": {
                "_id": "$category_name",
                "total_amount": {"$sum": "$amount"},
                "color_code": {"$first": "$color_code"},
                "icon_name": {"$first": "$icon_name"}
            }},
            {"$sort": {"total_amount": -1}}
        ]
        return [
            {
                "category_name": d["_id"],
                "total_amount": float(d["total_amount"]),
                "color_code": d.get("color_code", "#0d6efd"),
                "icon_name": d.get("icon_name", "bi-tag"),
            }
            for d in db.expenses.aggregate(pipeline)
        ]

    @staticmethod
    def get_six_months_trend(user_id):
        db = get_mongo_db()
        pipeline = [
            {"$match": {"user_id": _to_obj_id(user_id)}},
            {"$project": {
                "month_key": {"$substr": ["$expense_date", 0, 7]},
                "amount": "$amount"
            }},
            {"$group": {
                "_id": "$month_key",
                "total_amount": {"$sum": "$amount"}
            }},
            {"$sort": {"_id": 1}}
        ]
        return [
            {"month_key": d["_id"], "total_amount": float(d["total_amount"])}
            for d in db.expenses.aggregate(pipeline)
        ]

    @staticmethod
    def get_category_monthly_averages(user_id, exclude_month=None):
        db = get_mongo_db()
        match_q = {"user_id": _to_obj_id(user_id)}
        if exclude_month:
            match_q["expense_date"] = {"$not": {"$regex": f"^{exclude_month}"}}
        pipeline = [
            {"$match": match_q},
            {"$project": {
                "category_id": "$category_id",
                "category_name": "$category_name",
                "amount": "$amount",
                "month_key": {"$substr": ["$expense_date", 0, 7]}
            }},
            {"$group": {
                "_id": {"category_id": "$category_id", "month_key": "$month_key"},
                "category_name": {"$first": "$category_name"},
                "month_total": {"$sum": "$amount"}
            }},
            {"$group": {
                "_id": "$_id.category_id",
                "category_name": {"$first": "$category_name"},
                "avg_monthly_spent": {"$avg": "$month_total"}
            }}
        ]
        return [
            {
                "category_id": str(d["_id"]),
                "category_name": d.get("category_name", ""),
                "avg_monthly_spent": float(d.get("avg_monthly_spent", 0.0))
            }
            for d in db.expenses.aggregate(pipeline)
        ]


class MongoSplitModel:
    @staticmethod
    def create_splits(expense_id, friend_splits):
        db = get_mongo_db()
        eid = _to_obj_id(expense_id)
        exp = db.expenses.find_one({"_id": eid})
        uid = exp["user_id"] if exp else None

        ids = []
        for name, amount in friend_splits:
            res = db.split_records.insert_one({
                "expense_id": eid,
                "user_id": uid,
                "friend_name": name.strip(),
                "amount_owed": float(amount),
                "is_settled": False,
                "settled_at": None,
                "created_at": datetime.datetime.now(datetime.timezone.utc),
            })
            ids.append(str(res.inserted_id))
        return ids

    @staticmethod
    def get_user_splits(user_id, status=None):
        db = get_mongo_db()
        uid = _to_obj_id(user_id)
        
        # Match splits where user_id matches or expense.user_id matches
        match_query = {"user_id": uid}
        if status == "pending":
            match_query["is_settled"] = False
        elif status == "settled":
            match_query["is_settled"] = True

        splits = list(db.split_records.find(match_query).sort([("is_settled", 1), ("created_at", -1)]))
        results = []
        for s in splits:
            exp = db.expenses.find_one({"_id": s["expense_id"]}) or {}
            results.append({
                "split_id": str(s["_id"]),
                "expense_id": str(s["expense_id"]),
                "friend_name": s["friend_name"],
                "amount_owed": float(s["amount_owed"]),
                "is_settled": 1 if s["is_settled"] else 0,
                "settled_at": s.get("settled_at"),
                "expense_title": exp.get("title", "Shared Expense"),
                "total_bill_amount": float(exp.get("amount", 0.0)),
                "expense_date": exp.get("expense_date", ""),
                "payment_mode": exp.get("payment_mode", "UPI"),
                "category_name": exp.get("category_name", "Food & Canteen"),
                "color_code": exp.get("color_code", "#0d6efd"),
                "icon_name": exp.get("icon_name", "bi-tag"),
            })
        return results

    @staticmethod
    def toggle_settle(split_id, user_id, is_settled):
        db = get_mongo_db()
        settled_bool = bool(int(is_settled) == 1)
        settled_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") if settled_bool else None
        res = db.split_records.update_one(
            {"_id": _to_obj_id(split_id), "user_id": _to_obj_id(user_id)},
            {"$set": {"is_settled": settled_bool, "settled_at": settled_time}}
        )
        return res.matched_count > 0

    @staticmethod
    def get_split_stats(user_id):
        db = get_mongo_db()
        uid = _to_obj_id(user_id)
        splits = list(db.split_records.find({"user_id": uid}))
        total_lent = sum(float(s["amount_owed"]) for s in splits)
        total_recovered = sum(float(s["amount_owed"]) for s in splits if s.get("is_settled"))
        total_pending = sum(float(s["amount_owed"]) for s in splits if not s.get("is_settled"))
        pending_count = sum(1 for s in splits if not s.get("is_settled"))

        return {
            "total_lent": total_lent,
            "total_recovered": total_recovered,
            "total_pending": total_pending,
            "total_records": len(splits),
            "pending_count": pending_count,
        }


# ==============================================================================
# RECURRING BILLS MODEL (MONGODB ATLAS)
# ==============================================================================
class MongoRecurringModel:
    @staticmethod
    def seed_defaults_if_empty(user_id):
        db = get_mongo_db()
        uid = _to_obj_id(user_id)
        if db.recurring_bills.count_documents({"user_id": uid}) == 0:
            cats = {c["category_name"]: c["_id"] for c in db.categories.find()}
            housing_id = cats.get("Housing & Rent")
            util_id = cats.get("Utilities & Bills (Electricity, Wi-Fi, Phone)")
            invest_id = cats.get("Investments & Savings")
            default_cat = list(cats.values())[0] if cats else None

            sample_bills = [
                {
                    "user_id": uid,
                    "title": "Flat Rent & Maintenance",
                    "amount": 15000.0,
                    "category_id": housing_id or default_cat,
                    "category_name": "Housing & Rent",
                    "icon_name": "bi-house-door-fill",
                    "due_day": 5,
                    "frequency": "Monthly",
                    "payment_mode": "Net Banking",
                    "notes": "Shared apartment rent transfer to landlord",
                    "last_paid_date": None,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "user_id": uid,
                    "title": "High-Speed Fiber Wi-Fi",
                    "amount": 999.0,
                    "category_id": util_id or default_cat,
                    "category_name": "Utilities & Bills (Electricity, Wi-Fi, Phone)",
                    "icon_name": "bi-wifi",
                    "due_day": 10,
                    "frequency": "Monthly",
                    "payment_mode": "UPI",
                    "notes": "Airtel Xstream 200 Mbps broadband",
                    "last_paid_date": None,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "user_id": uid,
                    "title": "Electricity & Power Bill",
                    "amount": 1850.0,
                    "category_id": util_id or default_cat,
                    "category_name": "Utilities & Bills (Electricity, Wi-Fi, Phone)",
                    "icon_name": "bi-lightning-charge-fill",
                    "due_day": 15,
                    "frequency": "Monthly",
                    "payment_mode": "UPI",
                    "notes": "State electricity board bill",
                    "last_paid_date": None,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "user_id": uid,
                    "title": "Nifty 50 Index Fund SIP",
                    "amount": 5000.0,
                    "category_id": invest_id or default_cat,
                    "category_name": "Investments & Savings",
                    "icon_name": "bi-graph-up-arrow",
                    "due_day": 1,
                    "frequency": "Monthly",
                    "payment_mode": "Net Banking",
                    "notes": "Automated monthly investment via Zerodha/Groww",
                    "last_paid_date": None,
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
            ]
            db.recurring_bills.insert_many(sample_bills)

    @staticmethod
    def get_all(user_id):
        db = get_mongo_db()
        uid = _to_obj_id(user_id)
        MongoRecurringModel.seed_defaults_if_empty(uid)
        
        today = datetime.date.today()
        current_year_month = today.strftime("%Y-%m")
        current_day = today.day

        bills = list(db.recurring_bills.find({"user_id": uid}).sort("due_day", 1))
        results = []
        for b in bills:
            last_paid = b.get("last_paid_date")
            is_paid = bool(last_paid and str(last_paid).startswith(current_year_month))
            due_day = int(b.get("due_day", 1))

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
                "bill_id": str(b["_id"]),
                "title": b.get("title", ""),
                "amount": float(b.get("amount", 0.0)),
                "category_id": str(b.get("category_id", "")),
                "category_name": b.get("category_name", "General"),
                "icon_name": b.get("icon_name", "bi-calendar-check"),
                "due_day": due_day,
                "frequency": b.get("frequency", "Monthly"),
                "payment_mode": b.get("payment_mode", "UPI"),
                "notes": b.get("notes", ""),
                "last_paid_date": last_paid,
                "is_paid": is_paid,
                "status": status,
                "status_color": status_color,
                "status_badge": status_badge,
            })
        return results

    @staticmethod
    def get_by_id(bill_id, user_id):
        db = get_mongo_db()
        doc = db.recurring_bills.find_one({"_id": _to_obj_id(bill_id), "user_id": _to_obj_id(user_id)})
        if not doc:
            return None
        return {
            "bill_id": str(doc["_id"]),
            "title": doc.get("title", ""),
            "amount": float(doc.get("amount", 0.0)),
            "category_id": str(doc.get("category_id", "")),
            "category_name": doc.get("category_name", ""),
            "icon_name": doc.get("icon_name", "bi-calendar-check"),
            "due_day": int(doc.get("due_day", 1)),
            "frequency": doc.get("frequency", "Monthly"),
            "payment_mode": doc.get("payment_mode", "UPI"),
            "notes": doc.get("notes", ""),
            "last_paid_date": doc.get("last_paid_date"),
        }

    @staticmethod
    def create(user_id, title, amount, category_id, due_day=1, frequency="Monthly", payment_mode="UPI", notes=""):
        db = get_mongo_db()
        cat = db.categories.find_one({"_id": _to_obj_id(category_id)})
        cat_name = cat["category_name"] if cat else "General"
        icon_name = cat.get("icon_name", "bi-calendar-check") if cat else "bi-calendar-check"

        res = db.recurring_bills.insert_one({
            "user_id": _to_obj_id(user_id),
            "title": title.strip(),
            "amount": float(amount),
            "category_id": _to_obj_id(category_id),
            "category_name": cat_name,
            "icon_name": icon_name,
            "due_day": int(due_day),
            "frequency": frequency,
            "payment_mode": payment_mode,
            "notes": notes.strip() if notes else "",
            "last_paid_date": None,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
        return str(res.inserted_id)

    @staticmethod
    def update(bill_id, user_id, title, amount, category_id, due_day=1, frequency="Monthly", payment_mode="UPI", notes=""):
        db = get_mongo_db()
        cat = db.categories.find_one({"_id": _to_obj_id(category_id)})
        cat_name = cat["category_name"] if cat else "General"
        icon_name = cat.get("icon_name", "bi-calendar-check") if cat else "bi-calendar-check"

        res = db.recurring_bills.update_one(
            {"_id": _to_obj_id(bill_id), "user_id": _to_obj_id(user_id)},
            {"$set": {
                "title": title.strip(),
                "amount": float(amount),
                "category_id": _to_obj_id(category_id),
                "category_name": cat_name,
                "icon_name": icon_name,
                "due_day": int(due_day),
                "frequency": frequency,
                "payment_mode": payment_mode,
                "notes": notes.strip() if notes else "",
            }}
        )
        return res.modified_count > 0

    @staticmethod
    def delete(bill_id, user_id):
        db = get_mongo_db()
        res = db.recurring_bills.delete_one({"_id": _to_obj_id(bill_id), "user_id": _to_obj_id(user_id)})
        return res.deleted_count > 0

    @staticmethod
    def mark_paid(bill_id, user_id):
        db = get_mongo_db()
        bill = db.recurring_bills.find_one({"_id": _to_obj_id(bill_id), "user_id": _to_obj_id(user_id)})
        if not bill:
            return None, "Recurring bill not found."

        today_str = datetime.date.today().isoformat()
        
        # 1. Log expense into expenses collection
        from backend.models.expense_model import ExpenseModel
        expense_id = ExpenseModel.create(
            user_id=user_id,
            category_id=str(bill["category_id"]),
            title=f"Bill: {bill['title']}",
            amount=float(bill["amount"]),
            payment_mode=bill.get("payment_mode", "UPI"),
            expense_date=today_str,
            notes=f"Monthly recurring bill payment for {bill['title']}"
        )

        # 2. Update last_paid_date in recurring_bills collection
        db.recurring_bills.update_one(
            {"_id": bill["_id"]},
            {"$set": {"last_paid_date": today_str}}
        )

        return str(expense_id), None


# ==============================================================================
# SAVINGS GOALS MODEL (MONGODB ATLAS)
# ==============================================================================
class MongoSavingsModel:
    @staticmethod
    def seed_defaults_if_empty(user_id):
        db = get_mongo_db()
        uid = _to_obj_id(user_id)
        if db.savings_goals.count_documents({"user_id": uid}) == 0:
            sample_goals = [
                {
                    "user_id": uid,
                    "title": "Emergency Fund (6 Months)",
                    "target_amount": 100000.0,
                    "current_amount": 65000.0,
                    "target_date": "2026-12-31",
                    "category_icon": "bi-shield-shaded",
                    "color_code": "#059669",
                    "notes": "Emergency safety reserve for unexpected expenses",
                    "history": [
                        {"amount": 25000.0, "date": "2026-08-01", "note": "Initial deposit"},
                        {"amount": 20000.0, "date": "2026-09-01", "note": "Monthly contribution"},
                        {"amount": 20000.0, "date": "2026-10-01", "note": "Bonus savings"},
                    ],
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "user_id": uid,
                    "title": "MacBook M-Series Upgrade",
                    "target_amount": 85000.0,
                    "current_amount": 42500.0,
                    "target_date": "2026-11-30",
                    "category_icon": "bi-laptop",
                    "color_code": "#0284c7",
                    "notes": "Workstation for development & freelancing",
                    "history": [
                        {"amount": 20000.0, "date": "2026-08-15", "note": "Freelance project payment"},
                        {"amount": 22500.0, "date": "2026-09-20", "note": "Savings allocation"},
                    ],
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "user_id": uid,
                    "title": "Annual Vacation & Travel",
                    "target_amount": 30000.0,
                    "current_amount": 18500.0,
                    "target_date": "2026-12-15",
                    "category_icon": "bi-airplane",
                    "color_code": "#7c3aed",
                    "notes": "Holiday trip with friends",
                    "history": [
                        {"amount": 10000.0, "date": "2026-09-05", "note": "Flight ticket fund"},
                        {"amount": 8500.0, "date": "2026-10-05", "note": "Hotel stay fund"},
                    ],
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
                {
                    "user_id": uid,
                    "title": "Certifications & Upskilling",
                    "target_amount": 15000.0,
                    "current_amount": 12000.0,
                    "target_date": "2026-11-15",
                    "category_icon": "bi-mortarboard",
                    "color_code": "#d97706",
                    "notes": "Cloud & Database Developer Certifications",
                    "history": [
                        {"amount": 6000.0, "date": "2026-08-20", "note": "Course voucher"},
                        {"amount": 6000.0, "date": "2026-09-10", "note": "Exam fee deposit"},
                    ],
                    "created_at": datetime.datetime.now(datetime.timezone.utc),
                },
            ]
            db.savings_goals.insert_many(sample_goals)

    @staticmethod
    def get_all(user_id):
        db = get_mongo_db()
        uid = _to_obj_id(user_id)
        MongoSavingsModel.seed_defaults_if_empty(uid)

        goals = list(db.savings_goals.find({"user_id": uid}).sort("target_date", 1))
        results = []
        today = datetime.date.today()

        for g in goals:
            target = float(g.get("target_amount", 0.0))
            current = float(g.get("current_amount", 0.0))
            pct = min(100.0, round((current / target * 100), 1)) if target > 0 else 0.0
            remaining = max(0.0, target - current)
            is_completed = current >= target

            target_date_str = g.get("target_date", "")
            days_left = None
            if target_date_str:
                try:
                    td = datetime.date.fromisoformat(target_date_str)
                    days_left = (td - today).days
                except Exception:
                    pass

            results.append({
                "goal_id": str(g["_id"]),
                "title": g.get("title", ""),
                "target_amount": target,
                "current_amount": current,
                "progress_percent": pct,
                "remaining_amount": remaining,
                "is_completed": is_completed,
                "target_date": target_date_str,
                "days_left": days_left,
                "category_icon": g.get("category_icon", "bi-piggy-bank"),
                "color_code": g.get("color_code", "#059669"),
                "notes": g.get("notes", ""),
                "history": g.get("history", []),
            })
        return results

    @staticmethod
    def get_by_id(goal_id, user_id):
        db = get_mongo_db()
        doc = db.savings_goals.find_one({"_id": _to_obj_id(goal_id), "user_id": _to_obj_id(user_id)})
        if not doc:
            return None
        target = float(doc.get("target_amount", 0.0))
        current = float(doc.get("current_amount", 0.0))
        return {
            "goal_id": str(doc["_id"]),
            "title": doc.get("title", ""),
            "target_amount": target,
            "current_amount": current,
            "progress_percent": min(100.0, round((current / target * 100), 1)) if target > 0 else 0.0,
            "remaining_amount": max(0.0, target - current),
            "target_date": doc.get("target_date", ""),
            "category_icon": doc.get("category_icon", "bi-piggy-bank"),
            "color_code": doc.get("color_code", "#059669"),
            "notes": doc.get("notes", ""),
            "history": doc.get("history", []),
        }

    @staticmethod
    def create(user_id, title, target_amount, current_amount=0.0, target_date="", category_icon="bi-piggy-bank", color_code="#059669", notes=""):
        db = get_mongo_db()
        init_amount = float(current_amount) if current_amount else 0.0
        history = []
        if init_amount > 0:
            history.append({
                "amount": init_amount,
                "date": datetime.date.today().isoformat(),
                "note": "Initial opening deposit"
            })

        res = db.savings_goals.insert_one({
            "user_id": _to_obj_id(user_id),
            "title": title.strip(),
            "target_amount": float(target_amount),
            "current_amount": init_amount,
            "target_date": target_date.strip() if target_date else "",
            "category_icon": category_icon,
            "color_code": color_code,
            "notes": notes.strip() if notes else "",
            "history": history,
            "created_at": datetime.datetime.now(datetime.timezone.utc),
        })
        return str(res.inserted_id)

    @staticmethod
    def add_funds(goal_id, user_id, amount, note="Manual deposit"):
        db = get_mongo_db()
        amt = float(amount)
        if amt <= 0:
            return False, "Amount must be greater than zero."

        record = {
            "amount": amt,
            "date": datetime.date.today().isoformat(),
            "note": note.strip() if note else "Contribution"
        }

        res = db.savings_goals.update_one(
            {"_id": _to_obj_id(goal_id), "user_id": _to_obj_id(user_id)},
            {
                "$inc": {"current_amount": amt},
                "$push": {"history": record}
            }
        )
        return res.modified_count > 0, None

    @staticmethod
    def update(goal_id, user_id, title, target_amount, target_date="", category_icon="bi-piggy-bank", color_code="#059669", notes=""):
        db = get_mongo_db()
        res = db.savings_goals.update_one(
            {"_id": _to_obj_id(goal_id), "user_id": _to_obj_id(user_id)},
            {"$set": {
                "title": title.strip(),
                "target_amount": float(target_amount),
                "target_date": target_date.strip() if target_date else "",
                "category_icon": category_icon,
                "color_code": color_code,
                "notes": notes.strip() if notes else "",
            }}
        )
        return res.modified_count > 0

    @staticmethod
    def delete(goal_id, user_id):
        db = get_mongo_db()
        res = db.savings_goals.delete_one({"_id": _to_obj_id(goal_id), "user_id": _to_obj_id(user_id)})
        return res.deleted_count > 0

