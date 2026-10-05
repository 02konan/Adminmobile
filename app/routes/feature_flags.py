"""Feature flags : activer / désactiver des fonctionnalités de l'app.

Seules les surcharges sont stockées dans la table `feature_flags` ; le reste
suit les valeurs par défaut ci-dessous.

⚠️ À garder synchronisé avec le backend (appmobile-backend/app/features.py,
DEFAULT_FLAGS). Si une clé est ajoutée côté backend, l'ajouter ici pour la
rendre pilotable depuis l'admin.
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

feature_flags_bp = Blueprint(
    "feature_flags", __name__, url_prefix="/feature-flags"
)

# (clé, libellé, activé par défaut, aide)
FLAG_CATALOG = [
    (
        "lives",
        "Lives (diffusion en direct)",
        True,
        "Création, démarrage et jeton Agora. Gourmand en ressources — à "
        "couper en cas de forte charge.",
    ),
    (
        "reels",
        "ReelShops (vidéos courtes)",
        True,
        "Feed, création et envoi vidéo Cloudinary. Gourmand en ressources.",
    ),
    (
        "notifyLiveStart",
        "Notification — démarrage d'un live",
        True,
        "Notification envoyée à tous les utilisateurs quand un live démarre.",
    ),
    (
        "notifyNewReel",
        "Notification — nouveau ReelShop",
        True,
        "Notification envoyée à tous quand une boutique publie une vidéo.",
    ),
    (
        "mobileMoney",
        "Paiement mobile money",
        False,
        "Fonctionnalité à venir — laisser éteint tant qu'elle n'est pas prête.",
    ),
    (
        "reviews",
        "Avis & notes produits",
        False,
        "Fonctionnalité à venir — laisser éteint tant qu'elle n'est pas prête.",
    ),
]

_VALID_KEYS = {key for key, _, _, _ in FLAG_CATALOG}


@feature_flags_bp.route("/")
@login_required
def list_flags():
    overrides = {}
    try:
        rows = query("SELECT `key`, enabled FROM feature_flags")
        overrides = {r["key"]: bool(r["enabled"]) for r in rows}
    except Exception:
        # Table absente (migration non passée) : on affiche les défauts.
        flash(
            "Table feature_flags introuvable — exécutez la migration "
            "divix_step18_feature_flags.sql.",
            "warning",
        )

    flags = []
    for key, label, default, hint in FLAG_CATALOG:
        flags.append(
            {
                "key": key,
                "label": label,
                "hint": hint,
                "enabled": overrides.get(key, default),
                "default": default,
                "overridden": key in overrides,
            }
        )
    return render_template("feature_flags/list.html", flags=flags)


@feature_flags_bp.route("/<key>/toggle", methods=["POST"])
@login_required
def toggle_flag(key):
    if key not in _VALID_KEYS:
        flash("Fonctionnalité inconnue.", "danger")
        return redirect(url_for("feature_flags.list_flags"))

    enabled = request.form.get("enabled") == "1"
    execute(
        "INSERT INTO feature_flags (`key`, enabled) VALUES (%s, %s) "
        "ON DUPLICATE KEY UPDATE enabled = VALUES(enabled)",
        [key, 1 if enabled else 0],
    )
    flash(
        f"« {key} » {'activé' if enabled else 'désactivé'}.",
        "success",
    )
    return redirect(url_for("feature_flags.list_flags"))
