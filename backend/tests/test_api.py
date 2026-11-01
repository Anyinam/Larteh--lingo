"""
Integration tests for Category, Lexicon, and ML Dataset Export endpoints.
"""

import io
import json
import csv
from pydub import AudioSegment
from backend.app.extensions import db
from backend.app.models.category import Category
from backend.app.models.lexicon import LexiconEntry
from backend.app.models.ml_dataset import DatasetExportLog
from backend.app.utils.ml_audio_processor import process_and_resample_audio


def test_health_check(client):
    """Test health check route."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_create_and_get_categories(client):
    """Test POST /api/v1/categories and GET /api/v1/categories."""
    payload = {
        "name": "Numbers",
        "description": "Counting numbers in Larteh",
    }
    post_res = client.post("/api/v1/categories", json=payload)
    assert post_res.status_code == 201
    data = post_res.json["data"]
    assert data["name"] == "Numbers"
    assert data["slug"] == "numbers"

    get_res = client.get("/api/v1/categories")
    assert get_res.status_code == 200
    assert len(get_res.json["data"]) == 1
    assert get_res.json["data"][0]["slug"] == "numbers"


def test_create_category_duplicate_validation(client):
    """Test duplicate category validation error."""
    client.post("/api/v1/categories", json={"name": "Kinship"})
    res2 = client.post("/api/v1/categories", json={"name": "Kinship"})
    assert res2.status_code == 409
    assert "already exists" in res2.json["message"]


def test_lexicon_upload_and_search(client, sample_category):
    """Test POST /api/v1/lexicon/upload with multipart data and GET /api/v1/lexicon filtering."""
    fake_audio = io.BytesIO(b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00data\x00\x00\x00\x00")

    form_payload = {
        "larteh_text": "Ekɔ",
        "phonetic_script": "[e-kɔ]",
        "english_translation": "One (1)",
        "category_id": str(sample_category),
        "grammatical_type": "cardinal_number",
        "speaker_name": "Dad",
        "cultural_notes": "First cardinal counting unit.",
        "audio": (fake_audio, "eko.wav", "audio/wav"),
    }

    upload_res = client.post(
        "/api/v1/lexicon/upload",
        data=form_payload,
        content_type="multipart/form-data",
    )

    assert upload_res.status_code == 201
    entry_data = upload_res.json["data"]
    assert entry_data["larteh_text"] == "Ekɔ"
    assert entry_data["phonetic_script"] == "[e-kɔ]"
    assert entry_data["english_translation"] == "One (1)"
    assert entry_data["audio_url"] is not None

    search_res = client.get("/api/v1/lexicon?larteh_text=Ekɔ")
    assert search_res.status_code == 200
    assert len(search_res.json["data"]) == 1
    assert search_res.json["data"][0]["larteh_text"] == "Ekɔ"


def test_ml_audio_resampler():
    """Test audio resampling utility (16kHz mono WAV format)."""
    seg = AudioSegment.silent(duration=1500, frame_rate=44100).set_channels(2)
    buf = io.BytesIO()
    seg.export(buf, format="wav")

    wav_bytes, duration_sec, sample_rate = process_and_resample_audio(buf.getvalue())
    assert duration_sec == 1.5
    assert sample_rate == 16000
    assert len(wav_bytes) > 0
    assert wav_bytes.startswith(b"RIFF")


def test_ml_dataset_export_jsonl(app, client):
    """Test GET /api/v1/dataset/export with format=jsonl streaming."""
    with app.app_context():
        entry1 = LexiconEntry(
            larteh_text="Idu",
            phonetic_script="[i-du]",
            english_translation="Sunday",
            audio_url="https://media.lartehlingo.org/audio/days/idu.wav",
            audio_duration_sec=1.12,
            is_verified=True,
        )
        entry2 = LexiconEntry(
            larteh_text="Isum",
            phonetic_script="[i-sum]",
            english_translation="Monday",
            audio_url="https://media.lartehlingo.org/audio/days/isum.wav",
            audio_duration_sec=0.95,
            is_verified=False,  # Unverified
        )
        db.session.add_all([entry1, entry2])
        db.session.commit()

    # 1. Verified only (default)
    res = client.get("/api/v1/dataset/export?format=jsonl")
    assert res.status_code == 200
    assert "application/x-ndjson" in res.content_type
    lines = [line.strip() for line in res.data.decode("utf-8").split("\n") if line.strip()]
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["text"] == "Idu"
    assert data["phonetic"] == "[i-du]"
    assert data["translation"] == "Sunday"
    assert data["duration"] == 1.12
    assert data["audio"] == "https://media.lartehlingo.org/audio/days/idu.wav"

    # 2. Including unverified
    res_all = client.get("/api/v1/dataset/export?format=jsonl&verified_only=false")
    lines_all = [line.strip() for line in res_all.data.decode("utf-8").split("\n") if line.strip()]
    assert len(lines_all) == 2


def test_ml_dataset_export_csv(app, client):
    """Test GET /api/v1/dataset/export with format=csv streaming."""
    with app.app_context():
        entry = LexiconEntry(
            larteh_text="Epwɛ",
            phonetic_script="[e-pwɛ]",
            english_translation="Tuesday",
            audio_url="https://media.lartehlingo.org/audio/days/epwe.wav",
            audio_duration_sec=1.05,
            is_verified=True,
        )
        db.session.add(entry)
        db.session.commit()

    res = client.get("/api/v1/dataset/export?format=csv")
    assert res.status_code == 200
    assert "text/csv" in res.content_type
    reader = list(csv.reader(io.StringIO(res.data.decode("utf-8"))))
    assert reader[0] == ["audio", "text", "phonetic", "translation", "duration"]
    assert reader[1] == [
        "https://media.lartehlingo.org/audio/days/epwe.wav",
        "Epwɛ",
        "[e-pwɛ]",
        "Tuesday",
        "1.05",
    ]


def test_ml_dataset_export_invalid_format(client):
    """Test error handling for unsupported export format."""
    res = client.get("/api/v1/dataset/export?format=parquet")
    assert res.status_code == 400
    assert "Unsupported export format" in res.json["message"]
