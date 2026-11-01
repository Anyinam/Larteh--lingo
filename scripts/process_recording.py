#!/usr/bin/env python3
"""
CLI Audio Splitter & Automated Cloudflare R2 Ingestion Engine for Larteh Lingo.

Takes a continuous native-speaker studio recording (.wav/.webm/.mp3) and a sequential
metadata JSON list, slices words on inter-word silence intervals using pydub,
normalizes each chunk, uploads directly to Cloudflare R2, and optionally registers
the records in the PostgreSQL database.

Usage:
    python scripts/process_recording.py <audio_path> <metadata_json_path> [options]

Examples:
    # Dry-run slice inspection without uploading
    python scripts/process_recording.py "recordings/audio-daysofthe week.wav" seeds/days_of_the_week.json --dry-run

    # Slice, upload to Cloudflare R2, and save entries to PostgreSQL
    python scripts/process_recording.py recordings/session_01.wav seeds/days_of_the_week.json --save-db

    # Fine-tune silence thresholds for audio with background hum
    python scripts/process_recording.py session.wav seeds.json --silence-thresh -38 --min-silence 250
"""

import sys
import io
import json
import uuid
import argparse
from pathlib import Path
from typing import List, Dict, Any, Optional

# Locate project base directory and ensure it's in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Pydub imports
from pydub import AudioSegment
from pydub.silence import split_on_silence
from pydub.effects import normalize

# Application backend imports
from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.category import Category, slugify
from backend.app.models.lexicon import LexiconEntry, GrammaticalType
from backend.app.services.storage import upload_audio_to_r2


