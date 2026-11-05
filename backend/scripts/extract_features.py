#!/usr/bin/env python3
"""Extract MFCC and log-mel arrays for recorded Studio vocabulary."""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
for search_path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if search_path not in sys.path:
        sys.path.insert(0, search_path)

import numpy as np

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary
from backend.app.models.vocabulary_recording import VocabularyRecording
from backend.app.services.ml_features import extract_acoustic_features
from backend.app.services.storage import download_audio_from_storage
from sqlalchemy import or_


def extract_dataset_features(
    output_dir: Path,
    split: Optional[str] = None,
) -> int:
    """Write compressed per-item features and a JSONL labels manifest."""
    app = create_app()
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.jsonl"

    with app.app_context(), manifest_path.open("w", encoding="utf-8") as manifest:
        db.create_all()
        stmt = db.select(Vocabulary).where(
            or_(
                Vocabulary.recording_status == "recorded",
                Vocabulary.recording_status == "verified",
            ),
            Vocabulary.audio_url.isnot(None),
            Vocabulary.audio_url != "",
            Vocabulary.larteh.isnot(None),
            Vocabulary.larteh != "",
        ).order_by(Vocabulary.id.asc())
        if split:
            stmt = stmt.where(Vocabulary.ml_split == split)

        count = 0
        entries = db.session.execute(stmt).scalars().all()
        recordings_stmt = (
            db.select(VocabularyRecording)
            .join(VocabularyRecording.prompt)
            .where(
                VocabularyRecording.audio_key.isnot(None),
                VocabularyRecording.audio_key != "",
                VocabularyRecording.larteh.isnot(None),
                VocabularyRecording.larteh != "",
            )
            .order_by(VocabularyRecording.id.asc())
        )
        if split:
            recordings_stmt = recordings_stmt.where(
                VocabularyRecording.ml_split == split
            )
        recordings = db.session.execute(recordings_stmt).scalars().all()

        dataset_items = [
            (
                str(entry.id),
                entry,
                entry.audio_url,
                entry.larteh,
                entry.phonetic,
                entry.ml_split,
                None,
            )
            for entry in entries
        ] + [
            (
                f"contributor-recording-{recording.id}",
                recording.prompt,
                recording.audio_key,
                recording.larteh,
                recording.phonetic,
                recording.ml_split,
                recording.contributor_id,
            )
            for recording in recordings
        ]
        for item_key, prompt, audio_key, larteh, phonetic, ml_split, contributor_id in dataset_items:
            features = extract_acoustic_features(download_audio_from_storage(audio_key))
            feature_path = output_dir / f"{item_key}.npz"
            np.savez_compressed(
                feature_path,
                mfcc=features["mfcc"],
                mel_spectrogram=features["mel_spectrogram"],
                frame_times_sec=features["frame_times_sec"],
            )
            manifest.write(json.dumps({
                "id": item_key,
                "prompt_id": prompt.id,
                "contributor_id": contributor_id,
                "features": feature_path.name,
                "text": larteh,
                "phonetic": phonetic,
                "translation": prompt.english,
                "category": prompt.category,
                "split": ml_split,
                "duration_ms": round(features["duration_sec"] * 1000),
                "sample_rate": features["sample_rate"],
            }, ensure_ascii=False) + "\n")
            count += 1

    print(f"Extracted features for {count} recording(s) into {output_dir}.")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "exports" / "features",
        help="Directory for compressed feature arrays and manifest.",
    )
    parser.add_argument(
        "--split",
        choices=("train", "validation", "test"),
        help="Only process one dataset split.",
    )
    args = parser.parse_args()
    extract_dataset_features(args.output_dir, args.split)


if __name__ == "__main__":
    main()
