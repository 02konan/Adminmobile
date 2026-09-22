from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

shops_bp = Blueprint("shops", __name__, url_prefix="/shops")

VALID_STATUSES = ("pending", "validated", "suspended")


@shops_bp.route("/")
@login_required
def list_shops():
    status = request.args.get("status", "").strip()
    sql = """
        SELECT s.*, u.name AS owner_name, u.phone AS owner_phone,
               (SELECT COUNT(*) FROM products p WHERE p.shop_id = s.id) AS product_count,
               (SELECT COUNT(*) FROM lives l WHERE l.shop_id = s.id) AS live_count
        FROM shops s
        JOIN users u ON u.id = s.user_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND s.status = %s"
        params.append(status)
    sql += " ORDER BY s.created_at DESC"
    shops = query(sql, params)
    return render_template("shops/list.html", shops=shops, selected_status=status)


@shops_bp.route("/<int:shop_id>")
@login_required
def detail(shop_id):
    shop = query(
        """
        SELECT s.*, u.name AS owner_name, u.phone AS owner_phone, u.email AS owner_email
        FROM shops s
        JOIN users u ON u.id = s.user_id
        WHERE s.id = %s
        """,
        [shop_id],
        fetchone=True,
    )
    if shop is None:
        flash("Boutique introuvable.", "danger")
        return redirect(url_for("shops.list_shops"))

    products = query(
        "SELECT * FROM products WHERE shop_id = %s ORDER BY created_at DESC",
        [shop_id],
    )
    lives = query(
        "SELECT * FROM lives WHERE shop_id = %s ORDER BY created_at DESC LIMIT 10",
        [shop_id],
    )
    stats = {
        "orders": query(
            "SELECT COUNT(*) AS n FROM orders WHERE shop_id = %s",
            [shop_id],
            fetchone=True,
        )["n"],
        "revenue": query(
            "SELECT COALESCE(SUM(total),0) AS t FROM orders "
            "WHERE shop_id = %s AND status = 'delivered'",
            [shop_id],
            fetchone=True,
        )["t"],
    }
    return render_template(
        "shops/detail.html", shop=shop, products=products, lives=lives, stats=stats
    )


@shops_bp.route("/<int:shop_id>/status", methods=["POST"])
@login_required
def update_status(shop_id):
    status = request.form.get("status", "")
    if status not in VALID_STATUSES:
        flash("Statut invalide.", "danger")
    else:
        execute("UPDATE shops SET status = %s WHERE id = %s", [status, shop_id])
        flash("Statut de la boutique mis à jour.", "success")
    return redirect(url_for("shops.detail", shop_id=shop_id))
