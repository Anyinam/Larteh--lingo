"""
Routes package initialization and blueprint registration helper.
"""

from flask import Blueprint
from backend.app.routes.categories import categories_bp
from backend.app.routes.lexicon import lexicon_bp

# Aggregate API v1 Blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")
api_v1_bp.register_blueprint(categories_bp)
api_v1_bp.register_blueprint(lexicon_bp)

__all__ = ["api_v1_bp"]

