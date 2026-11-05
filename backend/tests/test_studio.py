"""Tests for prompt-based Studio recording endpoints."""

import io

from pydub import AudioSegment

from backend.app.extensions import db
from backend.app.models.vocabulary import Vocabulary
import backend.app.routes.studio as studio_routes


def _wav_recording(duration_ms=100):
    buffer = io.BytesIO()
    AudioSegment.silent(duration=duration_ms, frame_rate=44100).set_channels(2).export(
        buffer,
        format="wav",
    )
    return buffer.getvalue()


def test_studio_next_returns_pending_prompt_and_progress(client, app):
    with app.app_context():
        db.session.add_all([
            Vocabulary(
                english="Good morning",
                twi="Maakye",
                category="greetings",
                audio_url="audio/greetings/private.wav",
            ),
            Vocabulary(
                english="How are you?",
                category="greetings",
                recording_status="recorded",
                audio_url="https://media.example/audio/greetings/2.wav",
            ),
        ])
        db.session.commit()

    response = client.get("/api/studio/next")

    assert response.status_code == 200
    assert response.json["item"]["english"] == "Good morning"
    assert response.json["item"]["twi"] == "Maakye"
    assert response.json["item"]["audio_url"] is None
    assert response.json["stats"] == {
        "completed": 1,
        "total": 2,
        "percentage": 50.0,
    }


def test_studio_next_reports_completion_when_queue_is_empty(client):
    response = client.get("/api/studio/next")

    assert response.status_code == 404
    assert "All vocabulary items have been recorded" in response.json["message"]
    assert response.json["stats"] == {
        "completed": 0,
        "total": 0,
        "percentage": 0,
    }


def test_studio_upload_saves_audio_and_transcription(client, app, monkeypatch):
    with app.app_context():
        item = Vocabulary(english="Good morning", twi="Maakye", category="Greetings")
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    uploaded = {}

    def fake_upload(audio_bytes, object_key, content_type):
        uploaded.update(
            audio_bytes=audio_bytes,
            object_key=object_key,
            content_type=content_type,
        )
        return object_key

    monkeypatch.setattr(studio_routes, "upload_bytes_to_r2", fake_upload)
    recording = _wav_recording()
    response = client.post(
        f"/api/studio/upload/{item_id}",
        data={
            "larteh": "Eko",
            "phonetic": "[e-kɔ]",
            "audio": (io.BytesIO(recording), "recording.wav", "audio/wav"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert response.json == {"success": True}
    assert uploaded["object_key"] == "audio/greetings/1.wav"
    assert uploaded["content_type"] == "audio/wav"
    assert uploaded["audio_bytes"].startswith(b"RIFF")
    assert uploaded["audio_bytes"] != recording

    with app.app_context():
        saved = db.session.get(Vocabulary, item_id)
        assert saved.larteh == "Eko"
        assert saved.phonetic == "[e-kɔ]"
        assert saved.recording_status == "recorded"
        assert saved.audio_url == "audio/greetings/1.wav"
        assert saved.recorded_at is not None
        assert saved.duration_ms == 100
        assert saved.sample_rate == 16000


def test_studio_upload_requires_audio(client, app):
    with app.app_context():
        item = Vocabulary(english="Good morning")
        db.session.add(item)
        db.session.commit()
        item_id = item.id

    response = client.post(f"/api/studio/upload/{item_id}", data={})

    assert response.status_code == 400
    assert response.json["success"] is False
