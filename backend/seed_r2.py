"""
Cloudflare R2 Seed Generator for Larteh (Gua) Lexicon Recordings.

Populates PostgreSQL with initial lexicon entries (Days of the Week and Numbers 1–40)
and registers their respective Cloudflare R2 object storage audio URLs.

Usage:
    python backend/seed_r2.py
    python backend/seed_r2.py --upload-samples   # Uploads local audio samples if found
"""

import sys
import os
import argparse
from pathlib import Path
from typing import List, Tuple, Dict, Any

# Ensure project root is available in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.category import Category, slugify
from backend.app.models.lexicon import LexiconEntry, GrammaticalType
from backend.app.services.storage import upload_audio_to_r2, cloudflare_storage

# ---------------------------------------------------------------------------
# Initial Categories
# ---------------------------------------------------------------------------
CATEGORIES = [
    {
        "name": "Days of the Week",
        "slug": "days-of-the-week",
        "description": "The 7 traditional days of the week in Larteh (Gua).",
    },
    {
        "name": "Numbers & Counting",
        "slug": "numbers-counting",
        "description": "Cardinal counting numbers 1 through 40 in Larteh.",
    },
]

# ---------------------------------------------------------------------------
# Days of the Week Seed Data
# ---------------------------------------------------------------------------
DAYS_OF_WEEK: List[Dict[str, Any]] = [
    {
        "larteh_text": "Idu",
        "phonetic_script": "[i-du]",
        "english_translation": "Sunday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "idu.wav",
        "cultural_notes": "First day of the week in Gua traditional reckoning.",
    },
    {
        "larteh_text": "Isum",
        "phonetic_script": "[i-sum]",
        "english_translation": "Monday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "isum.wav",
        "cultural_notes": "Start of the weekly agrarian and ridge trading cycle.",
    },
    {
        "larteh_text": "Epwɛ",
        "phonetic_script": "[e-pwɛ]",
        "english_translation": "Tuesday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "epwe.wav",
        "cultural_notes": "Features open 'ɛ' and labialized 'pw' phonemes distinctive to Larteh.",
    },
    {
        "larteh_text": "Isu",
        "phonetic_script": "[i-su]",
        "english_translation": "Wednesday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "isu.wav",
        "cultural_notes": "Midweek communal gathering day in the Akuapem hills.",
    },
    {
        "larteh_text": "Ibiro",
        "phonetic_script": "[i-bi-ro]",
        "english_translation": "Thursday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "ibiro.wav",
        "cultural_notes": "Traditional rest day for sacred groves and farmland.",
    },
    {
        "larteh_text": "Ife",
        "phonetic_script": "[i-fe]",
        "english_translation": "Friday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "ife.wav",
        "cultural_notes": "Preparation day preceding weekend festivals and rites.",
    },
    {
        "larteh_text": "Yinke",
        "phonetic_script": "[jin-ke]",
        "english_translation": "Saturday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "audio_file": "yinke.wav",
        "cultural_notes": "Celebration day characterized by community assemblies and funerals.",
    },
]

