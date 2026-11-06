"""Prompt queue and recording upload endpoints for the Studio workflow."""

import re
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request
from sqlalchemy.exc import IntegrityError

from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary
from backend.app.models.vocabulary_recording import VocabularyRecording
from backend.app.services.storage import R2StorageError
from backend.app.utils.r2_uploader import upload_bytes_to_r2
from backend.app.utils.ml_audio_processor import process_and_resample_audio
from backend.app.utils.validators import validate_audio_file

studio_bp = Blueprint("studio", __name__)


def _get_contributor_id():
    contributor_id = request.headers.get("X-Contributor-ID", "").strip().lower()
    try:
        normalized_id = str(uuid.UUID(contributor_id))
    except (ValueError, AttributeError):
        return None
    return normalized_id if normalized_id == contributor_id else None


def _progress_stats(contributor_id: str) -> dict:
    total = db.session.query(Vocabulary.id).count()
    completed = db.session.query(VocabularyRecording.id).filter_by(
        contributor_id=contributor_id
    ).count()
    family_completed = db.session.query(
        db.select(VocabularyRecording.vocabulary_id)
        .union(
            db.select(Vocabulary.id).where(
                Vocabulary.recording_status.in_(("recorded", "verified"))
            )
        )
        .subquery()
    ).count()
    percentage = round((completed / total) * 100, 1) if total else 0
    return {
        "completed": completed,
        "family_completed": family_completed,
        "total": total,
        "percentage": percentage,
    }


@studio_bp.route("/next", methods=["GET"])
def get_next_studio_item():
    """Return the next prompt not yet recorded by this browser contributor."""
    contributor_id = _get_contributor_id()
    if contributor_id is None:
        return jsonify({
            "success": False,
            "message": "A valid browser contributor ID is required.",
        }), 400

    stats = _progress_stats(contributor_id)
    item = (
        Vocabulary.query.filter(
            ~Vocabulary.recordings.any(
                VocabularyRecording.contributor_id == contributor_id
            )
        )
        .order_by(Vocabulary.id.asc())
        .first()
    )
    if item is None:
        return jsonify({
            "success": True,
            "message": "All vocabulary items have been recorded.",
            "stats": stats,
        }), 404

    item_data = item.to_dict()
    item_data["audio_url"] = None
    return jsonify({"success": True, "item": item_data, "stats": stats}), 200


@studio_bp.route("/upload/<int:vocab_id>", methods=["POST"])
def upload_studio_recording(vocab_id: int):
    """Upload one recording per prompt for this browser contributor."""
    contributor_id = _get_contributor_id()
    if contributor_id is None:
        return jsonify({
            "success": False,
            "message": "A valid browser contributor ID is required.",
        }), 400

    vocab_item = db.session.get(Vocabulary, vocab_id)
    if vocab_item is None:
        return jsonify({"success": False, "message": "Vocabulary item not found."}), 404
    existing_recording = VocabularyRecording.query.filter_by(
        vocabulary_id=vocab_id,
        contributor_id=contributor_id,
    ).first()
    if existing_recording is not None:
        return jsonify({
            "success": False,
            "message": "You have already saved this prompt from this browser. Load the next prompt to continue.",
        }), 409

    audio_file = request.files.get("audio")
    if audio_file is None or not audio_file.filename:
        return jsonify({"success": False, "message": "Audio recording is required."}), 400

    is_valid, validation_error = validate_audio_file(audio_file)
    if not is_valid:
        return jsonify({"success": False, "message": validation_error}), 400

    audio_bytes = audio_file.read()
    if not audio_bytes:
        return jsonify({"success": False, "message": "Audio recording is empty."}), 400
    try:
        normalized_audio, duration_sec, sample_rate = process_and_resample_audio(audio_bytes)
    except (TypeError, ValueError) as err:
        return jsonify({"success": False, "message": f"Invalid audio recording: {err}"}), 400

    category = re.sub(r"[^a-z0-9_-]+", "-", vocab_item.category.lower()).strip("-")
    object_key = (
        f"audio/{category or 'general'}/{vocab_item.id}/"
        f"{contributor_id}/{uuid.uuid4().hex}.wav"
    )

    try:
        object_key = upload_bytes_to_r2(normalized_audio, object_key, "audio/wav")
    except R2StorageError as err:
        current_app.logger.exception("Failed to upload Studio audio to object storage.")
        return jsonify({"success": False, "message": str(err)}), 502

    recording = VocabularyRecording(
        vocabulary_id=vocab_item.id,
        contributor_id=contributor_id,
        audio_key=object_key,
        larteh=request.form.get("larteh", ""),
        phonetic=request.form.get("phonetic", ""),
        recorded_at=datetime.now(timezone.utc),
        duration_ms=round(duration_sec * 1000),
        sample_rate=sample_rate,
    )
    db.session.add(recording)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            "success": False,
            "message": "You have already saved this prompt from this browser. Load the next prompt to continue.",
        }), 409
    return jsonify({"success": True}), 200
