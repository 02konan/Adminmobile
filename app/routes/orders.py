from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")

VALID_STATUSES = ("processing", "shipped", "delivered")


@orders_bp.route("/")
@login_required
def list_orders():
    status = request.args.get("status", "").strip()

    sql = """
        SELECT o.*, u.name AS user_name, u.email AS user_email
        FROM orders o
        JOIN users u ON u.id = o.user_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND o.status = %s"
        params.append(status)
    sql += " ORDER BY o.created_at DESC"

    orders = query(sql, params)
    return render_template("orders/list.html", orders=orders, selected_status=status)


@orders_bp.route("/<int:order_id>")
@login_required
def detail(order_id):
    order = query(
        """
        SELECT o.*, u.name AS user_name, u.email AS user_email, u.phone AS user_phone
        FROM orders o
        JOIN users u ON u.id = o.user_id
        WHERE o.id = %s
        """,
        [order_id],
        fetchone=True,
    )
    if order is None:
        flash("Commande introuvable.", "danger")
        return redirect(url_for("orders.list_orders"))

    items = query("SELECT * FROM order_items WHERE order_id = %s", [order_id])
    return render_template("orders/detail.html", order=order, items=items)


@orders_bp.route("/<int:order_id>/status", methods=["POST"])
@login_required
def update_status(order_id):
    status = request.form.get("status", "")
    if status not in VALID_STATUSES:
        flash("Statut invalide.", "danger")
    else:
        execute("UPDATE orders SET status = %s WHERE id = %s", [status, order_id])
        flash("Statut mis à jour.", "success")
    return redirect(url_for("orders.detail", order_id=order_id))
