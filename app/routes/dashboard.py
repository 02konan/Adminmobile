from flask import Blueprint, render_template

from ..auth import login_required
from ..db import query

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    stats = {
        "products": query("SELECT COUNT(*) AS n FROM products", fetchone=True)["n"],
        "categories": query("SELECT COUNT(*) AS n FROM categories", fetchone=True)["n"],
        "orders": query("SELECT COUNT(*) AS n FROM orders", fetchone=True)["n"],
        "users": query("SELECT COUNT(*) AS n FROM users", fetchone=True)["n"],
        "revenue": query(
            "SELECT COALESCE(SUM(total), 0) AS total FROM orders", fetchone=True
        )["total"],
        "low_stock": query(
            "SELECT COUNT(*) AS n FROM products WHERE stock <= 5", fetchone=True
        )["n"],
    }

    recent_orders = query(
        """
        SELECT o.id, o.order_number, o.total, o.status, o.created_at, u.name AS user_name
        FROM orders o
        JOIN users u ON u.id = o.user_id
        ORDER BY o.created_at DESC
        LIMIT 5
        """
    )

    return render_template("dashboard.html", stats=stats, recent_orders=recent_orders)
