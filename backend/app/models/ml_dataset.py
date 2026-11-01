"""
ML Dataset Models and Export Telemetry.

Extends the Larteh language engine with schema support for speech ML pipelines,
fine-tuning benchmarks (Common Voice / Hugging Face datasets), and export auditing.
"""

from datetime import datetime, timezone
from typing import Optional
from backend.app.extensions import db
from backend.app.models.lexicon import LexiconEntry, GrammaticalType


class DatasetExportLog(db.Model):
    """
    Audit log tracking ML dataset batch exports (JSONL / CSV)
    for model training benchmarks and diaspora distribution.
    """

    __tablename__ = "dataset_export_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    export_format = db.Column(db.String(20), nullable=False)  # 'jsonl' | 'csv'
    record_count = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __init__(self, export_format: str, record_count: int = 0):
        self.export_format = export_format.lower().strip()
        self.record_count = max(0, record_count)

    def to_dict(self) -> dict:
        """Serialize export log entry to a JSON-compatible dictionary."""
        return {
            "id": self.id,
            "export_format": self.export_format,
            "record_count": self.record_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<DatasetExportLog id={self.id} format='{self.export_format}' count={self.record_count}>"


__all__ = ["DatasetExportLog", "LexiconEntry", "GrammaticalType"]

