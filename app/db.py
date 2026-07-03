import pymysql
import pymysql.cursors
from flask import current_app, g


def get_db():
    """Renvoie une connexion MySQL partagée pour la durée de la requête."""
    if "db" not in g:
        g.db = pymysql.connect(
            host=current_app.config["DB_HOST"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
        )
    return g.db


def close_db(_exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query(sql, params=None, fetchone=False):
    """Exécute un SELECT et renvoie les lignes (ou une seule ligne)."""
    with get_db().cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.fetchone() if fetchone else cursor.fetchall()


def execute(sql, params=None):
    """Exécute un INSERT/UPDATE/DELETE et renvoie le nombre de lignes affectées."""
    with get_db().cursor() as cursor:
        cursor.execute(sql, params or ())
        return cursor.rowcount


def init_app(app):
    app.teardown_appcontext(close_db)
