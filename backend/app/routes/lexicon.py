"""
Lexicon Blueprint: Audio Ingestion to Cloudflare R2, Querying, and Management.
"""

import os
import json
import uuid
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import or_

from backend.app.extensions import db
from backend.app.models.category import Category, slugify
from backend.app.models.lexicon import LexiconEntry, GrammaticalType
from backend.app.services.storage import (
    upload_audio_to_r2,
    delete_audio_from_r2,
    R2StorageError,
    InvalidAudioFormatError,
)
from backend.app.utils.validators import validate_audio_file

lexicon_bp = Blueprint("lexicon", __name__)


def _serialize_public_entry(entry: LexiconEntry) -> dict:
    """Serialize lexicon metadata without exposing private audio object keys."""
    data = entry.to_dict()
    data["audio_url"] = None
    return data


def generate_audio_storage_key(larteh_text: str, category_slug: str, original_filename: str) -> str:
    """
    Generate an organized, unique object key for Cloudflare R2:
    e.g., 'audio/days-of-the-week/idu_a1b2c3d4.wav' or 'audio/numbers/eko_e5f6g7h8.webm'
    """
    clean_text = slugify(larteh_text) or "recording"
    category_folder = category_slug or "general"
    
    # Extract extension
    _, ext = os.path.splitext(original_filename.lower() if original_filename else "")
    if not ext or ext.lstrip(".") not in current_app.config.get("ALLOWED_AUDIO_EXTENSIONS", {"wav", "webm"}):
        ext = ".webm"

    unique_suffix = uuid.uuid4().hex[:8]
    filename = f"{clean_text}_{unique_suffix}{ext}"
    return f"audio/{category_folder}/{filename}"


@lexicon_bp.route("/lexicon", methods=["GET"])
def get_lexicon():
    """
    Query and filter lexicon entries with search, categorization, and pagination.
    """
    larteh_text = request.args.get("larteh_text", "").strip()
    english_translation = request.args.get("english_translation", "").strip()
    category_id = request.args.get("category_id", type=int)
    query_text = request.args.get("q", "").strip()
    grammatical_type = request.args.get("grammatical_type", "").strip().lower()
    has_audio = request.args.get("has_audio", type=lambda v: v.lower() in ("true", "1", "yes"))

    page = max(request.args.get("page", 1, type=int), 1)
    per_page = min(max(request.args.get("per_page", 50, type=int), 1), 200)

    # Base select statement joined with Category
    stmt = db.select(LexiconEntry).outerjoin(Category)

    if query_text:
        term = f"%{query_text}%"
        stmt = stmt.where(
            or_(
                LexiconEntry.larteh_text.ilike(term),
                LexiconEntry.english_translation.ilike(term),
                LexiconEntry.phonetic_script.ilike(term),
            )
        )

    if larteh_text:
        stmt = stmt.where(LexiconEntry.larteh_text.ilike(f"%{larteh_text}%"))

    if english_translation:
        stmt = stmt.where(LexiconEntry.english_translation.ilike(f"%{english_translation}%"))

    if category_id is not None:
        stmt = stmt.where(LexiconEntry.category_id == category_id)

    if grammatical_type:
        stmt = stmt.where(LexiconEntry.grammatical_type == grammatical_type)

    if has_audio is not None:
        if has_audio:
            stmt = stmt.where(LexiconEntry.audio_url.isnot(None), LexiconEntry.audio_url != "")
        else:
            stmt = stmt.where(or_(LexiconEntry.audio_url.is_(None), LexiconEntry.audio_url == ""))

    paginated = db.paginate(
        stmt.order_by(LexiconEntry.larteh_text.asc()),
        page=page,
        per_page=per_page,
        error_out=False,
    )

    return jsonify({
        "status": "success",
        "data": [_serialize_public_entry(entry) for entry in paginated.items],
        "pagination": {
            "page": paginated.page,
            "per_page": paginated.per_page,
            "total": paginated.total,
            "total_pages": paginated.pages,
            "has_next": paginated.has_next,
            "has_prev": paginated.has_prev,
        },
    }), 200


@lexicon_bp.route("/lexicon/<uuid:entry_id>", methods=["GET"])
def get_lexicon_entry(entry_id: uuid.UUID):
    """Retrieve a single lexicon entry by its UUID."""
    entry = db.session.get(LexiconEntry, entry_id)
    if not entry:
        return jsonify({"status": "error", "message": "Lexicon entry not found."}), 404

    return jsonify({
        "status": "success",
        "data": _serialize_public_entry(entry),
    }), 200


