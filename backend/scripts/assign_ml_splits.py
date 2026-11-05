#!/usr/bin/env python3
"""Reproducibly assign recorded, transcribed prompts to ML dataset splits."""

import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
for search_path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if search_path not in sys.path:
        sys.path.insert(0, search_path)

from sqlalchemy import or_

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary
from backend.app.models.vocabulary_recording import VocabularyRecording


def assign_ml_splits(seed: int = 42) -> dict[str, int]:
    """Assign an approximate 80/10/10 split within each vocabulary category."""
    app = create_app()
    with app.app_context():
        db.create_all()
        entries = db.session.execute(
            db.select(Vocabulary)
            .where(
                or_(
                    Vocabulary.recording_status == "recorded",
                    Vocabulary.recording_status == "verified",
                ),
                Vocabulary.audio_url.isnot(None),
                Vocabulary.audio_url != "",
                Vocabulary.larteh.isnot(None),
                Vocabulary.larteh != "",
            )
            .order_by(Vocabulary.id.asc())
        ).scalars().all()
        recordings = db.session.execute(
            db.select(VocabularyRecording)
            .where(
                VocabularyRecording.audio_key.isnot(None),
                VocabularyRecording.audio_key != "",
                VocabularyRecording.larteh.isnot(None),
                VocabularyRecording.larteh != "",
            )
            .order_by(VocabularyRecording.id.asc())
        ).scalars().all()

        by_category: dict[str, list] = defaultdict(list)
        for entry in entries:
            by_category[entry.category].append(entry)
        for recording in recordings:
            by_category[recording.prompt.category].append(recording)

        counts = {"train": 0, "validation": 0, "test": 0}
        for category, category_entries in by_category.items():
            random.Random(f"{seed}:{category}").shuffle(category_entries)
            size = len(category_entries)
            validation_count = max(1, round(size * 0.1)) if size >= 3 else 0
            test_count = max(1, round(size * 0.1)) if size >= 3 else 0
            while validation_count + test_count >= size:
                if test_count >= validation_count and test_count:
                    test_count -= 1
                elif validation_count:
                    validation_count -= 1

            for index, entry in enumerate(category_entries):
                if index < validation_count:
                    entry.ml_split = "validation"
                elif index < validation_count + test_count:
                    entry.ml_split = "test"
                else:
                    entry.ml_split = "train"
                counts[entry.ml_split] += 1

        db.session.commit()
        print(
            "Assigned dataset splits: "
            f"{counts['train']} train, {counts['validation']} validation, "
            f"{counts['test']} test."
        )
        return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility.")
    args = parser.parse_args()
    assign_ml_splits(args.seed)


if __name__ == "__main__":
    main()
