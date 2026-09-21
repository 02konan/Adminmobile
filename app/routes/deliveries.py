from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

deliveries_bp = Blueprint("deliveries", __name__, url_prefix="/deliveries")

VALID_STATUSES = (
    "unassigned",
    "assigned",
    "picked_up",
    "delivering",
    "delivered",
    "failed",
)
# Statut de livraison -> statut de commande à synchroniser.
ORDER_SYNC = {
    "picked_up": "picked_up",
    "delivering": "delivering",
    "delivered": "delivered",
}


@deliveries_bp.route("/")
@login_required
def list_deliveries():
    status = request.args.get("status", "").strip()
    sql = """
        SELECT d.*, o.order_number, o.total, o.shipping_address,
               o.status AS order_status, s.name AS shop_name,
               dr.name AS driver_name, dr.phone AS driver_phone
        FROM deliveries d
        JOIN orders o ON o.id = d.order_id
        LEFT JOIN shops s ON s.id = o.shop_id
        LEFT JOIN users dr ON dr.id = d.driver_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND d.status = %s"
        params.append(status)
    sql += " ORDER BY d.updated_at DESC"
    deliveries = query(sql, params)

    # Commandes prêtes à livrer mais sans livraison créée (à affecter).
    ready_orders = query(
        """
        SELECT o.id, o.order_number, o.total, o.shipping_address, s.name AS shop_name
        FROM orders o
        LEFT JOIN shops s ON s.id = o.shop_id
        WHERE o.status = 'ready'
          AND NOT EXISTS (SELECT 1 FROM deliveries d WHERE d.order_id = o.id)
        ORDER BY o.updated_at ASC
        """
    )
    drivers = query(
        "SELECT id, name, phone FROM users WHERE role = 'driver' ORDER BY name"
    )
    return render_template(
        "deliveries/list.html",
        deliveries=deliveries,
        ready_orders=ready_orders,
        drivers=drivers,
        selected_status=status,
    )


@deliveries_bp.route("/assign", methods=["POST"])
@login_required
def assign():
    order_id = request.form.get("order_id", type=int)
    driver_id = request.form.get("driver_id", type=int)
    if not order_id or not driver_id:
        flash("Commande et livreur requis.", "danger")
        return redirect(url_for("deliveries.list_deliveries"))

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    existing = query(
        "SELECT id FROM deliveries WHERE order_id = %s", [order_id], fetchone=True
    )
    if existing:
        execute(
            "UPDATE deliveries SET driver_id = %s, status = 'assigned', "
            "assigned_at = %s WHERE order_id = %s",
            [driver_id, now, order_id],
        )
    else:
        execute(
            "INSERT INTO deliveries (order_id, driver_id, status, assigned_at) "
            "VALUES (%s, %s, 'assigned', %s)",
            [order_id, driver_id, now],
        )
    flash("Livreur affecté à la commande.", "success")
    return redirect(url_for("deliveries.list_deliveries"))


@deliveries_bp.route("/<int:delivery_id>/status", methods=["POST"])
@login_required
def update_status(delivery_id):
    status = request.form.get("status", "")
    if status not in VALID_STATUSES:
        flash("Statut invalide.", "danger")
        return redirect(url_for("deliveries.list_deliveries"))

    execute("UPDATE deliveries SET status = %s WHERE id = %s", [status, delivery_id])
    # Synchronise le statut de la commande liée.
    if status in ORDER_SYNC:
        row = query(
            "SELECT order_id FROM deliveries WHERE id = %s",
            [delivery_id],
            fetchone=True,
        )
        if row:
            execute(
                "UPDATE orders SET status = %s WHERE id = %s",
                [ORDER_SYNC[status], row["order_id"]],
            )
    flash("Statut de livraison mis à jour.", "success")
    return redirect(url_for("deliveries.list_deliveries"))
