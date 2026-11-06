"""Private, contributor-specific recordings of vocabulary prompts."""

from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.extensions import db

if TYPE_CHECKING:
    from backend.app.models.vocabulary import Vocabulary


class VocabularyRecording(db.Model):
    """One contributor's recording and transcription for one prompt."""

    __tablename__ = "vocabulary_recordings"
    __table_args__ = (
        UniqueConstraint(
            "vocabulary_id",
            "contributor_id",
            name="uq_vocabulary_recording_contributor",
        ),
    )

    id: Mapped[int] = mapped_column(db.Integer, primary_key=True, autoincrement=True)
    vocabulary_id: Mapped[int] = mapped_column(
        db.ForeignKey("vocabulary.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contributor_id: Mapped[str] = mapped_column(db.String(36), nullable=False, index=True)
    larteh: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    phonetic: Mapped[Optional[str]] = mapped_column(db.String(255), nullable=True)
    audio_key: Mapped[str] = mapped_column(db.String(512), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    ml_split: Mapped[str] = mapped_column(
        db.String(20), nullable=False, default="train", index=True
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(db.Integer, nullable=True)
    sample_rate: Mapped[int] = mapped_column(db.Integer, nullable=False, default=16000)

    prompt: Mapped["Vocabulary"] = db.relationship(back_populates="recordings")

    def __init__(
        self,
        vocabulary_id: int,
        contributor_id: str,
        audio_key: str,
        larteh: Optional[str] = None,
        phonetic: Optional[str] = None,
        recorded_at: Optional[datetime] = None,
        ml_split: str = "train",
        duration_ms: Optional[int] = None,
        sample_rate: int = 16000,
    ) -> None:
        self.vocabulary_id = vocabulary_id
        self.contributor_id = contributor_id
        self.audio_key = audio_key
        self.larteh = larteh.strip() if larteh else None
        self.phonetic = phonetic.strip() if phonetic else None
        if recorded_at is not None:
            self.recorded_at = recorded_at
        self.ml_split = ml_split
        self.duration_ms = duration_ms
        self.sample_rate = sample_rate
