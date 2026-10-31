"""
Seed Data Generator for Larteh (Gua) Preservation Engine.

Pre-populates the database with foundational taxonomic categories,
the 7 traditional days of the week, and cardinal numbers 1 through 40.
Execution is idempotent (safe to run multiple times).
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from backend.app import create_app
from backend.app.extensions import db
from backend.app.models.category import Category
from backend.app.models.lexicon import LexiconEntry, GrammaticalType


# ---------------------------------------------------------------------------
# Pre-populated Taxonomy Categories
# ---------------------------------------------------------------------------
CATEGORIES = [
    {
        "name": "Days of the Week",
        "slug": "days-of-the-week",
        "description": "The seven traditional days of the week in Larteh (Gua), reflecting indigenous calendars and naming conventions.",
    },
    {
        "name": "Numbers & Counting",
        "slug": "numbers-counting",
        "description": "Cardinal and ordinal numbers, counting systems, and quantitative terms in Larteh.",
    },
    {
        "name": "Greetings & Etiquette",
        "slug": "greetings-etiquette",
        "description": "Common salutations, daily greetings, and respectful expressions.",
    },
    {
        "name": "Family & Kinship",
        "slug": "family-kinship",
        "description": "Kinship terminology, lineage, elders, and domestic relations.",
    },
]

# ---------------------------------------------------------------------------
# 7 Days of the Week
# ---------------------------------------------------------------------------
DAYS_OF_WEEK = [
    {
        "larteh_text": "Idu",
        "phonetic_script": "[i-du]",
        "english_translation": "Sunday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "First day of the week. Day name associated with spiritual reverence in Gua traditions.",
    },
    {
        "larteh_text": "Isum",
        "phonetic_script": "[i-sum]",
        "english_translation": "Monday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "Start of the working and farming cycle in the Akuapem ridge.",
    },
    {
        "larteh_text": "Epwɛ",
        "phonetic_script": "[e-pwɛ]",
        "english_translation": "Tuesday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "Features open 'ɛ' vowel and labialized 'pw' consonant blend distinctive to Larteh phonology.",
    },
    {
        "larteh_text": "Isu",
        "phonetic_script": "[i-su]",
        "english_translation": "Wednesday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "Midweek market day in neighbouring settlements.",
    },
    {
        "larteh_text": "Ibiro",
        "phonetic_script": "[i-bi-ro]",
        "english_translation": "Thursday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "Often an agrarian observance day where certain forest lands were traditionally rested.",
    },
    {
        "larteh_text": "Ife",
        "phonetic_script": "[i-fe]",
        "english_translation": "Friday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "Sacred day of reflection preceding community weekend ceremonies.",
    },
    {
        "larteh_text": "Yinke",
        "phonetic_script": "[jin-ke]",
        "english_translation": "Saturday",
        "grammatical_type": GrammaticalType.DAY_OF_WEEK.value,
        "speaker_name": "Dad",
        "cultural_notes": "Final day of the week, celebrated with community gatherings, festivals, and family rites.",
    },
]

# ---------------------------------------------------------------------------
# Numbers 1 to 40 in Larteh (Gua)
# ---------------------------------------------------------------------------
BASE_NUMBERS = [
    (1, "Ekɔ", "[e-kɔ]", "One (1)"),
    (2, "Enyɔ", "[e-ɲɔ]", "Two (2)"),
    (3, "Esa", "[e-sa]", "Three (3)"),
    (4, "Enɛ", "[e-nɛ]", "Four (4)"),
    (5, "Enu", "[e-nu]", "Five (5)"),
    (6, "Esien", "[e-sien]", "Six (6)"),
    (7, "Esono", "[e-so-no]", "Seven (7)"),
    (8, "Etwie", "[e-twie]", "Eight (8)"),
    (9, "Ekpuno", "[e-kpu-no]", "Nine (9)"),
    (10, "Edu", "[e-du]", "Ten (10)"),
]

TEENS = [
    (11, "Edu n'Ekɔ", "[e-du n-e-kɔ]", "Eleven (11)"),
    (12, "Edu n'Enyɔ", "[e-du n-e-ɲɔ]", "Twelve (12)"),
    (13, "Edu n'Esa", "[e-du n-e-sa]", "Thirteen (13)"),
    (14, "Edu n'Enɛ", "[e-du n-e-nɛ]", "Fourteen (14)"),
    (15, "Edu n'Enu", "[e-du n-e-nu]", "Fifteen (15)"),
    (16, "Edu n'Esien", "[e-du n-e-sien]", "Sixteen (16)"),
    (17, "Edu n'Esono", "[e-du n-e-so-no]", "Seventeen (17)"),
    (18, "Edu n'Etwie", "[e-du n-e-twie]", "Eighteen (18)"),
    (19, "Edu n'Ekpuno", "[e-du n-e-kpu-no]", "Nineteen (19)"),
    (20, "Aduanyɔ", "[a-dua-ɲɔ]", "Twenty (20)"),
]

TWENTIES = [
    (21, "Aduanyɔ n'Ekɔ", "[a-dua-ɲɔ n-e-kɔ]", "Twenty-one (21)"),
    (22, "Aduanyɔ n'Enyɔ", "[a-dua-ɲɔ n-e-ɲɔ]", "Twenty-two (22)"),
    (23, "Aduanyɔ n'Esa", "[a-dua-ɲɔ n-e-sa]", "Twenty-three (23)"),
    (24, "Aduanyɔ n'Enɛ", "[a-dua-ɲɔ n-e-nɛ]", "Twenty-four (24)"),
    (25, "Aduanyɔ n'Enu", "[a-dua-ɲɔ n-e-nu]", "Twenty-five (25)"),
    (26, "Aduanyɔ n'Esien", "[a-dua-ɲɔ n-e-sien]", "Twenty-six (26)"),
    (27, "Aduanyɔ n'Esono", "[a-dua-ɲɔ n-e-so-no]", "Twenty-seven (27)"),
    (28, "Aduanyɔ n'Etwie", "[a-dua-ɲɔ n-e-twie]", "Twenty-eight (28)"),
    (29, "Aduanyɔ n'Ekpuno", "[a-dua-ɲɔ n-e-kpu-no]", "Twenty-nine (29)"),
    (30, "Aduasa", "[a-dua-sa]", "Thirty (30)"),
]

THIRTIES_AND_FORTY = [
    (31, "Aduasa n'Ekɔ", "[a-dua-sa n-e-kɔ]", "Thirty-one (31)"),
    (32, "Aduasa n'Enyɔ", "[a-dua-sa n-e-ɲɔ]", "Thirty-two (32)"),
    (33, "Aduasa n'Esa", "[a-dua-sa n-e-sa]", "Thirty-three (33)"),
    (34, "Aduasa n'Enɛ", "[a-dua-sa n-e-nɛ]", "Thirty-four (34)"),
    (35, "Aduasa n'Enu", "[a-dua-sa n-e-nu]", "Thirty-five (35)"),
    (36, "Aduasa n'Esien", "[a-dua-sa n-e-sien]", "Thirty-six (36)"),
    (37, "Aduasa n'Esono", "[a-dua-sa n-e-so-no]", "Thirty-seven (37)"),
    (38, "Aduasa n'Etwie", "[a-dua-sa n-e-twie]", "Thirty-eight (38)"),
    (39, "Aduasa n'Ekpuno", "[a-dua-sa n-e-kpu-no]", "Thirty-nine (39)"),
    (40, "Eduenɛ", "[e-due-nɛ]", "Forty (40)"),
]

ALL_NUMBERS = BASE_NUMBERS + TEENS + TWENTIES + THIRTIES_AND_FORTY


def seed_database():
    """Execute idempotent database seeding."""
    app = create_app(os.getenv("FLASK_ENV", "development"))

    with app.app_context():
        # Ensure all tables exist
        db.create_all()

        print("🇬🇭 Starting Larteh Lingo Database Seeding...")

        # 1. Seed Categories
        category_map = {}
        for cat_data in CATEGORIES:
            cat = Category.query.filter_by(slug=cat_data["slug"]).first()
            if not cat:
                cat = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    description=cat_data["description"],
                )
                db.session.add(cat)
                db.session.flush()
                print(f"  [+] Created Category: {cat.name}")
            else:
                cat.description = cat_data["description"]
                print(f"  [*] Existing Category: {cat.name}")
            category_map[cat.slug] = cat

        # 2. Seed 7 Days of the Week
        days_category = category_map["days-of-the-week"]
        days_added = 0
        for day in DAYS_OF_WEEK:
            existing = LexiconEntry.query.filter_by(
                larteh_text=day["larteh_text"],
                category_id=days_category.id,
            ).first()

            if not existing:
                entry = LexiconEntry(
                    category_id=days_category.id,
                    larteh_text=day["larteh_text"],
                    phonetic_script=day["phonetic_script"],
                    english_translation=day["english_translation"],
                    grammatical_type=day["grammatical_type"],
                    speaker_name=day["speaker_name"],
                    cultural_notes=day["cultural_notes"],
                )
                db.session.add(entry)
                days_added += 1
            else:
                existing.phonetic_script = day["phonetic_script"]
                existing.english_translation = day["english_translation"]
                existing.cultural_notes = day["cultural_notes"]

        print(f"  [✓] Seeded {days_added} Days of the Week entries.")

        # 3. Seed Numbers 1 - 40
        numbers_category = category_map["numbers-counting"]
        numbers_added = 0
        for num, text, phonetic, eng in ALL_NUMBERS:
            existing = LexiconEntry.query.filter_by(
                larteh_text=text,
                category_id=numbers_category.id,
            ).first()

            notes = f"Cardinal counting number {num} in the Larteh decimal system."
            if num == 40:
                notes += " Marks forty (Eduenɛ), derived compound based on four tens."

            if not existing:
                entry = LexiconEntry(
                    category_id=numbers_category.id,
                    larteh_text=text,
                    phonetic_script=phonetic,
                    english_translation=eng,
                    grammatical_type=GrammaticalType.CARDINAL_NUMBER.value,
                    speaker_name="Dad",
                    cultural_notes=notes,
                )
                db.session.add(entry)
                numbers_added += 1
            else:
                existing.phonetic_script = phonetic
                existing.english_translation = eng
                existing.cultural_notes = notes

        print(f"  [✓] Seeded {numbers_added} Numbers (1-40) entries.")

        # Commit transaction
        db.session.commit()
        print("✅ Database seeding completed successfully!\n")


if __name__ == "__main__":
    seed_database()

