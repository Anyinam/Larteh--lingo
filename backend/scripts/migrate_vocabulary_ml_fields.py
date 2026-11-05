#!/usr/bin/env python3
"""Add ML metadata columns to an existing Vocabulary table."""

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
for search_path in (str(ROOT_DIR), str(BACKEND_DIR)):
    if search_path not in sys.path:
        sys.path.insert(0, search_path)

from sqlalchemy import inspect, text

from backend.app import create_app
from backend.app.extensions import db


def migrate_vocabulary_ml_fields() -> None:
    """Create missing tables and add the three new ML columns idempotently."""
    app = create_app()
    with app.app_context():
        db.create_all()
        columns = {
            column["name"]
            for column in inspect(db.engine).get_columns("vocabulary")
        }
        additions = {
            "ml_split": "VARCHAR(20) NOT NULL DEFAULT 'train'",
            "duration_ms": "INTEGER",
            "sample_rate": "INTEGER NOT NULL DEFAULT 16000",
        }
        with db.engine.begin() as connection:
            for name, definition in additions.items():
                if name not in columns:
                    connection.execute(text(
                        f"ALTER TABLE vocabulary ADD COLUMN {name} {definition}"
                    ))
                    print(f"Added vocabulary.{name}.")
                else:
                    print(f"vocabulary.{name} already exists.")


if __name__ == "__main__":
    migrate_vocabulary_ml_fields()
