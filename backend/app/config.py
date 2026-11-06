"""
Application Configuration Module.

Supports 12-factor configuration via environment variables for
Development, Testing, and Production environments. Seamlessly integrates
PostgreSQL and Cloudflare R2 (S3-compatible object storage) with local disk fallback.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory for the backend
BASE_DIR = Path(__file__).resolve().parent.parent

# Load Neon CLI's local env file first, then project and backend fallbacks.
load_dotenv(BASE_DIR.parent / ".env.local")
load_dotenv(BASE_DIR.parent / ".env")
load_dotenv(BASE_DIR / ".env")

class Config:
    """Base application configuration shared across all environments."""

    # -------------------------------------------------------------------------
    # Core Application & Security Settings
    # -------------------------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "larteh-lingo-dev-secret-key-change-in-prod")
    JSON_SORT_KEYS = False

    # -------------------------------------------------------------------------
    # Database Configuration (PostgreSQL with SQLite fallback)
    # -------------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'larteh_lingo.db'}",
    )
    # Normalize legacy Heroku/Render postgres:// URI scheme
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    # Keep using the declared psycopg2-binary driver across SQLAlchemy versions.
    if SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgresql://", "postgresql+psycopg2://", 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # -------------------------------------------------------------------------
    # Uploads, Audio Media Limits & Allowed Mimetypes
    # -------------------------------------------------------------------------
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB max
    ALLOWED_AUDIO_EXTENSIONS = {"wav", "webm", "mp3", "ogg", "m4a", "flac"}
    ALLOWED_AUDIO_MIMETYPES = {
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/webm",
        "audio/ogg",
        "audio/mpeg",
        "audio/mp3",
        "audio/mp4",
        "audio/x-m4a",
        "video/webm",  # Chrome/Android webm audio recordings often tagged as video/webm
    }

    # -------------------------------------------------------------------------
    # Cloudflare R2 Object Storage (S3-Compatible)
    # -------------------------------------------------------------------------
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "r2").lower()

    # Cloudflare Account ID & S3 Credentials
    R2_ACCOUNT_ID = os.getenv("R2_ACCOUNT_ID")
    R2_ACCESS_KEY_ID = os.getenv("R2_ACCESS_KEY_ID") or os.getenv("S3_ACCESS_KEY_ID")
    R2_SECRET_ACCESS_KEY = os.getenv("R2_SECRET_ACCESS_KEY") or os.getenv("S3_SECRET_ACCESS_KEY")
    R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME", "larteh-lingo-audio")
    R2_PUBLIC_DOMAIN = os.getenv("R2_PUBLIC_DOMAIN") or os.getenv("S3_PUBLIC_URL_PREFIX")

    # Cloudflare R2 S3 API Endpoint: https://<account_id>.r2.cloudflarestorage.com
    if R2_ACCOUNT_ID:
        R2_ENDPOINT_URL = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
    else:
        R2_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")

    # Local Storage Fallback
    LOCAL_UPLOAD_FOLDER = os.getenv("LOCAL_UPLOAD_FOLDER", str(BASE_DIR / "uploads"))

    # -------------------------------------------------------------------------
    # CORS Allowed Origins
    # -------------------------------------------------------------------------
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]


class DevelopmentConfig(Config):
    """Development environment configuration."""
    DEBUG = True
    TESTING = False


class TestingConfig(Config):
    """Testing environment configuration."""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    STORAGE_BACKEND = "local"
    LOCAL_UPLOAD_FOLDER = str(BASE_DIR / "test_uploads")


class ProductionConfig(Config):
    """Production environment configuration."""
    DEBUG = False
    TESTING = False
    STORAGE_BACKEND = os.getenv("STORAGE_BACKEND", "r2")


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
