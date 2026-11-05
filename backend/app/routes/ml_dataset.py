"""Dataset routes kept disabled while recordings remain private."""

from flask import Blueprint, jsonify

from backend.app.models.ml_dataset import DatasetExportLog

ml_dataset_bp = Blueprint("ml_dataset", __name__)


def _private_dataset_response():
    return jsonify({
        "status": "error",
        "message": "Audio dataset exports are disabled because recordings are private.",
    }), 410


@ml_dataset_bp.route("/dataset/vocabulary/manifest", methods=["GET"])
def export_vocabulary_manifest():
    """Keep the former unauthenticated Studio manifest endpoint disabled."""
    return _private_dataset_response()


@ml_dataset_bp.route("/dataset/export", methods=["GET"])
def export_ml_dataset():
    """Keep the former unauthenticated lexicon audio export disabled."""
    return _private_dataset_response()


@ml_dataset_bp.route("/dataset/logs", methods=["GET"])
def get_export_logs():
    """Retrieve export telemetry without including audio URLs or transcripts."""
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
