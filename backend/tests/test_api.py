"""
Integration tests for Category & Lexicon endpoints.
"""

import io
from backend.app.models.category import Category
from backend.app.models.lexicon import LexiconEntry


def test_health_check(client):
    """Test health check route."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json["status"] == "healthy"


def test_create_and_get_categories(client):
    """Test POST /api/v1/categories and GET /api/v1/categories."""
    # Create category
    payload = {
        "name": "Numbers",
        "description": "Counting numbers in Larteh",
    }
    post_res = client.post("/api/v1/categories", json=payload)
    assert post_res.status_code == 201
    data = post_res.json["data"]
    assert data["name"] == "Numbers"
    assert data["slug"] == "numbers"

    # Get categories
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

    # Test search by larteh_text
    search_res = client.get("/api/v1/lexicon?larteh_text=Ekɔ")
    assert search_res.status_code == 200
    assert len(search_res.json["data"]) == 1
    assert search_res.json["data"][0]["larteh_text"] == "Ekɔ"

    # Test search by english_translation
    search_eng = client.get("/api/v1/lexicon?english_translation=One")
    assert search_eng.status_code == 200
    assert len(search_eng.json["data"]) == 1

    # Test filter by category_id
    cat_filter = client.get(f"/api/v1/lexicon?category_id={sample_category}")
    assert cat_filter.status_code == 200
    assert len(cat_filter.json["data"]) == 1

    # Test unified 'q' query
    q_search = client.get("/api/v1/lexicon?q=e-kɔ")
    assert q_search.status_code == 200
    assert len(q_search.json["data"]) == 1