# ---------------------------------------------------------------------------
# Numbers 1 to 40 in Larteh (Gua)
# ---------------------------------------------------------------------------
NUMBERS_1_TO_40: List[Tuple[int, str, str, str, str]] = [
    # (num, larteh_text, phonetic, english, audio_file)
    (1, "Ekɔ", "[e-kɔ]", "One (1)", "eko.wav"),
    (2, "Enyɔ", "[e-ɲɔ]", "Two (2)", "enyo.wav"),
    (3, "Esa", "[e-sa]", "Three (3)", "esa.wav"),
    (4, "Enɛ", "[e-nɛ]", "Four (4)", "ene.wav"),
    (5, "Enu", "[e-nu]", "Five (5)", "enu.wav"),
    (6, "Esien", "[e-sien]", "Six (6)", "esien.wav"),
    (7, "Esono", "[e-so-no]", "Seven (7)", "esono.wav"),
    (8, "Etwie", "[e-twie]", "Eight (8)", "etwie.wav"),
    (9, "Ekpuno", "[e-kpu-no]", "Nine (9)", "ekpuno.wav"),
    (10, "Edu", "[e-du]", "Ten (10)", "edu.wav"),
    (11, "Edu n'Ekɔ", "[e-du n-e-kɔ]", "Eleven (11)", "edu_n_eko.wav"),
    (12, "Edu n'Enyɔ", "[e-du n-e-ɲɔ]", "Twelve (12)", "edu_n_enyo.wav"),
    (13, "Edu n'Esa", "[e-du n-e-sa]", "Thirteen (13)", "edu_n_esa.wav"),
    (14, "Edu n'Enɛ", "[e-du n-e-nɛ]", "Fourteen (14)", "edu_n_ene.wav"),
    (15, "Edu n'Enu", "[e-du n-e-nu]", "Fifteen (15)", "edu_n_enu.wav"),
    (16, "Edu n'Esien", "[e-du n-e-sien]", "Sixteen (16)", "edu_n_esien.wav"),
    (17, "Edu n'Esono", "[e-du n-e-so-no]", "Seventeen (17)", "edu_n_esono.wav"),
    (18, "Edu n'Etwie", "[e-du n-e-twie]", "Eighteen (18)", "edu_n_etwie.wav"),
    (19, "Edu n'Ekpuno", "[e-du n-e-kpu-no]", "Nineteen (19)", "edu_n_ekpuno.wav"),
    (20, "Aduanyɔ", "[a-dua-ɲɔ]", "Twenty (20)", "aduanyo.wav"),
    (21, "Aduanyɔ n'Ekɔ", "[a-dua-ɲɔ n-e-kɔ]", "Twenty-one (21)", "aduanyo_n_eko.wav"),
    (22, "Aduanyɔ n'Enyɔ", "[a-dua-ɲɔ n-e-ɲɔ]", "Twenty-two (22)", "aduanyo_n_enyo.wav"),
    (23, "Aduanyɔ n'Esa", "[a-dua-ɲɔ n-e-sa]", "Twenty-three (23)", "aduanyo_n_esa.wav"),
    (24, "Aduanyɔ n'Enɛ", "[a-dua-ɲɔ n-e-nɛ]", "Twenty-four (24)", "aduanyo_n_ene.wav"),
    (25, "Aduanyɔ n'Enu", "[a-dua-ɲɔ n-e-nu]", "Twenty-five (25)", "aduanyo_n_enu.wav"),
    (26, "Aduanyɔ n'Esien", "[a-dua-ɲɔ n-e-sien]", "Twenty-six (26)", "aduanyo_n_esien.wav"),
    (27, "Aduanyɔ n'Esono", "[a-dua-ɲɔ n-e-so-no]", "Twenty-seven (27)", "aduanyo_n_esono.wav"),
    (28, "Aduanyɔ n'Etwie", "[a-dua-ɲɔ n-e-twie]", "Twenty-eight (28)", "aduanyo_n_etwie.wav"),
    (29, "Aduanyɔ n'Ekpuno", "[a-dua-ɲɔ n-e-kpu-no]", "Twenty-nine (29)", "aduanyo_n_ekpuno.wav"),
    (30, "Aduasa", "[a-dua-sa]", "Thirty (30)", "aduasa.wav"),
    (31, "Aduasa n'Ekɔ", "[a-dua-sa n-e-kɔ]", "Thirty-one (31)", "aduasa_n_eko.wav"),
    (32, "Aduasa n'Enyɔ", "[a-dua-sa n-e-ɲɔ]", "Thirty-two (32)", "aduasa_n_enyo.wav"),
    (33, "Aduasa n'Esa", "[a-dua-sa n-e-sa]", "Thirty-three (33)", "aduasa_n_esa.wav"),
    (34, "Aduasa n'Enɛ", "[a-dua-sa n-e-nɛ]", "Thirty-four (34)", "aduasa_n_ene.wav"),
    (35, "Aduasa n'Enu", "[a-dua-sa n-e-nu]", "Thirty-five (35)", "aduasa_n_enu.wav"),
    (36, "Aduasa n'Esien", "[a-dua-sa n-e-sien]", "Thirty-six (36)", "aduasa_n_esien.wav"),
    (37, "Aduasa n'Esono", "[a-dua-sa n-e-so-no]", "Thirty-seven (37)", "aduasa_n_esono.wav"),
    (38, "Aduasa n'Etwie", "[a-dua-sa n-e-twie]", "Thirty-eight (38)", "aduasa_n_etwie.wav"),
    (39, "Aduasa n'Ekpuno", "[a-dua-sa n-e-kpu-no]", "Thirty-nine (39)", "aduasa_n_ekpuno.wav"),
    (40, "Eduenɛ", "[e-due-nɛ]", "Forty (40)", "eduene.wav"),
]


def resolve_r2_audio_url(
    public_domain: str,
    category_slug: str,
    audio_filename: str,
    upload_sample: bool = False,
    sample_dir: Path = None,
) -> str:
    """
    Construct the canonical Cloudflare R2 audio URL and optionally upload physical sample files.
    """
    object_key = f"audio/{category_slug}/{audio_filename}"

    # If physical sample exists and upload requested, upload to R2
    if upload_sample and sample_dir:
        sample_path = sample_dir / audio_filename
        if sample_path.exists():
            print(f"    [↑] Uploading physical audio to R2: {sample_path.name}")
            with open(sample_path, "rb") as f:
                return upload_audio_to_r2(f, object_key, content_type="audio/wav")

    # Otherwise format canonical R2 URL via public domain or bucket path
    if public_domain:
        return f"{public_domain.rstrip('/')}/{object_key}"

    return f"https://larteh-lingo-audio.r2.cloudflarestorage.com/{object_key}"


