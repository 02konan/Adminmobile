from functools import wraps

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

from . import admin_accounts

auth_bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        admin_accounts.ensure_ready()
        admin = admin_accounts.get_by_username(username)
        valid = admin is not None and check_password_hash(
            admin["password_hash"], password
        )

        if valid:
            session.clear()
            session["admin_logged_in"] = True
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session["admin_name"] = admin["name"] or admin["username"]
            next_url = request.form.get("next") or url_for("dashboard.index")
            return redirect(next_url)

        flash("Identifiants incorrects.", "danger")

    return render_template("login.html", next=request.args.get("next", ""))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
