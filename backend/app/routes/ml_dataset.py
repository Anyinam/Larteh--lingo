"""
ML Dataset Export Blueprint: Hugging Face & Common Voice Ingestion Pipeline.

Streams curated speech datasets in JSONL / CSV formats for fine-tuning
automatic speech recognition (ASR) and text-to-speech (TTS) models.
"""

import io
import csv
import json
from datetime import datetime, timezone
from typing import Generator
from flask import Blueprint, request, Response, jsonify, stream_with_context

from backend.app.extensions import db
from backend.app.models.lexicon import LexiconEntry
from backend.app.models.ml_dataset import DatasetExportLog

ml_dataset_bp = Blueprint("ml_dataset", __name__)


@ml_dataset_bp.route("/dataset/export", methods=["GET"])
def export_ml_dataset():
    """
    Stream a Hugging Face / Common Voice compatible speech dataset.
    ---
    Query Parameters:
        format (str): 'jsonl' (default) or 'csv'.
        verified_only (bool): If True (default), exports only human-verified audio entries.
    Responses:
        200: Streamed JSONL or CSV file attachment.
        400: Invalid format requested.
    """
    export_format = request.args.get("format", "jsonl").strip().lower()
    verified_only_raw = request.args.get("verified_only", "true").strip().lower()
    verified_only = verified_only_raw not in ("false", "0", "no")

    if export_format not in ("jsonl", "csv"):
        return jsonify({
            "status": "error",
            "message": f"Unsupported export format '{export_format}'. Supported formats: 'jsonl', 'csv'.",
        }), 400

    # 1. Base Query: Only records with active audio recordings
    stmt = db.select(LexiconEntry).where(
        LexiconEntry.audio_url.isnot(None),
        LexiconEntry.audio_url != "",
    )

    if verified_only:
        stmt = stmt.where(LexiconEntry.is_verified.is_(True))

    stmt = stmt.order_by(LexiconEntry.created_at.asc())
    entries = db.session.execute(stmt).scalars().all()

    # 2. Record Export Audit Log
    log_entry = DatasetExportLog(export_format=export_format, record_count=len(entries))
    db.session.add(log_entry)
    db.session.commit()

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # 3. Stream JSONL Format (Hugging Face / WebDataset Standard)
    if export_format == "jsonl":
        def generate_jsonl() -> Generator[str, None, None]:
            for entry in entries:
                record = {
                    "audio": entry.audio_url,
                    "text": entry.larteh_text,
                    "phonetic": entry.phonetic_script,
                    "translation": entry.english_translation,
                    "duration": entry.audio_duration_sec,
                }
                yield json.dumps(record, ensure_ascii=False) + "\n"

        filename = f"larteh_dataset_{timestamp_str}.jsonl"
        return Response(
            stream_with_context(generate_jsonl()),
            mimetype="application/x-ndjson; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "X-Dataset-Total-Records": str(len(entries)),
            },
        )

    # 4. Stream CSV Format (Common Voice / Kaldi / Fairseq Standard)
    def generate_csv() -> Generator[str, None, None]:
        string_buffer = io.StringIO()
        writer = csv.writer(string_buffer)

        # Header row
        writer.writerow(["audio", "text", "phonetic", "translation", "duration"])
        yield string_buffer.getvalue()
        string_buffer.seek(0)
        string_buffer.truncate(0)

        for entry in entries:
            writer.writerow([
                entry.audio_url,
                entry.larteh_text,
                entry.phonetic_script,
                entry.english_translation,
                entry.audio_duration_sec if entry.audio_duration_sec is not None else "",
            ])
            yield string_buffer.getvalue()
            string_buffer.seek(0)
            string_buffer.truncate(0)

    filename = f"larteh_dataset_{timestamp_str}.csv"
    return Response(
        stream_with_context(generate_csv()),
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Dataset-Total-Records": str(len(entries)),
        },
    )


@ml_dataset_bp.route("/dataset/logs", methods=["GET"])
def get_export_logs():
    """Retrieve telemetry history of dataset exports."""
    logs = (
        DatasetExportLog.query.order_by(DatasetExportLog.created_at.desc())
        .limit(50)
        .all()
    )
    return jsonify({
        "status": "success",
        "count": len(logs),
        "data": [log.to_dict() for log in logs],
    }), 200

