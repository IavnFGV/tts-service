from fastapi.testclient import TestClient
import pytest

from tts_service import app, settings
from tts_service.text import normalize_text


@pytest.fixture(autouse=True)
def patch_synthesizer(monkeypatch):
    class DummySynthesizer:
        async def synthesize_ogg(self, text: str, voice_id: str, speed: float = 1.0) -> bytes:
            return b"dummy-ogg-data"

    monkeypatch.setattr("tts_service.api.synthesizer", DummySynthesizer())
    yield


def test_healthz_returns_ok():
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_voices_returns_catalog():
    client = TestClient(app)
    response = client.get("/voices")
    assert response.status_code == 200
    payload = response.json()
    assert payload["default_voice_id"] == settings.default_voice_id
    assert isinstance(payload["voices"], list)
    assert any(voice["id"] == settings.default_voice_id for voice in payload["voices"])


def test_synthesize_returns_audio_bytes():
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={"text": "Hello world", "voice_id": settings.default_voice_id},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/ogg"
    assert response.content == b"dummy-ogg-data"


def test_synthesize_accepts_speed_parameter(monkeypatch):
    captured = {}

    async def fake_synthesize(text: str, voice_id: str, speed: float = 1.0) -> bytes:
        captured["text"] = text
        captured["voice_id"] = voice_id
        captured["speed"] = speed
        return b"dummy-ogg-data"

    monkeypatch.setattr("tts_service.api.synthesizer.synthesize_ogg", fake_synthesize)
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={
            "text": "Hello world",
            "voice_id": settings.default_voice_id,
            "speed": 1.5,
        },
    )
    assert response.status_code == 200
    assert captured == {
        "text": "Hello world",
        "voice_id": settings.default_voice_id,
        "speed": 1.5,
    }


def test_synthesize_uses_default_speed_when_omitted(monkeypatch):
    captured = {}

    async def fake_synthesize(text: str, voice_id: str, speed: float = 1.0) -> bytes:
        captured["text"] = text
        captured["voice_id"] = voice_id
        captured["speed"] = speed
        return b"dummy-ogg-data"

    monkeypatch.setattr("tts_service.api.synthesizer.synthesize_ogg", fake_synthesize)
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={
            "text": "Hello world",
            "voice_id": settings.default_voice_id,
        },
    )
    assert response.status_code == 200
    assert captured == {
        "text": "Hello world",
        "voice_id": settings.default_voice_id,
        "speed": 1.0,
    }


def test_unknown_voice_id_is_bad_request():
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={"text": "Hello world", "voice_id": "unknown-voice"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "unknown voice_id"


def test_empty_text_is_bad_request():
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={"text": "   ", "voice_id": settings.default_voice_id},
    )
    assert response.status_code == 400


def test_text_over_limit_is_bad_request():
    client = TestClient(app)
    sample_text = "a" * (settings.max_text_length + 1)
    response = client.post(
        "/v1/synthesize",
        json={"text": sample_text, "voice_id": settings.default_voice_id},
    )
    assert response.status_code == 400
    assert str(settings.max_text_length) in response.json()["detail"]


def test_speed_over_limit_is_bad_request():
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={
            "text": "Hello world",
            "voice_id": settings.default_voice_id,
            "speed": 5.1,
        },
    )
    assert response.status_code == 400
    assert "less than or equal to 5" in response.json()["detail"]


def test_speed_under_limit_is_bad_request():
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={
            "text": "Hello world",
            "voice_id": settings.default_voice_id,
            "speed": 0.09,
        },
    )
    assert response.status_code == 400
    assert "greater than or equal to 0.1" in response.json()["detail"]


def test_synthesis_failure_returns_500(monkeypatch):
    async def fail(text: str, voice_id: str, speed: float = 1.0) -> bytes:
        raise RuntimeError("boom")

    monkeypatch.setattr("tts_service.api.synthesizer.synthesize_ogg", fail)
    client = TestClient(app)
    response = client.post(
        "/v1/synthesize",
        json={"text": "Hello world", "voice_id": settings.default_voice_id},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "synthesis failed"
