"""Byte-oriented adapter for the configured audio storage backend."""

from backend.app.services.storage import upload_audio_to_r2


def upload_bytes_to_r2(
    audio_bytes: bytes,
    object_key: str,
    content_type: str = "audio/wav",
) -> str:
    """Upload audio bytes using the project's R2 or local-fallback storage."""
    return upload_audio_to_r2(
        file_obj=audio_bytes,
        filename=object_key,
        content_type=content_type,
    )
