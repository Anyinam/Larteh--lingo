"""
Category Blueprint: Taxonomy and Classification Endpoints.
"""

from flask import Blueprint, request, jsonify
from backend.app.extensions import db
from backend.app.models.category import Category, slugify

categories_bp = Blueprint("categories", __name__)


@categories_bp.route("/categories", methods=["GET"])
def get_categories():
    """
    Retrieve all taxonomy categories with entry counts.
    ---
    Responses:
        200: JSON list of Category objects.
    """
    categories = Category.query.order_by(Category.name.asc()).all()
    return jsonify({
        "status": "success",
        "count": len(categories),
        "data": [cat.to_dict() for cat in categories],
    }), 200


@categories_bp.route("/categories", methods=["POST"])
def create_category():
    """
    Create a new taxonomy category.
    ---
    Payload (JSON):
        name (str): Category name (e.g. 'Numbers', 'Greetings').
        slug (str, optional): Custom URL slug.
        description (str, optional): Informational notes.
    Responses:
        201: Successfully created.
        400: Validation error.
        409: Duplicate name or slug.
    """
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    description = data.get("description", "").strip() or None
    slug = data.get("slug", "").strip() or None

    if not name:
        return jsonify({
            "status": "error",
            "message": "Category 'name' is required.",
        }), 400

    generated_slug = slugify(slug or name)

    # Check for duplicate
    existing = Category.query.filter(
        (Category.name.ilike(name)) | (Category.slug == generated_slug)
    ).first()
    if existing:
        return jsonify({
            "status": "error",
            "message": f"Category with name '{name}' or slug '{generated_slug}' already exists.",
        }), 409

    category = Category(name=name, slug=generated_slug, description=description)
    db.session.add(category)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Category created successfully.",
        "data": category.to_dict(),
    }), 201


@categories_bp.route("/categories/<int:category_id>", methods=["GET"])
def get_category_by_id(category_id: int):
    """Retrieve a single category by its identifier."""
    category = db.session.get(Category, category_id)
    if not category:
        return jsonify({"status": "error", "message": "Category not found."}), 404

    return jsonify({
        "status": "success",
        "data": category.to_dict(),
    }), 200

