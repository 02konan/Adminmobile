from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

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

        expected_username = current_app.config["ADMIN_USERNAME"]
        expected_hash = current_app.config["ADMIN_PASSWORD_HASH"]

        valid = (
            expected_hash
            and username == expected_username
            and check_password_hash(expected_hash, password)
        )

        if valid:
            session.clear()
            session["admin_logged_in"] = True
            session["admin_username"] = username
            next_url = request.form.get("next") or url_for("dashboard.index")
            return redirect(next_url)

        flash("Identifiants incorrects.", "danger")

    return render_template("login.html", next=request.args.get("next", ""))


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
