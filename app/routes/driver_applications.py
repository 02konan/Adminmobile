from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

driver_apps_bp = Blueprint(
    "driver_applications", __name__, url_prefix="/driver-applications"
)

VALID_STATUSES = ("pending", "approved", "rejected")


@driver_apps_bp.route("/")
@login_required
def list_applications():
    status = request.args.get("status", "").strip()
    sql = """
        SELECT da.*, u.name AS applicant_name, u.phone AS applicant_phone
        FROM driver_applications da
        JOIN users u ON u.id = da.user_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND da.status = %s"
        params.append(status)
    sql += (
        " ORDER BY FIELD(da.status,'pending','approved','rejected'),"
        " da.created_at DESC"
    )
    applications = query(sql, params)
    return render_template(
        "driver_applications/list.html",
        applications=applications,
        selected_status=status,
    )


@driver_apps_bp.route("/<int:app_id>")
@login_required
def detail(app_id):
    application = query(
        """
        SELECT da.*, u.name AS applicant_name, u.phone AS applicant_phone,
               u.email AS applicant_email, u.role AS applicant_role
        FROM driver_applications da
        JOIN users u ON u.id = da.user_id
        WHERE da.id = %s
        """,
        [app_id],
        fetchone=True,
    )
    if application is None:
        flash("Candidature introuvable.", "danger")
        return redirect(url_for("driver_applications.list_applications"))
    return render_template(
        "driver_applications/detail.html", application=application
    )


@driver_apps_bp.route("/<int:app_id>/approve", methods=["POST"])
@login_required
def approve(app_id):
    application = query(
        "SELECT * FROM driver_applications WHERE id = %s", [app_id], fetchone=True
    )
    if application is None:
        flash("Candidature introuvable.", "danger")
        return redirect(url_for("driver_applications.list_applications"))

    execute(
        "UPDATE users SET role = 'driver' WHERE id = %s", [application["user_id"]]
    )
    execute(
        "UPDATE driver_applications SET status = 'approved', review_note = NULL, "
        "reviewed_at = %s WHERE id = %s",
        [datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), app_id],
    )
    flash("Candidature approuvée : le compte est désormais livreur.", "success")
    return redirect(url_for("driver_applications.detail", app_id=app_id))


@driver_apps_bp.route("/<int:app_id>/reject", methods=["POST"])
@login_required
def reject(app_id):
    note = (request.form.get("note") or "").strip() or None
    execute(
        "UPDATE driver_applications SET status = 'rejected', review_note = %s, "
        "reviewed_at = %s WHERE id = %s",
        [note, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), app_id],
    )
    flash("Candidature refusée.", "warning")
    return redirect(url_for("driver_applications.detail", app_id=app_id))
