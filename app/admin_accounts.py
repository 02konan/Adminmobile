"""Comptes administrateurs stockés en base (plusieurs administrateurs).

Remplace le compte unique par variables d'environnement. La table est créée
automatiquement au besoin, et amorcée une première fois avec le compte défini
par ADMIN_USERNAME / ADMIN_PASSWORD_HASH (rétro-compatibilité), afin de ne
jamais se retrouver sans accès.
"""

import os

from werkzeug.security import check_password_hash, generate_password_hash

from .db import execute, get_db, query

# Compte par défaut créé au tout premier lancement si rien n'est configuré.
# À CHANGER après la première connexion (un avertissement s'affiche tant que
# ce mot de passe est encore actif).
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "divix2025"

_ready = False


def ensure_ready():
    """Crée la table `admin_users` si besoin et amorce le premier compte."""
    global _ready
    if _ready:
        return
    with get_db().cursor() as cursor:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_users (
              id            INT UNSIGNED AUTO_INCREMENT,
              username      VARCHAR(100) NOT NULL,
              name          VARCHAR(150) NULL,
              password_hash VARCHAR(255) NOT NULL,
              is_active     TINYINT(1) NOT NULL DEFAULT 1,
              created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
              PRIMARY KEY (id),
              UNIQUE KEY uq_admin_username (username)
            ) ENGINE=InnoDB
            """
        )
    # Amorçage : si aucun admin en base, créer un premier compte.
    if query("SELECT COUNT(*) AS n FROM admin_users", fetchone=True)["n"] == 0:
        env_user = os.environ.get("ADMIN_USERNAME")
        env_hash = os.environ.get("ADMIN_PASSWORD_HASH")
        if env_user and env_hash:
            # Priorité au compte défini par variables d'environnement.
            execute(
                "INSERT INTO admin_users (username, name, password_hash) "
                "VALUES (%s, %s, %s)",
                [env_user, "Administrateur", env_hash],
            )
        else:
            # Sinon, compte par défaut prêt à l'emploi (à changer ensuite).
            execute(
                "INSERT INTO admin_users (username, name, password_hash) "
                "VALUES (%s, %s, %s)",
                [
                    DEFAULT_USERNAME,
                    "Administrateur",
                    generate_password_hash(DEFAULT_PASSWORD),
                ],
            )
    _ready = True


def default_password_active():
    """True si un compte utilise encore le mot de passe par défaut.

    Défensif : ne casse jamais la page (retourne False si la base est
    indisponible ou la table absente)."""
    try:
        admin = query(
            "SELECT password_hash FROM admin_users "
            "WHERE username = %s AND is_active = 1",
            [DEFAULT_USERNAME],
            fetchone=True,
        )
        return admin is not None and check_password_hash(
            admin["password_hash"], DEFAULT_PASSWORD
        )
    except Exception:
        return False


def get_by_username(username):
    return query(
        "SELECT * FROM admin_users WHERE username = %s AND is_active = 1",
        [username],
        fetchone=True,
    )


def get_by_id(admin_id):
    return query("SELECT * FROM admin_users WHERE id = %s", [admin_id], fetchone=True)


def list_admins():
    return query("SELECT * FROM admin_users ORDER BY username")


def username_exists(username, exclude_id=None):
    if exclude_id:
        row = query(
            "SELECT id FROM admin_users WHERE username = %s AND id <> %s",
            [username, exclude_id],
            fetchone=True,
        )
    else:
        row = query(
            "SELECT id FROM admin_users WHERE username = %s", [username], fetchone=True
        )
    return row is not None


def create_admin(username, password, name=None):
    execute(
        "INSERT INTO admin_users (username, name, password_hash) VALUES (%s, %s, %s)",
        [username, name or None, generate_password_hash(password)],
    )


def set_password(admin_id, password):
    execute(
        "UPDATE admin_users SET password_hash = %s WHERE id = %s",
        [generate_password_hash(password), admin_id],
    )


def set_active(admin_id, active):
    execute(
        "UPDATE admin_users SET is_active = %s WHERE id = %s",
        [1 if active else 0, admin_id],
    )


def delete_admin(admin_id):
    execute("DELETE FROM admin_users WHERE id = %s", [admin_id])


def count_active():
    return query(
        "SELECT COUNT(*) AS n FROM admin_users WHERE is_active = 1", fetchone=True
    )["n"]
