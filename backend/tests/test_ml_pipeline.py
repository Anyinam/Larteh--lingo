"""Tests for Studio ML metadata, manifests, and acoustic feature extraction."""

import io
import json

import numpy as np
import pytest
from pydub import AudioSegment
from sqlalchemy import inspect, text

from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary
from backend.app.models.vocabulary_recording import VocabularyRecording
from backend.app.services.ml_features import extract_acoustic_features
from backend.app.services.storage import (
    R2ConfigurationError,
    cloudflare_storage,
    download_audio_from_storage,
)
import backend.scripts.assign_ml_splits as split_script
import backend.scripts.extract_features as extraction_script
import backend.scripts.migrate_vocabulary_ml_fields as migration_script
import backend.scripts.seed_database as seed_script


def _wav_recording(duration_ms=300):
    buffer = io.BytesIO()
    AudioSegment.silent(duration=duration_ms, frame_rate=16000).export(buffer, format="wav")
    return buffer.getvalue()


def test_vocabulary_ml_metadata_defaults_and_serialization():
    item = Vocabulary(english="Good morning")

    assert item.ml_split == "train"
    assert item.duration_ms is None
    assert item.sample_rate == 16000
    assert item.to_dict()["ml_split"] == "train"
    assert item.to_dict()["duration_ms"] is None
    assert item.to_dict()["sample_rate"] == 16000


def test_vocabulary_manifest_is_disabled_for_privacy(client, app):
    with app.app_context():
        db.session.add_all([
            Vocabulary(
                english="Good morning",
                twi="Maakye",
                larteh="Eko",
                phonetic="[e-kɔ]",
                category="greetings",
                recording_status="recorded",
                audio_url="https://media.example/audio/greetings/1.wav",
                ml_split="validation",
                duration_ms=500,
            ),
            Vocabulary(
                english="Untranscribed recording",
                recording_status="recorded",
                audio_url="https://media.example/audio/greetings/2.wav",
            ),
            Vocabulary(
                english="Pending prompt",
                larteh="Idu",
                audio_url="https://media.example/audio/greetings/3.wav",
            ),
        ])
        db.session.commit()

    response = client.get("/api/v1/dataset/vocabulary/manifest?split=validation")

    assert response.status_code == 410
    assert b"https://media.example" not in response.data


def test_acoustic_feature_extraction_returns_mfcc_and_log_mel():
    result = extract_acoustic_features(_wav_recording())

    assert result["sample_rate"] == 16000
    assert result["duration_sec"] == 0.3
    assert result["mfcc"].shape[1] == 13
    assert result["mel_spectrogram"].shape[1] == 80
    assert result["mfcc"].shape[0] == result["mel_spectrogram"].shape[0]
    assert result["frame_times_sec"].shape[0] == result["mfcc"].shape[0]


def test_split_assignment_is_deterministic_and_category_stratified(app, monkeypatch):
    with app.app_context():
        db.session.add_all([
            Vocabulary(
                english=f"Prompt {index}",
                category="greetings",
                larteh=f"Word {index}",
                recording_status="recorded",
                audio_url=f"https://media.example/audio/greetings/{index}.wav",
            )
            for index in range(10)
        ])
        db.session.commit()

    monkeypatch.setattr(split_script, "create_app", lambda: app)
    split_counts = split_script.assign_ml_splits(seed=12)

    assert split_counts == {"train": 8, "validation": 1, "test": 1}
    with app.app_context():
        assert {
            entry.ml_split
            for entry in Vocabulary.query.filter_by(category="greetings").all()
        } == {"train", "validation", "test"}


def test_contributor_recordings_are_included_in_feature_pipeline(app, tmp_path, monkeypatch):
    with app.app_context():
        prompt = Vocabulary(english="Good morning", category="greetings")
        db.session.add(prompt)
        db.session.flush()
        db.session.add(VocabularyRecording(
            vocabulary_id=prompt.id,
            contributor_id="00000000-0000-4000-8000-000000000001",
            audio_key="audio/greetings/1/anonymous.wav",
            larteh="Eko",
            phonetic="[e-kɔ]",
        ))
        db.session.commit()

    monkeypatch.setattr(extraction_script, "create_app", lambda: app)
    monkeypatch.setattr(
        extraction_script,
        "download_audio_from_storage",
        lambda audio_key: _wav_recording(),
    )
    count = extraction_script.extract_dataset_features(tmp_path, "train")

    assert count == 1
    with np.load(tmp_path / "contributor-recording-1.npz") as features:
        assert features["mfcc"].shape[1] == 13
    manifest = json.loads((tmp_path / "manifest.jsonl").read_text().splitlines()[0])
    assert manifest["prompt_id"] == 1
    assert manifest["contributor_id"] == "00000000-0000-4000-8000-000000000001"
    assert manifest["text"] == "Eko"


def test_local_audio_download_reads_media_url_and_rejects_traversal(app, tmp_path):
    with app.app_context():
        app.config["LOCAL_UPLOAD_FOLDER"] = str(tmp_path)
        audio_path = tmp_path / "audio" / "greetings" / "1.wav"
        audio_path.parent.mkdir(parents=True)
        audio_path.write_bytes(b"wav")

        assert download_audio_from_storage(
            "/api/v1/media/audio/greetings/1.wav"
        ) == b"wav"
        try:
            download_audio_from_storage("/api/v1/media/audio/../../secret.wav")
        except ValueError as error:
            assert "outside" in str(error)
        else:
            raise AssertionError("Expected traversal path to be rejected.")


