import pytest
from fastapi.testclient import TestClient
from main import app
from services.speech import text_to_speech
import os
import types

client = TestClient(app)

# ---- UNIT TESTS ----
def test_text_to_speech_unit(monkeypatch):
    # Mock httpx.post to avoid real API call
    def mock_post(url, headers, json, params, timeout):
        class MockResponse:
            def raise_for_status(self):
                pass
            @property
            def content(self):
                return b"fake-mp3-bytes"
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    os.environ["DEEPGRAM_API_KEY"] = "dummy"
    audio = text_to_speech("hello world", "asteria")
    assert isinstance(audio, bytes)
    assert audio == b"fake-mp3-bytes"

# ---- INTEGRATION TESTS ----
def test_tts_speak_integration(monkeypatch):
    # Mock Deepgram API call
    def mock_post(url, headers, json, params, timeout):
        class MockResponse:
            def raise_for_status(self):
                pass
            @property
            def content(self):
                return b"integration-mp3"
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    os.environ["DEEPGRAM_API_KEY"] = "dummy"
    response = client.post("/ivr/tts/speak", json={"text": "test", "voice": "asteria"})
    assert response.status_code == 200
    assert response.content == b"integration-mp3"
    assert response.headers["content-type"].startswith("audio/mpeg")

# ---- END-TO-END TESTS ----
def test_ivr_call_flow(monkeypatch):
    # This is a placeholder for a full IVR journey simulation
    # You can expand this with more endpoints and logic
    def mock_post(url, headers, json, params, timeout):
        class MockResponse:
            def raise_for_status(self):
                pass
            @property
            def content(self):
                return b"e2e-mp3"
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    os.environ["DEEPGRAM_API_KEY"] = "dummy"
    # Simulate TTS as part of IVR flow
    response = client.post("/ivr/tts/speak", json={"text": "welcome", "voice": "asteria"})
    assert response.status_code == 200
    assert response.content == b"e2e-mp3"

# ---- PERFORMANCE TESTS ----
def test_tts_speak_performance(monkeypatch):
    import time
    def mock_post(url, headers, json, params, timeout):
        class MockResponse:
            def raise_for_status(self):
                pass
            @property
            def content(self):
                return b"perf-mp3"
        return MockResponse()
    monkeypatch.setattr("httpx.post", mock_post)
    os.environ["DEEPGRAM_API_KEY"] = "dummy"
    start = time.time()
    for _ in range(20):
        response = client.post("/ivr/tts/speak", json={"text": "load", "voice": "asteria"})
        assert response.status_code == 200
        assert response.content == b"perf-mp3"
    elapsed = time.time() - start
    assert elapsed < 5  # All 20 requests should finish quickly (mocked)
