from flask import Flask, redirect, url_for

from . import db
from .auth import auth_bp
from .config import Config
from .routes.categories import categories_bp
from .routes.dashboard import dashboard_bp
from .routes.deliveries import deliveries_bp
from .routes.lives import lives_bp
from .routes.orders import orders_bp
from .routes.products import products_bp
from .routes.reports import reports_bp
from .routes.shops import shops_bp
from .routes.stats import stats_bp
from .routes.users import users_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(shops_bp)
    app.register_blueprint(lives_bp)
    app.register_blueprint(deliveries_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(users_bp)

    @app.context_processor
    def inject_badges():
        """Compteur de signalements ouverts affiché dans la navigation."""
        from flask import session

        if not session.get("admin_logged_in"):
            return {}
        try:
            row = db.query(
                "SELECT COUNT(*) AS n FROM reports WHERE status = 'open'",
                fetchone=True,
            )
            return {"open_reports_count": row["n"] if row else 0}
        except Exception:
            return {"open_reports_count": 0}

    @app.route("/")
    def root():
        return redirect(url_for("dashboard.index"))

    return app
