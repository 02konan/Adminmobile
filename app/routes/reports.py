from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

VALID_STATUSES = ("open", "reviewing", "resolved", "dismissed")


@reports_bp.route("/")
@login_required
def list_reports():
    status = request.args.get("status", "").strip()
    sql = """
        SELECT r.*, u.name AS reporter_name, u.phone AS reporter_phone
        FROM reports r
        LEFT JOIN users u ON u.id = r.reporter_id
        WHERE 1=1
    """
    params = []
    if status in VALID_STATUSES:
        sql += " AND r.status = %s"
        params.append(status)
    sql += " ORDER BY FIELD(r.status,'open','reviewing','resolved','dismissed'), r.created_at DESC"
    reports = query(sql, params)
    return render_template(
        "reports/list.html", reports=reports, selected_status=status
    )


@reports_bp.route("/<int:report_id>/status", methods=["POST"])
@login_required
def update_status(report_id):
    status = request.form.get("status", "")
    if status not in VALID_STATUSES:
        flash("Statut invalide.", "danger")
        return redirect(url_for("reports.list_reports"))

    resolved_at = None
    if status in ("resolved", "dismissed"):
        resolved_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    execute(
        "UPDATE reports SET status = %s, resolved_at = %s WHERE id = %s",
        [status, resolved_at, report_id],
    )
    flash("Signalement mis à jour.", "success")
    return redirect(url_for("reports.list_reports"))
