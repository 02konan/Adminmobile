from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..auth import login_required
from ..db import execute, get_db, query

products_bp = Blueprint("products", __name__, url_prefix="/products")


def _next_product_id():
    rows = query("SELECT id FROM products WHERE id REGEXP '^p[0-9]+$'")
    numbers = [int(row["id"][1:]) for row in rows]
    return f"p{(max(numbers) + 1) if numbers else 1}"


def _split_variants(raw):
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


@products_bp.route("/")
@login_required
def list_products():
    search = request.args.get("q", "").strip()
    category_id = request.args.get("category", "").strip()

    sql = """
        SELECT p.*, c.name AS category_name
        FROM products p
        JOIN categories c ON c.id = p.category_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (p.name LIKE %s OR p.id LIKE %s)"
        params += [f"%{search}%", f"%{search}%"]
    if category_id:
        sql += " AND p.category_id = %s"
        params.append(category_id)
    sql += " ORDER BY p.name"

    products = query(sql, params)
    categories = query("SELECT id, name FROM categories ORDER BY name")

    return render_template(
        "products/list.html",
        products=products,
        categories=categories,
        search=search,
        selected_category=category_id,
    )


@products_bp.route("/new", methods=["GET", "POST"])
@login_required
def new_product():
    categories = query("SELECT id, name FROM categories ORDER BY name")

    if request.method == "POST":
        _save_product(product_id=None, categories=categories)
        return redirect(url_for("products.list_products"))

    return render_template(
        "products/form.html", product=None, categories=categories, colors="", sizes=""
    )


@products_bp.route("/<product_id>/edit", methods=["GET", "POST"])
@login_required
def edit_product(product_id):
    categories = query("SELECT id, name FROM categories ORDER BY name")
    product = query("SELECT * FROM products WHERE id = %s", [product_id], fetchone=True)
    if product is None:
        flash("Produit introuvable.", "danger")
        return redirect(url_for("products.list_products"))

    if request.method == "POST":
        _save_product(product_id=product_id, categories=categories)
        return redirect(url_for("products.list_products"))

    colors = ", ".join(
        row["color"]
        for row in query(
            "SELECT color FROM product_colors WHERE product_id = %s ORDER BY id", [product_id]
        )
    )
    sizes = ", ".join(
        row["size"]
        for row in query(
            "SELECT size FROM product_sizes WHERE product_id = %s ORDER BY id", [product_id]
        )
    )

    return render_template(
        "products/form.html", product=product, categories=categories, colors=colors, sizes=sizes
    )


def _save_product(product_id, categories):
    form = request.form
    name = form.get("name", "").strip()
    category_id = form.get("category_id", "")
    price = form.get("price", "0").replace(",", ".")
    old_price = form.get("old_price", "").replace(",", ".").strip()

    if not name or not category_id:
        flash("Le nom et la catégorie sont obligatoires.", "danger")
        return

    if category_id not in {c["id"] for c in categories}:
        flash("Catégorie invalide.", "danger")
        return

    try:
        price_value = float(price)
        old_price_value = float(old_price) if old_price else None
    except ValueError:
        flash("Prix invalide.", "danger")
        return

    fields = {
        "category_id": category_id,
        "name": name,
        "description": form.get("description", "").strip(),
        "price": price_value,
        "old_price": old_price_value,
        "image_url": form.get("image_url", "").strip(),
        "stock": int(form.get("stock") or 0),
        "is_featured": 1 if form.get("is_featured") == "on" else 0,
    }

    db = get_db()
    with db.cursor() as cursor:
        if product_id is None:
            product_id = _next_product_id()
            cursor.execute(
                """
                INSERT INTO products
                    (id, category_id, name, description, price, old_price,
                     image_url, stock, is_featured, rating, review_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 0)
                """,
                [
                    product_id,
                    fields["category_id"],
                    fields["name"],
                    fields["description"],
                    fields["price"],
                    fields["old_price"],
                    fields["image_url"],
                    fields["stock"],
                    fields["is_featured"],
                ],
            )
        else:
            cursor.execute(
                """
                UPDATE products
                SET category_id=%s, name=%s, description=%s, price=%s, old_price=%s,
                    image_url=%s, stock=%s, is_featured=%s
                WHERE id=%s
                """,
                [
                    fields["category_id"],
                    fields["name"],
                    fields["description"],
                    fields["price"],
                    fields["old_price"],
                    fields["image_url"],
                    fields["stock"],
                    fields["is_featured"],
                    product_id,
                ],
            )
            cursor.execute("DELETE FROM product_colors WHERE product_id = %s", [product_id])
            cursor.execute("DELETE FROM product_sizes WHERE product_id = %s", [product_id])

        for color in _split_variants(form.get("colors", "")):
            cursor.execute(
                "INSERT INTO product_colors (product_id, color) VALUES (%s, %s)",
                [product_id, color],
            )
        for size in _split_variants(form.get("sizes", "")):
            cursor.execute(
                "INSERT INTO product_sizes (product_id, size) VALUES (%s, %s)",
                [product_id, size],
            )

    flash("Produit enregistré.", "success")


@products_bp.route("/<product_id>/delete", methods=["POST"])
@login_required
def delete_product(product_id):
    execute("DELETE FROM products WHERE id = %s", [product_id])
    flash("Produit supprimé.", "success")
    return redirect(url_for("products.list_products"))
