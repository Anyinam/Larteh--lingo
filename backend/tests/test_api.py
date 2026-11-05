"""
Integration tests for Category, Lexicon, and ML Dataset Export endpoints.
"""

import io
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
    assert entry_data["audio_url"] is None

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


def test_dataset_export_endpoints_are_disabled_for_privacy(client):
    """Public export routes must never disclose audio URLs or transcripts."""
    for path in (
        "/api/v1/dataset/export",
        "/api/v1/dataset/vocabulary/manifest",
    ):
        response = client.get(path)
        assert response.status_code == 410
        assert "recordings are private" in response.json["message"]


def test_local_media_route_does_not_serve_recordings(client):
    response = client.get("/api/v1/media/audio/greetings/1.wav")

    assert response.status_code == 404
    assert "private" in response.json["message"]
