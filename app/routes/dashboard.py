from flask import Blueprint, render_template

from ..auth import login_required
from ..db import query

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    def count(sql):
        return query(sql, fetchone=True)["n"]

    stats = {
        "products": count("SELECT COUNT(*) AS n FROM products"),
        "orders": count("SELECT COUNT(*) AS n FROM orders"),
        "users": count("SELECT COUNT(*) AS n FROM users"),
        "revenue": query(
            "SELECT COALESCE(SUM(total), 0) AS total FROM orders "
            "WHERE status = 'delivered'",
            fetchone=True,
        )["total"],
        "shops": count("SELECT COUNT(*) AS n FROM shops"),
        "pending_shops": count(
            "SELECT COUNT(*) AS n FROM shops WHERE status = 'pending'"
        ),
        "live_now": count("SELECT COUNT(*) AS n FROM lives WHERE status = 'live'"),
        "drivers": count("SELECT COUNT(*) AS n FROM users WHERE role = 'driver'"),
        "active_deliveries": count(
            "SELECT COUNT(*) AS n FROM deliveries "
            "WHERE status IN ('assigned','picked_up','delivering')"
        ),
        "open_reports": count(
            "SELECT COUNT(*) AS n FROM reports WHERE status = 'open'"
        ),
        "low_stock": count("SELECT COUNT(*) AS n FROM products WHERE stock <= 5"),
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
