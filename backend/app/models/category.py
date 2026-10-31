"""
Category Model for Larteh Lexicon Taxonomy.
"""

from datetime import datetime, timezone
from typing import Optional
import re
from backend.app.extensions import db


def slugify(text: str) -> str:
    """Generate a clean URL-friendly slug from text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


class Category(db.Model):
    """
    Taxonomic category grouping related lexical entries
    (e.g., 'Numbers', 'Days of the Week', 'Kinship', 'Greetings', 'Flora & Fauna').
    """

    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False, unique=True, index=True)
    slug = db.Column(db.String(120), nullable=False, unique=True, index=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    entries = db.relationship(
        "LexiconEntry",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="select",
        order_by="LexiconEntry.larteh_text",
    )

    def __init__(self, name: str, slug: Optional[str] = None, description: Optional[str] = None):
        self.name = name.strip()
        self.slug = slugify(slug or name)
        self.description = description.strip() if description else None

    def to_dict(self, include_entries_count: bool = True) -> dict:
        """Serialize category to a JSON-compatible dictionary."""
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_entries_count:
            data["entries_count"] = len(self.entries) if self.entries is not None else 0
        return data

    def __repr__(self) -> str:
        return f"<Category id={self.id} slug='{self.slug}'>"

