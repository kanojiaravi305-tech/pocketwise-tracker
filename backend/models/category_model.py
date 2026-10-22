"""
backend/models/category_model.py
Data Access Object (DAO) for categories table and category-budget metrics.
"""

from backend.config.mongodb import DB_ENGINE
from backend.config.db import query_db, execute_db

class CategoryModel:
    @staticmethod
    def get_all():
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoCategoryModel
            return MongoCategoryModel.get_all()
        return query_db(
            "SELECT category_id, category_name, icon_name, color_code, monthly_limit FROM categories ORDER BY category_id ASC;"
        )

    @staticmethod
    def get_by_id(category_id):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoCategoryModel
            return MongoCategoryModel.get_by_id(category_id)
        return query_db(
            "SELECT category_id, category_name, icon_name, color_code, monthly_limit FROM categories WHERE category_id = ?;",
            (category_id,),
            one=True,
        )

    @staticmethod
    def update_limit(category_id, new_limit):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoCategoryModel
            return MongoCategoryModel.update_limit(category_id, new_limit)
        _, rowcount = execute_db(
            "UPDATE categories SET monthly_limit = ? WHERE category_id = ?;",
            (float(new_limit), category_id),
        )
        return rowcount > 0

    @staticmethod
    def get_spending_with_limits(user_id, year_month):
        if DB_ENGINE == "mongodb":
            from backend.models.mongo_models import MongoCategoryModel
            return MongoCategoryModel.get_spending_with_limits(user_id, year_month)
        sql = """
            SELECT 
                c.category_id,
                c.category_name,
                c.icon_name,
                c.color_code,
                c.monthly_limit,
                COALESCE(SUM(e.amount), 0.0) AS spent_amount,
                ROUND(
                    CASE 
                        WHEN c.monthly_limit > 0 THEN (COALESCE(SUM(e.amount), 0.0) / c.monthly_limit) * 100.0
                        ELSE 0.0 
                    END, 1
                ) AS percent_used
            FROM categories c
            LEFT JOIN expenses e ON c.category_id = e.category_id 
                AND e.user_id = ? 
                AND strftime('%Y-%m', e.expense_date) = ?
            GROUP BY c.category_id, c.category_name, c.icon_name, c.color_code, c.monthly_limit
            ORDER BY spent_amount DESC;
        """
        return query_db(sql, (user_id, year_month))
