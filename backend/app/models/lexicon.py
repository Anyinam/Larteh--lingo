"""
Lexicon Entry Model for Larteh (Gua) Language Records.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional
import enum
from backend.app.extensions import db


class GrammaticalType(str, enum.Enum):
    """Standard grammatical classifications for lexicon entries."""
    NOUN = "noun"
    VERB = "verb"
    ADJECTIVE = "adjective"
    ADVERB = "adverb"
    PRONOUN = "pronoun"
    CARDINAL_NUMBER = "cardinal_number"
    ORDINAL_NUMBER = "ordinal_number"
    GREETING = "greeting"
    PHRASE = "phrase"
    IDIOM = "idiom"
    INTERJECTION = "interjection"
    CONJUNCTION = "conjunction"
    PREPOSITION = "preposition"
    DAY_OF_WEEK = "day_of_week"
    OTHER = "other"

    @classmethod
    def list_values(cls):
        return [item.value for item in cls]


class LexiconEntry(db.Model):
    """
    Core phonetic, textual, and audio representation of a Larteh (Gua) word or phrase.
    """

    __tablename__ = "lexicon_entries"

    # UUID Primary Key (Native UUID on PostgreSQL, Uuid/VARCHAR on SQLite)
    id = db.Column(db.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Foreign Key to taxonomy Category
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Linguistic Attributes
    larteh_text = db.Column(db.String(255), nullable=False, index=True)
    phonetic_script = db.Column(db.String(255), nullable=False)
    english_translation = db.Column(db.String(255), nullable=False, index=True)
    grammatical_type = db.Column(
        db.String(50),
        nullable=False,
        default=GrammaticalType.NOUN.value,
        index=True,
    )

    # Media & Provenance
    audio_url = db.Column(db.String(1024), nullable=True)
    speaker_name = db.Column(db.String(100), nullable=False, default="Dad")
    cultural_notes = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    category = db.relationship("Category", back_populates="entries")

    def __init__(
        self,
        larteh_text: str,
        phonetic_script: str,
        english_translation: str,
        category_id: Optional[int] = None,
        grammatical_type: str = GrammaticalType.NOUN.value,
        audio_url: Optional[str] = None,
        speaker_name: str = "Dad",
        cultural_notes: Optional[str] = None,
        id: Optional[uuid.UUID] = None,
        created_at: Optional[datetime] = None,
    ):
        if id is not None:
            self.id = id
        self.category_id = category_id
        self.larteh_text = larteh_text.strip() if larteh_text else ""
        self.phonetic_script = phonetic_script.strip() if phonetic_script else ""
        self.english_translation = english_translation.strip() if english_translation else ""
        self.grammatical_type = grammatical_type or GrammaticalType.NOUN.value
        self.audio_url = audio_url
        self.speaker_name = speaker_name.strip() if speaker_name else "Dad"
        self.cultural_notes = cultural_notes.strip() if cultural_notes else None
        if created_at is not None:
            self.created_at = created_at

    def to_dict(self) -> dict:
        """Serialize lexicon entry to a JSON-compatible dictionary."""
        return {
            "id": str(self.id),
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "category_slug": self.category.slug if self.category else None,
            "larteh_text": self.larteh_text,
            "phonetic_script": self.phonetic_script,
            "english_translation": self.english_translation,
            "grammatical_type": self.grammatical_type,
            "audio_url": self.audio_url,
            "speaker_name": self.speaker_name,
            "cultural_notes": self.cultural_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<LexiconEntry id={self.id} text='{self.larteh_text}' ({self.english_translation})>"

