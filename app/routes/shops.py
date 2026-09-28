from datetime import datetime

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
        "shops/detail.html",
        shop=shop,
        products=products,
        lives=lives,
        stats=stats,
        now=datetime.utcnow(),
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


@shops_bp.route("/<int:shop_id>/appearance", methods=["POST"])
@login_required
def update_appearance(shop_id):
    """Met à jour le logo et la bannière (image de couverture) de la boutique."""
    logo_url = (request.form.get("logo_url") or "").strip() or None
    cover_url = (request.form.get("cover_url") or "").strip() or None
    execute(
        "UPDATE shops SET logo_url = %s, cover_url = %s WHERE id = %s",
        [logo_url, cover_url, shop_id],
    )
    flash("Apparence de la boutique mise à jour.", "success")
    return redirect(url_for("shops.detail", shop_id=shop_id))


PLAN_DAYS = {"monthly": 30, "quarterly": 90, "yearly": 365}


@shops_bp.route("/<int:shop_id>/subscription", methods=["POST"])
@login_required
def update_subscription(shop_id):
    """Active/prolonge ou révoque manuellement l'abonnement d'une boutique.

    (En attendant le paiement mobile money automatique.)
    """
    action = request.form.get("action", "")
    if action == "revoke":
        execute(
            "UPDATE shops SET subscription_plan = NULL, "
            "subscription_expires_at = NULL WHERE id = %s",
            [shop_id],
        )
        flash("Abonnement révoqué.", "warning")
        return redirect(url_for("shops.detail", shop_id=shop_id))

    plan = request.form.get("plan", "monthly")
    days = PLAN_DAYS.get(plan)
    if days is None:
        flash("Offre invalide.", "danger")
        return redirect(url_for("shops.detail", shop_id=shop_id))

    # Prolonge depuis la date d'expiration si elle est future, sinon depuis maintenant.
    execute(
        """
        UPDATE shops
        SET subscription_plan = %s,
            subscription_expires_at = DATE_ADD(
                IF(subscription_expires_at IS NOT NULL
                   AND subscription_expires_at > NOW(),
                   subscription_expires_at, NOW()),
                INTERVAL %s DAY)
        WHERE id = %s
        """,
        [plan, days, shop_id],
    )
    # Trace un paiement "manuel" abouti.
    execute(
        "INSERT INTO subscription_payments "
        "(shop_id, plan, amount, provider, status, days, paid_at) "
        "VALUES (%s, %s, 0, 'manual', 'success', %s, NOW())",
        [shop_id, plan, days],
    )
    flash(f"Abonnement activé/prolongé de {days} jours.", "success")
    return redirect(url_for("shops.detail", shop_id=shop_id))
