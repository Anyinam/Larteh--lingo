"""
Flask Application Factory for Larteh Lingo Language Engine.
"""

import os
from flask import Flask, jsonify
from backend.app.config import config_by_name
from backend.app.extensions import db, migrate, cors
from backend.app.routes import api_v1_bp
from backend.app.routes.studio import studio_bp


def create_app(config_name: str = None) -> Flask:
    """Create and configure the Flask application instance."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(
        app,
        resources={
            r"/api/*": {
                "origins": app.config.get("CORS_ORIGINS", "*"),
                "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            }
        },
    )

    # Register blueprints
    app.register_blueprint(api_v1_bp)
    app.register_blueprint(studio_bp, url_prefix="/api/studio")

    # Health check route
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "larteh-lingo-engine",
            "version": "1.0.0",
        }), 200

    # Error Handlers
    @app.errorhandler(404)
    def handle_not_found(e):
        return jsonify({"status": "error", "message": "Resource not found"}), 404

    @app.errorhandler(413)
    def handle_payload_too_large(e):
        return jsonify({"status": "error", "message": "Audio file exceeds maximum allowed upload size (16MB)"}), 413

    @app.errorhandler(500)
    def handle_internal_server_error(e):
        app.logger.exception("Internal Server Error occurred.")
        return jsonify({"status": "error", "message": "Internal server error"}), 500

    # Ensure upload directory exists if local storage is used
    if app.config.get("STORAGE_BACKEND") == "local":
        os.makedirs(app.config["LOCAL_UPLOAD_FOLDER"], exist_ok=True)

    return app

