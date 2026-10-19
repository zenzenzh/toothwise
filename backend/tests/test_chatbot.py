"""
Tests for the public chatbot route's resilience: retries on transient Gemini
errors and the verified-facts fallback when Gemini stays down. Gemini is
replaced by a fake httpx client, so no network or API key is used.
"""
from __future__ import annotations

import httpx
import pytest

from app.routers import chatbot


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = str(self._payload)

    def json(self):
        return self._payload


def _ok(text: str) -> _FakeResponse:
    return _FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": text}]}}]})


@pytest.fixture()
def fake_gemini(monkeypatch):
    """Queue of responses the fake Gemini returns, in order."""
    queue: list = []
    calls = {"n": 0}

    async def fake_post(self, url, headers=None, json=None):
        calls["n"] += 1
        item = queue.pop(0) if queue else _FakeResponse(503)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(chatbot.settings, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(chatbot, "RETRY_DELAYS", (0, 0))
    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    return queue, calls


def _ask(client, message: str):
    return client.post("/api/chatbot", json={"message": message, "history": [
        {"role": "model", "content": "Hi! I’m the ToothWise AI Assistant."},
    ]})


def test_retries_transient_error_then_answers(client, fake_gemini):
    queue, calls = fake_gemini
    queue += [_FakeResponse(503), _ok("Brush twice a day.")]
    resp = _ask(client, "How often should I brush?")
    assert resp.status_code == 200, resp.text
    assert resp.json()["reply"] == "Brush twice a day."
    assert calls["n"] == 2


def test_clinic_question_falls_back_to_verified_facts(client, fake_gemini):
    queue, calls = fake_gemini
    queue += [_FakeResponse(503), _FakeResponse(503), _FakeResponse(503)]
    resp = _ask(client, "What are your clinic hours?")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model"] == "clinic-faq"
    assert "9:00 AM" in body["reply"]
    assert calls["n"] == 3


def test_unknown_question_still_reports_outage(client, fake_gemini):
    queue, _ = fake_gemini
    queue += [httpx.ConnectError("down")] * 3
    resp = _ask(client, "Is it normal for my gums to itch?")
    assert resp.status_code == 502


def test_bad_request_is_not_retried(client, fake_gemini):
    queue, calls = fake_gemini
    queue += [_FakeResponse(400), _ok("never reached")]
    resp = _ask(client, "Tell me about flossing")
    assert resp.status_code == 502
    assert calls["n"] == 1


def test_truncated_reply_is_trimmed_to_last_full_sentence(client, fake_gemini):
    queue, _ = fake_gemini
    queue.append(_FakeResponse(200, {"candidates": [{
        "finishReason": "MAX_TOKENS",
        "content": {"parts": [{"text": "Brush twice a day. Floss every night.\n\n* Use a soft brush to keep your"}]},
    }]}))
    resp = _ask(client, "How do I care for my gums?")
    assert resp.status_code == 200, resp.text
    assert resp.json()["reply"] == "Brush twice a day. Floss every night."


def test_faq_fallback_does_not_invent_prices():
    reply = chatbot._faq_fallback("Magkano ang cleaning?")
    assert reply and "can't confirm prices" in reply
