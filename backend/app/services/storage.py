"""
Cloudflare R2 Object Storage Service for Larteh Audio Blobs.

Provides an enterprise-grade, S3-compatible interface for storing lossless audio
recordings (.wav / .webm) in Cloudflare R2 with automatic CDN URL generation,
lifecycle deletion, and local fallback for offline development.
"""

import os
import io
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Union, BinaryIO, Optional, Tuple
from urllib.parse import urlparse
from werkzeug.utils import secure_filename
import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError
from flask import current_app

logger = logging.getLogger("larteh.storage")


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------
class R2StorageError(Exception):
    """Base exception for Cloudflare R2 storage operations."""
    pass


class R2ConfigurationError(R2StorageError):
    """Raised when R2 credentials or bucket configuration is missing."""
    pass


class InvalidAudioFormatError(R2StorageError):
    """Raised when an uploaded audio blob has an invalid extension or MIME type."""
    pass


# ---------------------------------------------------------------------------
# Storage Implementation
# ---------------------------------------------------------------------------
class CloudflareR2Storage:
    """Manages audio file lifecycle in Cloudflare R2."""

    def __init__(self, app=None):
        self.app = app
        self._client = None

    def get_client(self):
        """
        Construct and cache the boto3 S3 client targeted at Cloudflare R2.
        
        Cloudflare R2 requires:
          - endpoint_url: https://<account_id>.r2.cloudflarestorage.com
          - region_name: 'auto'
          - signature_version: 's3v4'
          - addressing_style: 'path'
        """
        if self._client is not None:
            return self._client

        account_id = current_app.config.get("R2_ACCOUNT_ID")
        access_key = current_app.config.get("R2_ACCESS_KEY_ID")
        secret_key = current_app.config.get("R2_SECRET_ACCESS_KEY")
        endpoint_url = current_app.config.get("R2_ENDPOINT_URL")

        if not endpoint_url and account_id:
            endpoint_url = f"https://{account_id}.r2.cloudflarestorage.com"

        if not access_key or not secret_key:
            logger.warning("Cloudflare R2 credentials not fully set; R2 client cannot be created.")
            return None

        if not endpoint_url:
            raise R2ConfigurationError(
                "Cloudflare R2 endpoint URL missing. Please set R2_ACCOUNT_ID or R2_ENDPOINT_URL."
            )

        boto_config = BotoConfig(
            s3={"addressing_style": "path"},
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30,
        )

        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="auto",
            config=boto_config,
        )
        return self._client

    def is_configured(self) -> bool:
        """Check whether Cloudflare R2 credentials are fully populated in config."""
        access_key = current_app.config.get("R2_ACCESS_KEY_ID")
        secret_key = current_app.config.get("R2_SECRET_ACCESS_KEY")
        endpoint = current_app.config.get("R2_ENDPOINT_URL") or current_app.config.get("R2_ACCOUNT_ID")
        return bool(access_key and secret_key and endpoint)

    def validate_audio(self, filename: str, content_type: Optional[str] = None) -> None:
        """
        Validate audio filename extension and MIME type against allowed configurations.
        """
        ext = os.path.splitext(filename)[1].lstrip(".").lower()
        allowed_exts = current_app.config.get("ALLOWED_AUDIO_EXTENSIONS", {"wav", "webm", "mp3", "ogg", "m4a"})
        if ext and ext not in allowed_exts:
            raise InvalidAudioFormatError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(allowed_exts))}"
            )

        allowed_mimes = current_app.config.get("ALLOWED_AUDIO_MIMETYPES")
        if allowed_mimes and content_type:
            # Normalize and tolerate standard browser video/webm or application/octet-stream tags
            clean_mime = content_type.split(";")[0].strip().lower()
            if clean_mime not in allowed_mimes and clean_mime not in {"application/octet-stream", "binary/octet-stream"}:
                raise InvalidAudioFormatError(
                    f"Unsupported audio MIME type '{content_type}'. Allowed types: {', '.join(sorted(allowed_mimes))}"
                )

    def upload_audio_to_r2(
        self,
        file_obj: Union[BinaryIO, bytes, io.BytesIO],
        filename: str,
        content_type: str = "audio/webm",
    ) -> str:
        """
        Uploads an audio file or byte buffer to the Cloudflare R2 bucket.

        Args:
            file_obj: File-like object (e.g. Werkzeug FileStorage.stream) or raw bytes.
            filename: Destination object key (e.g. 'audio/days/idu_abc123.wav').
            content_type: MIME type for the audio blob.

        Returns:
            str: Full public URL for the uploaded audio (e.g. 'https://media.lartehlingo.org/audio/...').
        """
        # Clean destination key path
        clean_key = filename.lstrip("/")
        self.validate_audio(clean_key, content_type)

        bucket_name = current_app.config.get("R2_BUCKET_NAME", "larteh-lingo-audio")
        public_domain = current_app.config.get("R2_PUBLIC_DOMAIN")

        # Fallback to local storage if R2 is not configured or STORAGE_BACKEND == 'local'
        backend = current_app.config.get("STORAGE_BACKEND", "r2")
        if backend == "local" or not self.is_configured():
            logger.info("R2 not active or storage backend is local. Persisting to local disk fallback.")
            return self._save_to_local_fallback(file_obj, clean_key)

        client = self.get_client()
        if not client:
            raise R2ConfigurationError("Unable to initialize Cloudflare R2 client.")

        # Prepare payload
        if isinstance(file_obj, bytes):
            stream = io.BytesIO(file_obj)
        else:
            stream = file_obj

        try:
            # Rewind stream before upload
            if hasattr(stream, "seek"):
                stream.seek(0)

            # Upload to Cloudflare R2 via S3 API
            client.upload_fileobj(
                Fileobj=stream,
                Bucket=bucket_name,
                Key=clean_key,
                ExtraArgs={
                    "ContentType": content_type,
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )
            logger.info(f"Successfully uploaded audio to R2 bucket '{bucket_name}' key '{clean_key}'")

            # Construct public CDN URL
            if public_domain:
                return f"{public_domain.rstrip('/')}/{clean_key}"

            # Fallback to direct R2 endpoint path if custom public domain is not yet mapped
            endpoint_url = current_app.config.get("R2_ENDPOINT_URL")
            if endpoint_url:
                return f"{endpoint_url.rstrip('/')}/{bucket_name}/{clean_key}"

            return f"https://{bucket_name}.r2.cloudflarestorage.com/{clean_key}"

        except (ClientError, BotoCoreError) as err:
            logger.error(f"Cloudflare R2 upload error for key '{clean_key}': {err}")
            raise R2StorageError(f"Cloudflare R2 upload failed: {str(err)}") from err

    def delete_audio_from_r2(self, filename_or_url: str) -> bool:
        """
        Delete an audio object from the Cloudflare R2 bucket.

        Args:
            filename_or_url: Either the raw object key ('audio/days/idu.wav')
                             or a full public URL ('https://media.lartehlingo.org/audio/days/idu.wav').

        Returns:
            bool: True if deletion succeeded or file did not exist; False on failure.
        """
        if not filename_or_url:
            return False

        # Extract the object key if full URL was supplied
        object_key = filename_or_url
        if "://" in filename_or_url:
            parsed = urlparse(filename_or_url)
            # Remove leading slash
            object_key = parsed.path.lstrip("/")

        # Handle local disk fallback deletion
        if object_key.startswith("api/v1/media/"):
            object_key = object_key.replace("api/v1/media/", "", 1)
            local_path = Path(current_app.config["LOCAL_UPLOAD_FOLDER"]) / object_key
            if local_path.exists():
                try:
                    local_path.unlink()
                    logger.info(f"Deleted local audio file: {local_path}")
                    return True
                except OSError as err:
                    logger.error(f"Failed to delete local audio file: {err}")
                    return False
            return True

        if not self.is_configured():
            logger.warning("R2 storage not configured; skipping remote R2 deletion.")
            return False

        bucket_name = current_app.config.get("R2_BUCKET_NAME", "larteh-lingo-audio")
        client = self.get_client()

        try:
            client.delete_object(Bucket=bucket_name, Key=object_key)
            logger.info(f"Deleted object '{object_key}' from R2 bucket '{bucket_name}'")
            return True
        except (ClientError, BotoCoreError) as err:
            logger.error(f"Failed to delete '{object_key}' from R2: {err}")
            raise R2StorageError(f"Cloudflare R2 deletion failed: {str(err)}") from err

    def _save_to_local_fallback(self, file_obj: Union[BinaryIO, bytes, io.BytesIO], key: str) -> str:
        """Persist audio blob to local disk when R2 is offline or in development."""
        local_base = Path(current_app.config["LOCAL_UPLOAD_FOLDER"])
        dest_path = local_base / key
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if isinstance(file_obj, bytes):
            with open(dest_path, "wb") as f:
                f.write(file_obj)
        else:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            with open(dest_path, "wb") as f:
                f.write(file_obj.read())

        return f"/api/v1/media/{key}"


# ---------------------------------------------------------------------------
# Module Singleton & Standalone Functions
# ---------------------------------------------------------------------------
cloudflare_storage = CloudflareR2Storage()

# Backwards compatibility alias for storage_service
storage_service = cloudflare_storage


def upload_audio_to_r2(
    file_obj: Union[BinaryIO, bytes, io.BytesIO],
    filename: str,
    content_type: str = "audio/webm",
) -> str:
    """Convenience wrapper for CloudflareR2Storage.upload_audio_to_r2."""
    return cloudflare_storage.upload_audio_to_r2(file_obj, filename, content_type)


def delete_audio_from_r2(filename_or_url: str) -> bool:
    """Convenience wrapper for CloudflareR2Storage.delete_audio_from_r2."""
    return cloudflare_storage.delete_audio_from_r2(filename_or_url)
