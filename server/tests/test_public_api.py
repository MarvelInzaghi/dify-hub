import hashlib
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import public as public_module
from app.db import get_db
from app.deps import get_service_client
from app.main import app
from app.models import ApiKey, Publication


class FakeServiceClient:
    def __init__(self):
        self.calls = []

    def completion_message(self, app_token, *, inputs, user, response_mode="blocking"):
        self.calls.append(("completion", app_token, inputs))

        class R:
            def json(self):
                return {"answer": "hello " + inputs.get("name", ""), "usage": {"total_tokens": 7}}

        return R()

    def chat_message(self, app_token, *, inputs, query, user, response_mode="blocking", conversation_id=None):
        self.calls.append(("chat", app_token, inputs, query))

        class R:
            def json(self):
                return {"answer": "chat " + query, "usage": {"total_tokens": 8}}

        return R()


@pytest.fixture
def client(session):
    fake = FakeServiceClient()

    def _get_db():
        yield session

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_service_client] = lambda: fake
    yield TestClient(app), fake, session
    app.dependency_overrides.clear()


def _seed_key(session, *, scopes=("*",), quota=-1, raw="dhk_testsecretvalue"):
    key = ApiKey(
        name="k",
        key_prefix=raw[:12],
        key_hash=hashlib.sha256(raw.encode()).hexdigest(),
        scopes=list(scopes),
        quota=quota,
    )
    session.add(key)
    session.commit()
    session.refresh(key)
    return key, raw


def _seed_pub(session, slug="greet"):
    pub = Publication(
        slug=slug,
        name="Greet",
        item_type="prompt",
        item_id="p1",
        mode="completion",
        dify_app_id="app-1",
        service_api_token="tok",
        variable_schema=[{"name": "name", "required": True}],
    )
    session.add(pub)
    session.commit()
    session.refresh(pub)
    return pub


def test_run_requires_auth(client):
    c, _, _ = client
    assert c.post("/v1/run/greet", json={"inputs": {"name": "x"}}).status_code == 401


def test_run_full_flow(client):
    c, fake, session = client
    _seed_pub(session)
    _, raw = _seed_key(session)
    r = c.post("/v1/run/greet", json={"inputs": {"name": "Alice"}}, headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 200
    assert r.json()["answer"] == "hello Alice"
    assert fake.calls[0][0] == "completion"


def test_run_scope_denied(client):
    c, _, session = client
    _seed_pub(session)
    _, raw = _seed_key(session, scopes=("other",))
    r = c.post("/v1/run/greet", json={"inputs": {"name": "x"}}, headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 403


def test_run_quota_exceeded(client):
    c, _, session = client
    _seed_pub(session)
    _, raw = _seed_key(session, quota=0)
    r = c.post("/v1/run/greet", json={"inputs": {"name": "x"}}, headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 429


def test_run_missing_required_input(client):
    c, _, session = client
    _seed_pub(session)
    _, raw = _seed_key(session)
    r = c.post("/v1/run/greet", json={"inputs": {}}, headers={"Authorization": f"Bearer {raw}"})
    assert r.status_code == 400


def test_run_rate_limit_exceeded(client, monkeypatch):
    c, _, session = client
    _seed_pub(session)
    _, raw = _seed_key(session)
    # limit = 1/min: first request passes (records usage), second is rate-limited.
    monkeypatch.setattr(public_module, "get_settings", lambda: SimpleNamespace(rate_limit_per_minute=1))
    first = c.post("/v1/run/greet", json={"inputs": {"name": "x"}}, headers={"Authorization": f"Bearer {raw}"})
    assert first.status_code == 200
    second = c.post("/v1/run/greet", json={"inputs": {"name": "x"}}, headers={"Authorization": f"Bearer {raw}"})
    assert second.status_code == 429
