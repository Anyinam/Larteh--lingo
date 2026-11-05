"""Prompt-based vocabulary records used by the Studio workflow."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column

from backend.app.extensions import db


class Vocabulary(db.Model):
    """A speaker prompt and its Larteh recording metadata."""

    __tablename__ = "vocabulary"

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, autoincrement=True)
    english: Mapped[str] = mapped_column(db.String(255), nullable=False, index=True)
    twi: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    category: Mapped[str] = mapped_column(
        db.String(100), nullable=False, default="general", index=True
    )
    larteh: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    phonetic: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    recording_status: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="pending", index=True
    )
    audio_url: Mapped[Optional[str]] = mapped_column(db.String(512), nullable=True)
    recorded_at: Mapped[Optional[datetime]] = mapped_column(
        db.DateTime(timezone=True), nullable=True
    )
    ml_split: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="train", index=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    sample_rate: Mapped[int] = mapped_column(db.Integer, nullable=False, default=16000)

    def __init__(
        self,
        english: str,
        category: str = "general",
        twi: Optional[str] = None,
        larteh: Optional[str] = None,
        phonetic: Optional[str] = None,
        recording_status: str = "pending",
        audio_url: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
        ml_split: str = "train",
        duration_ms: Optional[int] = None,
        sample_rate: int = 16000,
    ) -> None:
        self.english = english.strip()
        self.twi = twi.strip() if twi else None
        self.category = category.strip() if category else "general"
        self.larteh = larteh.strip() if larteh else None
        self.phonetic = phonetic.strip() if phonetic else None
        self.recording_status = recording_status
        self.audio_url = audio_url
        self.recorded_at = recorded_at
        self.ml_split = ml_split
        self.duration_ms = duration_ms
        self.sample_rate = sample_rate

    def to_dict(self) -> dict:
        """Return all vocabulary fields as JSON-compatible values."""
        return {
            "id": self.id,
            "english": self.english,
            "twi": self.twi,
            "category": self.category,
            "larteh": self.larteh,
            "phonetic": self.phonetic,
            "recording_status": self.recording_status,
            "audio_url": self.audio_url,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "ml_split": self.ml_split,
            "duration_ms": self.duration_ms,
            "sample_rate": self.sample_rate,
        }
