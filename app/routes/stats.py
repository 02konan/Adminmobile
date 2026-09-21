from flask import Blueprint, render_template

from ..auth import login_required
from ..db import query

stats_bp = Blueprint("stats", __name__, url_prefix="/stats")


@stats_bp.route("/")
@login_required
def index():
    orders_by_status = query(
        """
        SELECT status, COUNT(*) AS n, COALESCE(SUM(total),0) AS total
        FROM orders GROUP BY status
        """
    )
    deliveries_by_status = query(
        "SELECT status, COUNT(*) AS n FROM deliveries GROUP BY status"
    )
    revenue_by_shop = query(
        """
        SELECT s.name AS shop_name, COUNT(o.id) AS orders,
               COALESCE(SUM(o.total),0) AS revenue
        FROM shops s
        LEFT JOIN orders o ON o.shop_id = s.id AND o.status = 'delivered'
        GROUP BY s.id, s.name
        ORDER BY revenue DESC
        LIMIT 8
        """
    )
    top_products = query(
        """
        SELECT p.name, s.name AS shop_name,
               COALESCE(SUM(oi.quantity),0) AS sold
        FROM order_items oi
        JOIN products p ON p.id = oi.product_id
        LEFT JOIN shops s ON s.id = p.shop_id
        GROUP BY p.id, p.name, s.name
        ORDER BY sold DESC
        LIMIT 8
        """
    )
    top_drivers = query(
        """
        SELECT u.name AS driver_name,
               SUM(CASE WHEN d.status = 'delivered' THEN 1 ELSE 0 END) AS delivered,
               COUNT(d.id) AS total
        FROM users u
        LEFT JOIN deliveries d ON d.driver_id = u.id
        WHERE u.role = 'driver'
        GROUP BY u.id, u.name
        ORDER BY delivered DESC
        LIMIT 8
        """
    )

    totals = {
        "revenue": query(
            "SELECT COALESCE(SUM(total),0) AS t FROM orders WHERE status = 'delivered'",
            fetchone=True,
        )["t"],
        "delivered": query(
            "SELECT COUNT(*) AS n FROM orders WHERE status = 'delivered'",
            fetchone=True,
        )["n"],
        "shops": query("SELECT COUNT(*) AS n FROM shops", fetchone=True)["n"],
        "drivers": query(
            "SELECT COUNT(*) AS n FROM users WHERE role = 'driver'", fetchone=True
        )["n"],
    }

    return render_template(
        "stats.html",
        orders_by_status=orders_by_status,
        deliveries_by_status=deliveries_by_status,
        revenue_by_shop=revenue_by_shop,
        top_products=top_products,
        top_drivers=top_drivers,
        totals=totals,
    )