@lexicon_bp.route("/lexicon/upload", methods=["POST"])
def upload_lexicon_entry():
    """
    Ingest a new lexicon entry with audio upload to Cloudflare R2 and PostgreSQL metadata.
    ---
    Accepts multipart/form-data:
        - audio: Audio binary file (.wav, .webm, .mp3, etc.)
        - larteh_text (str): Larteh spelling (e.g. 'Idu', 'Ekɔ') [Required]
        - phonetic_script (str): Phonetic pronunciation [Required]
        - english_translation (str): English meaning [Required]
        - category_id (int): Category foreign key [Optional]
        - grammatical_type (str): Classification [Optional, default 'noun']
        - speaker_name (str): Native speaker attribution [Optional, default 'Dad']
        - cultural_notes (str): Oral heritage or context notes [Optional]
    """
    # 1. Parse fields from request.form and handle embedded JSON 'metadata' string if present
    form_data = dict(request.form)
    if "metadata" in form_data:
        try:
            embedded_meta = json.loads(form_data.get("metadata", "{}"))
            form_data.update(embedded_meta)
        except json.JSONDecodeError:
            return jsonify({
                "status": "error",
                "message": "Malformed JSON in 'metadata' form field.",
            }), 400

    larteh_text = form_data.get("larteh_text", "").strip()
    phonetic_script = form_data.get("phonetic_script", "").strip()
    english_translation = form_data.get("english_translation", "").strip()
    raw_category_id = form_data.get("category_id")
    grammatical_type = form_data.get("grammatical_type", GrammaticalType.NOUN.value).strip().lower()
    speaker_name = form_data.get("speaker_name", "Dad").strip() or "Dad"
    cultural_notes = form_data.get("cultural_notes", "").strip() or None

    # Validate required text attributes
    missing = []
    if not larteh_text:
        missing.append("larteh_text")
    if not phonetic_script:
        missing.append("phonetic_script")
    if not english_translation:
        missing.append("english_translation")

    if missing:
        return jsonify({
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing)}",
        }), 400

    # Validate category foreign key if supplied
    category_id = None
    category_slug = "general"
    if raw_category_id:
        try:
            category_id = int(raw_category_id)
            cat = db.session.get(Category, category_id)
            if not cat:
                return jsonify({
                    "status": "error",
                    "message": f"Category with id {category_id} does not exist.",
                }), 400
            category_slug = cat.slug
        except (ValueError, TypeError):
            return jsonify({
                "status": "error",
                "message": f"Invalid category_id: '{raw_category_id}'. Must be an integer.",
            }), 400

    # 2. Process audio upload to Cloudflare R2
    audio_file = request.files.get("audio") or request.files.get("audio_file")
    audio_url = None

    if audio_file and audio_file.filename:
        # Validate format & mimetype
        is_valid, validation_err = validate_audio_file(audio_file)
        if not is_valid:
            return jsonify({
                "status": "error",
                "message": f"Audio validation failed: {validation_err}",
            }), 400

        # Construct structured destination key: audio/<category>/<larteh>_<uuid>.<ext>
        r2_object_key = generate_audio_storage_key(
            larteh_text=larteh_text,
            category_slug=category_slug,
            original_filename=audio_file.filename,
        )

        content_type = audio_file.content_type or "audio/webm"

        try:
            audio_url = upload_audio_to_r2(
                file_obj=audio_file.stream,
                filename=r2_object_key,
                content_type=content_type,
            )
        except InvalidAudioFormatError as err:
            return jsonify({"status": "error", "message": str(err)}), 400
        except R2StorageError as err:
            current_app.logger.exception("Failed to upload audio to Cloudflare R2.")
            return jsonify({
                "status": "error",
                "message": f"Object storage upload failed: {str(err)}",
            }), 502
        except Exception as err:
            current_app.logger.exception("Unexpected error during audio upload.")
            return jsonify({
                "status": "error",
                "message": f"Internal storage error: {str(err)}",
            }), 500

    # 3. Create and persist LexiconEntry in PostgreSQL
    entry = LexiconEntry(
        category_id=category_id,
        larteh_text=larteh_text,
        phonetic_script=phonetic_script,
        english_translation=english_translation,
        grammatical_type=grammatical_type,
        audio_url=audio_url,
        speaker_name=speaker_name,
        cultural_notes=cultural_notes,
    )

    db.session.add(entry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": "Lexicon entry created successfully.",
        "data": _serialize_public_entry(entry),
    }), 201


@lexicon_bp.route("/lexicon/<uuid:entry_id>", methods=["DELETE"])
def delete_lexicon_entry(entry_id: uuid.UUID):
    """
    Delete a lexicon entry and clean up its associated audio file in Cloudflare R2.
    """
    entry = db.session.get(LexiconEntry, entry_id)
    if not entry:
        return jsonify({"status": "error", "message": "Lexicon entry not found."}), 404

    # Remove audio blob from Cloudflare R2 if present
    if entry.audio_url:
        try:
            delete_audio_from_r2(entry.audio_url)
        except Exception as err:
            current_app.logger.warning(f"Could not delete R2 audio for entry {entry_id}: {err}")

    db.session.delete(entry)
    db.session.commit()

    return jsonify({
        "status": "success",
        "message": f"Lexicon entry '{entry.larteh_text}' deleted successfully.",
    }), 200


@lexicon_bp.route("/media/<path:filename>", methods=["GET"])
def serve_local_media(filename: str):
    """Keep local recording blobs private; no unauthenticated media serving."""
    return jsonify({
        "status": "error",
        "message": "Audio media is private and is not served publicly.",
    }), 404
