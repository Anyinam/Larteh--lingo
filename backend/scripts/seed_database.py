"""Idempotently seed the Studio vocabulary prompts from JSON files."""

import glob
import json
import sys
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
for search_path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary

app = create_app()


def populate_database(seed_directory: Optional[Path] = None) -> int:
    """Insert prompts not already present; return the number of new records."""
    directory = seed_directory or BACKEND_DIR / "scripts"
    seed_files = sorted(glob.glob(str(directory / "*.json")))
    if not seed_files:
        raise FileNotFoundError(f"No seed JSON files found in {directory}")

    inserted = 0
    with app.app_context():
        db.create_all()
        seen_english: set[str] = set()
        for file_path in seed_files:
            with open(file_path, "r", encoding="utf-8") as seed_file:
                records = json.load(seed_file)
            if not isinstance(records, list):
                raise ValueError(f"Seed file must contain a JSON array: {file_path}")

            for record in records:
                english = str(record.get("english", "")).strip()
                if not english:
                    raise ValueError(f"Seed record is missing its English prompt: {file_path}")
                if english in seen_english:
                    continue
                seen_english.add(english)
                if Vocabulary.query.filter_by(english=english).first() is not None:
                    continue

                db.session.add(
                    Vocabulary(
                        english=english,
                        twi=record.get("twi"),
                        category=record.get("category") or "general",
                        larteh=None,
                        phonetic=None,
                    )
                )
                inserted += 1

        db.session.commit()
    print(f"Seeded {inserted} new vocabulary prompt(s).")
    return inserted


if __name__ == "__main__":
    populate_database()
