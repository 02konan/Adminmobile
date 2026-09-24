from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

seller_apps_bp = Blueprint(
    "seller_applications", __name__, url_prefix="/seller-applications"
)

VALID_STATUSES = ("pending", "approved", "rejected")


@seller_apps_bp.route("/")
@login_required
def list_applications():
    status = request.args.get("status", "").strip()
    sql = """
        SELECT sa.*, u.name AS applicant_name, u.phone AS applicant_phone
        FROM seller_applications sa
        JOIN users u ON u.id = sa.user_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND sa.status = %s"
        params.append(status)
    sql += (
        " ORDER BY FIELD(sa.status,'pending','approved','rejected'),"
        " sa.created_at DESC"
    )
    applications = query(sql, params)
    return render_template(
        "seller_applications/list.html",
        applications=applications,
        selected_status=status,
    )


@seller_apps_bp.route("/<int:app_id>")
@login_required
def detail(app_id):
    application = query(
        """
        SELECT sa.*, u.name AS applicant_name, u.phone AS applicant_phone,
               u.email AS applicant_email, u.role AS applicant_role
        FROM seller_applications sa
        JOIN users u ON u.id = sa.user_id
        WHERE sa.id = %s
        """,
        [app_id],
        fetchone=True,
    )
    if application is None:
        flash("Candidature introuvable.", "danger")
        return redirect(url_for("seller_applications.list_applications"))
    return render_template(
        "seller_applications/detail.html", application=application
    )


@seller_apps_bp.route("/<int:app_id>/approve", methods=["POST"])
@login_required
def approve(app_id):
    application = query(
        "SELECT * FROM seller_applications WHERE id = %s", [app_id], fetchone=True
    )
    if application is None:
        flash("Candidature introuvable.", "danger")
        return redirect(url_for("seller_applications.list_applications"))

    user_id = application["user_id"]
    # Boutique existante ? sinon on la crée.
    existing = query(
        "SELECT id FROM shops WHERE user_id = %s", [user_id], fetchone=True
    )
    phone = query(
        "SELECT phone FROM users WHERE id = %s", [user_id], fetchone=True
    )
    phone = phone["phone"] if phone else None

    if existing is None:
        execute(
            """
            INSERT INTO shops
                (user_id, name, logo_url, cover_url, category, commune,
                 phone, whatsapp, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'validated')
            """,
            [
                user_id,
                application["shop_name"],
                application["logo_url"],
                application["cover_url"],
                application["category"],
                application["city"],
                phone,
                phone,
            ],
        )
    else:
        execute(
            """
            UPDATE shops
            SET name = %s, logo_url = %s, cover_url = %s, category = %s,
                commune = %s, status = 'validated'
            WHERE user_id = %s
            """,
            [
                application["shop_name"],
                application["logo_url"],
                application["cover_url"],
                application["category"],
                application["city"],
                user_id,
            ],
        )

    execute("UPDATE users SET role = 'merchant' WHERE id = %s", [user_id])
    execute(
        "UPDATE seller_applications SET status = 'approved', review_note = NULL, "
        "reviewed_at = %s WHERE id = %s",
        [datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), app_id],
    )
    flash("Candidature approuvée : le compte est désormais vendeur.", "success")
    return redirect(url_for("seller_applications.detail", app_id=app_id))


@seller_apps_bp.route("/<int:app_id>/reject", methods=["POST"])
@login_required
def reject(app_id):
    note = (request.form.get("note") or "").strip() or None
    execute(
        "UPDATE seller_applications SET status = 'rejected', review_note = %s, "
        "reviewed_at = %s WHERE id = %s",
        [note, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), app_id],
    )
    flash("Candidature refusée.", "warning")
    return redirect(url_for("seller_applications.detail", app_id=app_id))
