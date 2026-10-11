import os

import pytest
from fastapi.testclient import TestClient

from app.llm_client import LLMError
from app.main import app
from app.schemas import TriageResponse


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_valid_request_success(client, monkeypatch):
    def fake_triage(text):
        return TriageResponse(
            category="support",
            draft_reply="Спасибо, разбираемся с вашим вопросом.",
            confidence="high",
            escalate=False,
        )

    monkeypatch.setattr("app.main.triage", fake_triage)
    resp = client.post(
        "/triage",
        json={"text": "У меня не работает вход в личный кабинет", "channel": "chat", "client_id": "user-1"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["category"] == "support"
    assert data["escalate"] is False
    assert set(data.keys()) == {"category", "draft_reply", "confidence", "escalate"}


def test_empty_text_rejected(client):
    resp = client.post("/triage", json={"text": "", "channel": "chat", "client_id": "user-2"})
    assert resp.status_code == 422


def test_invalid_channel_rejected(client):
    resp = client.post("/triage", json={"text": "test", "channel": "sms", "client_id": "user-3"})
    assert resp.status_code == 422


def test_text_too_long_rejected(client):
    resp = client.post("/triage", json={"text": "a" * 2001, "channel": "chat", "client_id": "user-4"})
    assert resp.status_code == 422


def test_llm_failure_triggers_fallback(client, monkeypatch):
    def fake_triage(text):
        raise LLMError("boom")

    monkeypatch.setattr("app.main.triage", fake_triage)
    resp = client.post("/triage", json={"text": "test", "channel": "email", "client_id": "user-5"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["escalate"] is True
    assert data["confidence"] == "low"
    assert "оператору" in data["draft_reply"].lower()


def test_rate_limit_blocks_after_n_requests(client, monkeypatch):
    def fake_triage(text):
        return TriageResponse(category="other", draft_reply="ok", confidence="high", escalate=False)

    monkeypatch.setattr("app.main.triage", fake_triage)
    client_id = "rate-test-client"
    limit = int(os.environ["RATE_LIMIT_PER_MINUTE"])

    for _ in range(limit):
        r = client.post("/triage", json={"text": "test", "channel": "chat", "client_id": client_id})
        assert r.status_code == 200

    r = client.post("/triage", json={"text": "test", "channel": "chat", "client_id": client_id})
    assert r.status_code == 429
