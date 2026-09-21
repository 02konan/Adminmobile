from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import query

lives_bp = Blueprint("lives", __name__, url_prefix="/lives")

VALID_STATUSES = ("scheduled", "live", "ended")


@lives_bp.route("/")
@login_required
def list_lives():
    status = request.args.get("status", "").strip()
    sql = """
        SELECT l.*, s.name AS shop_name,
               (SELECT COUNT(*) FROM live_products lp WHERE lp.live_id = l.id) AS product_count,
               (SELECT COUNT(*) FROM live_messages m WHERE m.live_id = l.id) AS message_count
        FROM lives l
        JOIN shops s ON s.id = l.shop_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND l.status = %s"
        params.append(status)
    sql += " ORDER BY FIELD(l.status,'live','scheduled','ended'), l.created_at DESC"
    lives = query(sql, params)
    return render_template("lives/list.html", lives=lives, selected_status=status)


@lives_bp.route("/<int:live_id>")
@login_required
def detail(live_id):
    live = query(
        """
        SELECT l.*, s.name AS shop_name
        FROM lives l
        JOIN shops s ON s.id = l.shop_id
        WHERE l.id = %s
        """,
        [live_id],
        fetchone=True,
    )
    if live is None:
        flash("Live introuvable.", "danger")
        return redirect(url_for("lives.list_lives"))

    products = query(
        """
        SELECT p.id, p.name, p.price, p.image_url, lp.position
        FROM live_products lp
        JOIN products p ON p.id = lp.product_id
        WHERE lp.live_id = %s
        ORDER BY lp.position
        """,
        [live_id],
    )
    messages = query(
        "SELECT * FROM live_messages WHERE live_id = %s ORDER BY id DESC LIMIT 30",
        [live_id],
    )
    orders_count = query(
        "SELECT COUNT(*) AS n FROM orders WHERE live_id = %s",
        [live_id],
        fetchone=True,
    )["n"]
    return render_template(
        "lives/detail.html",
        live=live,
        products=products,
        messages=messages,
        orders_count=orders_count,
    )
