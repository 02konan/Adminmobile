from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from .. import admin_accounts
from ..auth import login_required

admins_bp = Blueprint("admins", __name__, url_prefix="/admins")


@admins_bp.route("/")
@login_required
def list_admins():
    admin_accounts.ensure_ready()
    return render_template(
        "admins/list.html",
        admins=admin_accounts.list_admins(),
        current_id=session.get("admin_id"),
        default_active=admin_accounts.default_password_active(),
        default_username=admin_accounts.DEFAULT_USERNAME,
    )


@admins_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_admin():
    admin_accounts.ensure_ready()
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        name = request.form.get("name", "").strip() or None
        password = request.form.get("password", "")

        if not username or len(password) < 6:
            flash(
                "Identifiant requis et mot de passe d'au moins 6 caractères.",
                "danger",
            )
        elif admin_accounts.username_exists(username):
            flash("Cet identifiant existe déjà.", "danger")
        else:
            admin_accounts.create_admin(username, password, name)
            flash("Administrateur ajouté.", "success")
            return redirect(url_for("admins.list_admins"))

    return render_template("admins/form.html")


@admins_bp.route("/<int:admin_id>/password", methods=["POST"])
@login_required
def reset_password(admin_id):
    password = request.form.get("password", "")
    if len(password) < 6:
        flash("Le mot de passe doit faire au moins 6 caractères.", "danger")
    elif admin_accounts.get_by_id(admin_id) is None:
        flash("Administrateur introuvable.", "danger")
    else:
        admin_accounts.set_password(admin_id, password)
        flash("Mot de passe mis à jour.", "success")
    return redirect(url_for("admins.list_admins"))


@admins_bp.route("/<int:admin_id>/toggle", methods=["POST"])
@login_required
def toggle_active(admin_id):
    admin = admin_accounts.get_by_id(admin_id)
    if admin is None:
        flash("Administrateur introuvable.", "danger")
        return redirect(url_for("admins.list_admins"))

    if admin_id == session.get("admin_id"):
        flash("Vous ne pouvez pas désactiver votre propre compte.", "danger")
    elif admin["is_active"] and admin_accounts.count_active() <= 1:
        flash("Impossible : c'est le dernier administrateur actif.", "danger")
    else:
        admin_accounts.set_active(admin_id, not admin["is_active"])
        flash("Statut du compte mis à jour.", "success")
    return redirect(url_for("admins.list_admins"))


@admins_bp.route("/<int:admin_id>/delete", methods=["POST"])
@login_required
def delete_admin(admin_id):
    admin = admin_accounts.get_by_id(admin_id)
    if admin is None:
        flash("Administrateur introuvable.", "danger")
    elif admin_id == session.get("admin_id"):
        flash("Vous ne pouvez pas supprimer votre propre compte.", "danger")
    elif admin["is_active"] and admin_accounts.count_active() <= 1:
        flash("Impossible : c'est le dernier administrateur actif.", "danger")
    else:
        admin_accounts.delete_admin(admin_id)
        flash("Administrateur supprimé.", "success")
    return redirect(url_for("admins.list_admins"))