def seed_r2_data(upload_samples: bool = False):
    """Seed the database with Days of the Week and Numbers 1-40 linked to Cloudflare R2."""
    app = create_app(os.getenv("FLASK_ENV", "development"))

    with app.app_context():
        db.create_all()

        public_domain = app.config.get("R2_PUBLIC_DOMAIN", "https://media.lartehlingo.org")
        sample_audio_dir = BASE_DIR / "backend" / "seed_audio"

        print("🇬🇭 Seeding Larteh Lexicon to Cloudflare R2 Pipeline...")
        print(f"  • R2 Bucket: {app.config.get('R2_BUCKET_NAME', 'larteh-lingo-audio')}")
        print(f"  • Public Domain: {public_domain}")

        # 1. Categories
        cat_map = {}
        for cat_info in CATEGORIES:
            cat = Category.query.filter_by(slug=cat_info["slug"]).first()
            if not cat:
                cat = Category(
                    name=cat_info["name"],
                    slug=cat_info["slug"],
                    description=cat_info["description"],
                )
                db.session.add(cat)
                db.session.flush()
                print(f"  [+] Created Category: '{cat.name}'")
            else:
                cat.description = cat_info["description"]
            cat_map[cat.slug] = cat

        # 2. Days of the Week (7 Entries)
        days_cat = cat_map["days-of-the-week"]
        days_count = 0
        for day in DAYS_OF_WEEK:
            r2_url = resolve_r2_audio_url(
                public_domain=public_domain,
                category_slug=days_cat.slug,
                audio_filename=day["audio_file"],
                upload_sample=upload_samples,
                sample_dir=sample_audio_dir,
            )

            entry = LexiconEntry.query.filter_by(
                larteh_text=day["larteh_text"],
                category_id=days_cat.id,
            ).first()

            if not entry:
                entry = LexiconEntry(
                    category_id=days_cat.id,
                    larteh_text=day["larteh_text"],
                    phonetic_script=day["phonetic_script"],
                    english_translation=day["english_translation"],
                    grammatical_type=day["grammatical_type"],
                    audio_url=r2_url,
                    speaker_name=day["speaker_name"],
                    cultural_notes=day["cultural_notes"],
                )
                db.session.add(entry)
                days_count += 1
            else:
                entry.phonetic_script = day["phonetic_script"]
                entry.english_translation = day["english_translation"]
                entry.audio_url = r2_url
                entry.cultural_notes = day["cultural_notes"]

        print(f"  [✓] Synced {len(DAYS_OF_WEEK)} Days of the Week records with R2 audio links.")

        # 3. Numbers 1 to 40 (40 Entries)
        numbers_cat = cat_map["numbers-counting"]
        nums_count = 0
        for num, text, phonetic, eng, audio_file in NUMBERS_1_TO_40:
            r2_url = resolve_r2_audio_url(
                public_domain=public_domain,
                category_slug=numbers_cat.slug,
                audio_filename=audio_file,
                upload_sample=upload_samples,
                sample_dir=sample_audio_dir,
            )

            entry = LexiconEntry.query.filter_by(
                larteh_text=text,
                category_id=numbers_cat.id,
            ).first()

            notes = f"Cardinal number {num} in the Larteh decimal numeral system."
            if num == 40:
                notes += " Marks forty (Eduenɛ), derived compound based on four tens."

            if not entry:
                entry = LexiconEntry(
                    category_id=numbers_cat.id,
                    larteh_text=text,
                    phonetic_script=phonetic,
                    english_translation=eng,
                    grammatical_type=GrammaticalType.CARDINAL_NUMBER.value,
                    audio_url=r2_url,
                    speaker_name="Dad",
                    cultural_notes=notes,
                )
                db.session.add(entry)
                nums_count += 1
            else:
                entry.phonetic_script = phonetic
                entry.english_translation = eng
                entry.audio_url = r2_url
                entry.cultural_notes = notes

        print(f"  [✓] Synced {len(NUMBERS_1_TO_40)} Numbers (1-40) records with R2 audio links.")

        db.session.commit()
        print("✅ Database successfully seeded and connected to Cloudflare R2 audio pipeline!\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed Larteh Lexicon to Cloudflare R2")
    parser.add_argument(
        "--upload-samples",
        action="store_true",
        help="Upload sample audio files from backend/seed_audio/ to R2 if present",
    )
    args = parser.parse_args()
    seed_r2_data(upload_samples=args.upload_samples)

