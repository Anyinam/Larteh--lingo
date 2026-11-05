"""Prompt queue and recording upload endpoints for the Studio workflow."""

import re
from datetime import datetime, timezone

from flask import Blueprint, current_app, jsonify, request

from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary
from backend.app.services.storage import R2StorageError
from backend.app.utils.r2_uploader import upload_bytes_to_r2
from backend.app.utils.ml_audio_processor import process_and_resample_audio
from backend.app.utils.validators import validate_audio_file

studio_bp = Blueprint("studio", __name__)


def _progress_stats() -> dict:
    total = db.session.query(Vocabulary.id).count()
    completed = sum(
        db.session.query(Vocabulary.id)
        .filter_by(recording_status=status)
        .count()
        for status in ("recorded", "verified")
    )
    percentage = round((completed / total) * 100, 1) if total else 0
    return {"completed": completed, "total": total, "percentage": percentage}


@studio_bp.route("/next", methods=["GET"])
def get_next_studio_item():
    """Return the next pending prompt and current session progress."""
    stats = _progress_stats()
    item = (
        Vocabulary.query.filter_by(recording_status="pending")
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
    """Upload a prompt's audio and save any optional transcription fields."""
    vocab_item = db.session.get(Vocabulary, vocab_id)
    if vocab_item is None:
        return jsonify({"success": False, "message": "Vocabulary item not found."}), 404

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
    object_key = f"audio/{category or 'general'}/{vocab_item.id}.wav"

    try:
        object_key = upload_bytes_to_r2(normalized_audio, object_key, "audio/wav")
    except R2StorageError as err:
        current_app.logger.exception("Failed to upload Studio audio to object storage.")
        return jsonify({"success": False, "message": str(err)}), 502

    if "larteh" in request.form:
        vocab_item.larteh = request.form["larteh"].strip() or None
    if "phonetic" in request.form:
        vocab_item.phonetic = request.form["phonetic"].strip() or None
    vocab_item.audio_url = object_key
    vocab_item.recording_status = "recorded"
    vocab_item.recorded_at = datetime.now(timezone.utc)
    vocab_item.duration_ms = round(duration_sec * 1000)
    vocab_item.sample_rate = sample_rate

    db.session.commit()
    return jsonify({"success": True}), 200
