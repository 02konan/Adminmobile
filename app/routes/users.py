from flask import Blueprint, render_template

from ..auth import login_required
from ..db import query

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/")
@login_required
def list_users():
    users = query(
        """
        SELECT u.*, COUNT(o.id) AS order_count, COALESCE(SUM(o.total), 0) AS total_spent
        FROM users u
        LEFT JOIN orders o ON o.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    )
    return render_template("users/list.html", users=users)