def test_r2_audio_download_strips_configured_public_domain_prefix(app, monkeypatch):
    class FakeClient:
        def get_object(self, **kwargs):
            assert kwargs["Bucket"] == "test-bucket"
            assert kwargs["Key"] == "audio/greetings/1.wav"
            return {"Body": io.BytesIO(b"r2 audio")}

    with app.app_context():
        app.config.update(
            STORAGE_BACKEND="r2",
            R2_ACCESS_KEY_ID="test-access",
            R2_SECRET_ACCESS_KEY="test-secret",
            R2_BUCKET_NAME="test-bucket",
            R2_PUBLIC_DOMAIN="https://cdn.example/audio-prefix",
        )
        monkeypatch.setattr(cloudflare_storage, "get_client", lambda: FakeClient())
        assert download_audio_from_storage(
            "https://cdn.example/audio-prefix/audio/greetings/1.wav"
        ) == b"r2 audio"


def test_production_cannot_store_audio_on_local_disk(app, tmp_path):
    with app.app_context():
        app.testing = False
        app.debug = False
        app.config.update(
            STORAGE_BACKEND="local",
            LOCAL_UPLOAD_FOLDER=str(tmp_path),
        )
        with pytest.raises(R2ConfigurationError, match="not permitted in production"):
            cloudflare_storage.upload_audio_to_r2(
                b"audio",
                "audio/greetings/1.wav",
                "audio/wav",
            )
        assert not (tmp_path / "audio" / "greetings" / "1.wav").exists()


def test_ml_metadata_migration_adds_missing_columns(app, monkeypatch):
    with app.app_context():
        db.session.execute(text("DROP TABLE vocabulary"))
        db.session.execute(text(
            "CREATE TABLE vocabulary (id INTEGER PRIMARY KEY, english VARCHAR(255) NOT NULL)"
        ))
        db.session.commit()

    monkeypatch.setattr(migration_script, "create_app", lambda: app)
    migration_script.migrate_vocabulary_ml_fields()

    with app.app_context():
        column_names = {
            column["name"]
            for column in inspect(db.engine).get_columns("vocabulary")
        }
        assert {"ml_split", "duration_ms", "sample_rate"} <= column_names


def test_common_phrase_seed_has_broad_unique_prompt_coverage(app, monkeypatch):
    seed_path = seed_script.BACKEND_DIR / "scripts" / "common_phrases.json"
    records = json.loads(seed_path.read_text(encoding="utf-8"))
    english_prompts = [record["english"] for record in records]

    assert len(records) >= 2000
    assert len(english_prompts) == len(set(english_prompts))
    assert len({prompt.casefold() for prompt in english_prompts}) == len(english_prompts)
    number_prompts = {
        record["english"]
        for record in records
        if record["category"] == "numbers"
    }
    assert {
        "Two hundred (200)",
        "Three hundred (300)",
        "Four hundred (400)",
        "Five hundred (500)",
        "One thousand (1,000)",
        "Two thousand (2,000)",
        "Ten thousand (10,000)",
    } <= number_prompts
    assert sum(record["category"] == "numbers" for record in records) >= 125
    assert sum(record["category"] == "days_of_week" for record in records) == 7
    assert all(record.get("larteh") is None for record in records)
    monkeypatch.setattr(seed_script, "app", app)
    assert seed_script.populate_database(seed_path.parent) == len(records)
    assert seed_script.populate_database(seed_path.parent) == 0
    with app.app_context():
        assert Vocabulary.query.count() == len(records)


def test_seed_database_skips_duplicate_prompts_in_a_file(app, tmp_path, monkeypatch):
    seed_file = tmp_path / "prompts.json"
    seed_file.write_text(json.dumps([
        {"english": "Good morning", "category": "greetings"},
        {"english": "Good morning", "category": "greetings"},
        {"english": "Thank you", "category": "greetings"},
    ]), encoding="utf-8")
    monkeypatch.setattr(seed_script, "app", app)

    assert seed_script.populate_database(tmp_path) == 2
    with app.app_context():
        assert Vocabulary.query.count() == 2


def test_feature_extraction_writes_npz_and_transcript_manifest(app, tmp_path, monkeypatch):
    with app.app_context():
        db.session.add(Vocabulary(
            english="Good morning",
            larteh="Eko",
            phonetic="[e-kɔ]",
            category="greetings",
            recording_status="recorded",
            audio_url="https://media.example/audio/greetings/1.wav",
        ))
        db.session.commit()

    monkeypatch.setattr(extraction_script, "create_app", lambda: app)
    monkeypatch.setattr(
        extraction_script,
        "download_audio_from_storage",
        lambda audio_url: _wav_recording(),
    )
    count = extraction_script.extract_dataset_features(tmp_path, "train")

    assert count == 1
    with np.load(tmp_path / "1.npz") as features:
        assert features["mfcc"].shape[1] == 13
        assert features["mel_spectrogram"].shape[1] == 80
    manifest = json.loads((tmp_path / "manifest.jsonl").read_text(encoding="utf-8"))
    assert manifest["text"] == "Eko"
    assert manifest["features"] == "1.npz"