def load_metadata_sequence(json_path: Path) -> List[Dict[str, Any]]:
    """Load and validate the sequential metadata JSON file."""
    if not json_path.exists():
        raise FileNotFoundError(f"Metadata JSON file not found at: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list) or len(data) == 0:
        raise ValueError("Metadata JSON must contain a non-empty JSON array of lexical objects.")

    return data


def slice_recording(
    audio_path: Path,
    min_silence_len: int = 500,
    silence_thresh: int = -35,
    keep_silence: int = 150,
) -> List[AudioSegment]:
    """
    Load continuous master audio and slice into individual utterance segments.

    Args:
        audio_path: Path to continuous recording (.wav, .mp3, etc.)
        min_silence_len: Minimum pause duration (ms) considered silence.
        silence_thresh: Silence threshold (dBFS). Chunks quieter than this are treated as silence.
        keep_silence: Milliseconds of padding retained around start and end of slices.

    Returns:
        List of normalized AudioSegment instances.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"Master audio file not found at: {audio_path}")

    print(f"\n🎧 Loading audio file: {audio_path.name}...")
    file_format = audio_path.suffix.lstrip(".").lower()
    if not file_format:
        file_format = "wav"

    audio = AudioSegment.from_file(str(audio_path), format=file_format)
    duration_sec = len(audio) / 1000.0
    print(f"   • Duration: {duration_sec:.2f}s ({len(audio)} ms)")
    print(f"   • Channels: {audio.channels} ({'Mono' if audio.channels == 1 else 'Stereo'})")
    print(f"   • Frame Rate: {audio.frame_rate} Hz")
    print(f"   • Average dBFS: {audio.dBFS:.2f} dBFS")

    # If silence threshold is 0, calculate dynamic relative threshold
    effective_thresh = silence_thresh
    if silence_thresh == 0:
        effective_thresh = int(audio.dBFS - 14)
        print(f"   • Dynamic Silence Threshold calculated: {effective_thresh} dBFS")
    else:
        print(f"   • Configured Silence Threshold: {effective_thresh} dBFS")

    print(f"   • Splitting on silence (min_silence={min_silence_len}ms, padding={keep_silence}ms)...")
    raw_chunks = split_on_silence(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=effective_thresh,
        keep_silence=keep_silence,
    )

    # Normalize volume of each chunk to -1.0 dBFS for uniform speech output
    normalized_chunks = [normalize(chunk) for chunk in raw_chunks]
    return normalized_chunks


def persist_lexicon_entry(
    app: Any,
    category_slug: str,
    category_name: str,
    larteh_text: str,
    phonetic: str,
    english: str,
    grammatical_type: str,
    speaker: str,
    cultural_notes: Optional[str],
    r2_url: str,
) -> None:
    """Save or update a single lexicon entry in PostgreSQL inside an app context."""
    with app.app_context():
        cat = Category.query.filter_by(slug=category_slug).first()
        if not cat:
            cat = Category(name=category_name, slug=category_slug)
            db.session.add(cat)
            db.session.flush()

        entry = LexiconEntry.query.filter_by(
            larteh_text=larteh_text,
            category_id=cat.id,
        ).first()

        clean_type = grammatical_type or GrammaticalType.NOUN.value

        if not entry:
            entry = LexiconEntry(
                larteh_text=larteh_text,
                phonetic_script=phonetic,
                english_translation=english,
                category_id=cat.id,
                grammatical_type=clean_type,
                audio_url=r2_url,
                speaker_name=speaker,
                cultural_notes=cultural_notes,
            )
            db.session.add(entry)
        else:
            entry.audio_url = r2_url
            entry.phonetic_script = phonetic
            entry.english_translation = english
            entry.grammatical_type = clean_type
            entry.cultural_notes = cultural_notes

        db.session.commit()


def process_and_ingest(
    audio_path: Path,
    metadata_path: Path,
    min_silence_len: int = 500,
    silence_thresh: int = -35,
    keep_silence: int = 150,
    dry_run: bool = False,
    save_local: Optional[Path] = None,
    save_db: bool = False,
    speaker_override: Optional[str] = None,
) -> None:
    """Orchestrates slicing, R2 streaming, and metadata linkage."""
    # Always create Flask app and establish context so current_app works for uploads
    flask_app = create_app()

    with flask_app.app_context():
        # 1. Load inputs
        metadata = load_metadata_sequence(metadata_path)
        chunks = slice_recording(
            audio_path=audio_path,
            min_silence_len=min_silence_len,
            silence_thresh=silence_thresh,
            keep_silence=keep_silence,
        )

        print(f"\n✂️ Slicing complete: Extracted {len(chunks)} chunks for {len(metadata)} metadata items.")

        # Alignment diagnostics
        if len(chunks) != len(metadata):
            print("\n⚠️  ALIGNMENT MISMATCH DETECTED:")
            print(f"    Expected: {len(metadata)} items (from {metadata_path.name})")
            print(f"    Received: {len(chunks)} audio segments (from {audio_path.name})")
            print("    Tips to calibrate:")
            print("      - If too many chunks were cut: increase --min-silence (e.g. 700) or decrease --silence-thresh (e.g. -40)")
            print("      - If words were fused together: decrease --min-silence (e.g. 400) or increase --silence-thresh (e.g. -30)")
            print("    Proceeding with 1:1 mapping up to minimum length.\n")

        limit = min(len(chunks), len(metadata))

        if save_local:
            save_local.mkdir(parents=True, exist_ok=True)

        results: List[Dict[str, Any]] = []

        print("\n🚀 Processing & Ingesting Audio Segments:")
        print("=" * 80)
        print(f"{'#':<3} | {'Larteh Text':<15} | {'Phonetic':<15} | {'English':<15} | Status")
        print("=" * 80)

        for i in range(limit):
            chunk = chunks[i]
            meta = metadata[i]

            larteh_text: str = str(meta.get("larteh", "")).strip()
            phonetic: str = str(meta.get("phonetic", "")).strip()
            english: str = str(meta.get("english", "")).strip()
            category_slug: str = str(meta.get("category", "general"))
            category_name: str = str(meta.get("category_name", category_slug.replace("-", " ").title()))
            speaker: str = speaker_override or str(meta.get("speaker_name", "Dad"))
            grammatical_type: str = str(meta.get("grammatical_type", "noun"))
            cultural_notes: Optional[str] = meta.get("cultural_notes")

            slug_name = slugify(larteh_text) or f"entry_{i+1}"
            unique_id = uuid.uuid4().hex[:8]
            filename = f"{slug_name}_{unique_id}.wav"
            r2_key = f"audio/{category_slug}/{filename}"

            # Export chunk to in-memory WAV buffer (16-bit PCM WAV)
            wav_buffer = io.BytesIO()
            chunk.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            chunk_bytes = wav_buffer.getvalue()

            # Optional local export
            if save_local:
                local_file = save_local / filename
                with open(local_file, "wb") as f:
                    f.write(chunk_bytes)

            r2_public_url: Optional[str] = None
            status = "Dry Run"

            # Cloudflare R2 Upload
            if not dry_run:
                try:
                    r2_public_url = upload_audio_to_r2(
                        file_obj=chunk_bytes,
                        filename=r2_key,
                        content_type="audio/wav",
                    )
                    status = "Uploaded to R2"
                except Exception as e:
                    status = f"Upload Failed: {e}"

            # Database record persistence
            if save_db and not dry_run and r2_public_url:
                try:
                    persist_lexicon_entry(
                        app=flask_app,
                        category_slug=category_slug,
                        category_name=category_name,
                        larteh_text=larteh_text,
                        phonetic=phonetic,
                        english=english,
                        grammatical_type=grammatical_type,
                        speaker=speaker,
                        cultural_notes=cultural_notes,
                        r2_url=r2_public_url,
                    )
                    status = "Uploaded + DB Synced"
                except Exception as e:
                    status = f"DB Sync Error: {e}"

            print(f"{i+1:<3} | {larteh_text:<15} | {phonetic:<15} | {english:<15} | {status}")
            results.append({
                "order": i + 1,
                "larteh_text": larteh_text,
                "phonetic_script": phonetic,
                "english_translation": english,
                "r2_url": r2_public_url,
                "duration_ms": len(chunk),
            })

        print("=" * 80)
        print(f"\n✅ Completed processing {len(results)} audio slices.")
        if dry_run:
            print("💡 Dry run complete. Re-run without --dry-run to stream directly to Cloudflare R2.")


def main():
    parser = argparse.ArgumentParser(
        description="Larteh Lingo Audio Slicer & Cloudflare R2 Ingestion Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("audio_path", type=Path, help="Path to continuous master audio file (.wav, .mp3, .webm)")
    parser.add_argument("metadata_json", type=Path, help="Path to sequential metadata JSON file")
    parser.add_argument(
        "--min-silence",
        type=int,
        default=500,
        help="Minimum silence duration (ms) for slicing (default: 500)",
    )
    parser.add_argument(
        "--silence-thresh",
        type=int,
        default=-35,
        help="Silence threshold in dBFS (default: -35)",
    )
    parser.add_argument(
        "--padding",
        type=int,
        default=150,
        help="Padding (ms) kept before and after speech (default: 150)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform slicing analysis without uploading to R2",
    )
    parser.add_argument(
        "--save-local",
        type=Path,
        default=None,
        help="Optional local directory to write sliced .wav files",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Directly create/update records in PostgreSQL database",
    )
    parser.add_argument(
        "--speaker",
        type=str,
        default=None,
        help="Override native speaker name (defaults to metadata or 'Dad')",
    )

    args = parser.parse_args()

    process_and_ingest(
        audio_path=args.audio_path,
        metadata_path=args.metadata_json,
        min_silence_len=args.min_silence,
        silence_thresh=args.silence_thresh,
        keep_silence=args.padding,
        dry_run=args.dry_run,
        save_local=args.save_local,
        save_db=args.save_db,
        speaker_override=args.speaker,
    )


if __name__ == "__main__":
    main()