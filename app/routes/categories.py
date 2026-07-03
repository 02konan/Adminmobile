import re
import unicodedata

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, query

categories_bp = Blueprint("categories", __name__, url_prefix="/categories")

# Icônes reconnues par l'application mobile (lib/models/category.dart).
# En choisir une autre affichera une icône générique côté app tant que le
# mapping Flutter n'est pas mis à jour.
AVAILABLE_ICONS = [
    ("checkroom", "Vêtements"),
    ("sports_soccer_outlined", "Sport / Chaussures"),
    ("headphones", "Électronique"),
    ("watch_outlined", "Accessoires"),
    ("chair_outlined", "Maison"),
    ("spa_outlined", "Beauté"),
]


def _slugify(name):
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "categorie"


def _unique_id(base_id):
    candidate = base_id
    suffix = 2
    existing_ids = {row["id"] for row in query("SELECT id FROM categories")}
    while candidate in existing_ids:
        candidate = f"{base_id}-{suffix}"
        suffix += 1
    return candidate


@categories_bp.route("/")
@login_required
def list_categories():
    categories = query(
        """
        SELECT c.*, COUNT(p.id) AS product_count
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id
        ORDER BY c.name
        """
    )
    return render_template("categories/list.html", categories=categories, icons=dict(AVAILABLE_ICONS))


@categories_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_category():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "")

        if not name:
            flash("Le nom est obligatoire.", "danger")
        elif icon not in dict(AVAILABLE_ICONS):
            flash("Icône invalide.", "danger")
        else:
            category_id = _unique_id(_slugify(name))
            execute(
                "INSERT INTO categories (id, name, icon) VALUES (%s, %s, %s)",
                [category_id, name, icon],
            )
            flash("Catégorie créée.", "success")
            return redirect(url_for("categories.list_categories"))

    return render_template("categories/form.html", category=None, icons=AVAILABLE_ICONS)


@categories_bp.route("/<category_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    category = query("SELECT * FROM categories WHERE id = %s", [category_id], fetchone=True)
    if category is None:
        flash("Catégorie introuvable.", "danger")
        return redirect(url_for("categories.list_categories"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        icon = request.form.get("icon", "")

        if not name:
            flash("Le nom est obligatoire.", "danger")
        elif icon not in dict(AVAILABLE_ICONS):
            flash("Icône invalide.", "danger")
        else:
            execute(
                "UPDATE categories SET name=%s, icon=%s WHERE id=%s",
                [name, icon, category_id],
            )
            flash("Catégorie mise à jour.", "success")
            return redirect(url_for("categories.list_categories"))

    return render_template("categories/form.html", category=category, icons=AVAILABLE_ICONS)


@categories_bp.route("/<category_id>/delete", methods=["POST"])
@login_required
def delete_category(category_id):
    product_count = query(
        "SELECT COUNT(*) AS n FROM products WHERE category_id = %s", [category_id], fetchone=True
    )["n"]
    if product_count > 0:
        flash(
            f"Impossible de supprimer : {product_count} produit(s) utilisent encore cette catégorie.",
            "danger",
        )
    else:
        execute("DELETE FROM categories WHERE id = %s", [category_id])
        flash("Catégorie supprimée.", "success")
    return redirect(url_for("categories.list_categories"))
