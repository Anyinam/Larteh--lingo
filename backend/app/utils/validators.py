"""
Input validation and file sanity helpers.
"""

from typing import Tuple, Optional
from flask import current_app


def validate_audio_file(file_storage) -> Tuple[bool, Optional[str]]:
    """
    Validate an uploaded Werkzeug FileStorage object.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not file_storage or not file_storage.filename:
        return False, "No audio file provided."

    filename = file_storage.filename.lower()
    allowed_exts = current_app.config.get("ALLOWED_AUDIO_EXTENSIONS", {"wav", "webm", "mp3", "ogg", "m4a"})

    has_valid_ext = any(filename.endswith(f".{ext}") for ext in allowed_exts)
    if not has_valid_ext:
        return False, f"Unsupported file extension. Allowed: {', '.join(sorted(allowed_exts))}"

    # Check content type if available
    content_type = file_storage.content_type
    allowed_mimes = current_app.config.get("ALLOWED_AUDIO_MIMETYPES")
    if allowed_mimes and content_type and content_type not in allowed_mimes:
        # Some browsers omit or send application/octet-stream for blobs
        if content_type not in {"application/octet-stream", "binary/octet-stream"}:
            return False, f"Unsupported MIME type: {content_type}"

    return True, None

