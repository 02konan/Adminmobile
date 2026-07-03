from flask import Flask, redirect, url_for

from . import db
from .auth import auth_bp
from .config import Config
from .routes.categories import categories_bp
from .routes.dashboard import dashboard_bp
from .routes.orders import orders_bp
from .routes.products import products_bp
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
    app.register_blueprint(users_bp)

    @app.route("/")
    def root():
        return redirect(url_for("dashboard.index"))

    return app
