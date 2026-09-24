from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register models on Base.metadata)
from app.db import Base


class FakeAppsClient:
    def __init__(self) -> None:
        self.created: list[dict] = []
        self.last_config: tuple[str, dict] | None = None
        self.api_keys: dict[str, list[dict]] = {}

    def create(self, *, name, mode, **kwargs) -> dict:
        self.created.append({"name": name, "mode": mode})
        return {"id": f"app-{len(self.created)}"}

    def set_model_config(self, app_id: str, *, config: dict) -> dict:
        self.last_config = (app_id, config)
        return {"result": "success"}

    def list_api_keys(self, app_id: str) -> dict:
        return {"data": list(self.api_keys.get(app_id, []))}

    def create_api_key(self, app_id: str) -> dict:
        keys = self.api_keys.setdefault(app_id, [])
        token = f"app-{app_id}-{len(keys) + 1}"
        key = {"id": f"key-{len(keys) + 1}", "token": token}
        keys.append(key)
        return key


class FakeJsonResponse:
    def __init__(self, data: dict) -> None:
        self._data = data

    def json(self) -> dict:
        return self._data


class FakeStreamingResponse:
    def iter_lines(self):
        return iter(["data: one", "data: two"])


class FakeServiceClient:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.blocking = {"answer": "hi", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}

    def completion_message(self, app_token, *, inputs, user, response_mode="blocking"):
        self.calls.append(("completion", app_token, inputs, user, response_mode))
        return FakeStreamingResponse() if response_mode == "streaming" else FakeJsonResponse(self.blocking)

    def chat_message(self, app_token, *, inputs, query, user, response_mode="blocking", conversation_id=None):
        self.calls.append(("chat", app_token, inputs, query, user, response_mode))
        return FakeStreamingResponse() if response_mode == "streaming" else FakeJsonResponse(self.blocking)


class FakeSkillsClient:
    def __init__(self) -> None:
        self.skills: dict[str, dict] = {}  # dify_skill_id -> dict
        self.files: dict[str, dict[str, str]] = {}
        self.versions: dict[str, list[dict]] = {}
        self.deleted: list[str] = []
        self.bound: list[tuple[str, list[str]]] = []
        self._next = 0

    def create(self, *, name=None, display_name=None, icon="📄", description="", tags=None) -> dict:
        self._next += 1
        sid = f"dify-skill-{self._next}"
        nm = name or f"untitled-{self._next}"
        self.skills[sid] = {
            "id": sid,
            "name": nm,
            "display_name": display_name or nm,
            "icon": icon,
            "description": description,
            "tags": tags or [],
            "latest_published_version_id": None,
        }
        self.files[sid] = {}
        return dict(self.skills[sid])

    def list(self, *, page: int = 1, limit: int = 20, keyword: str | None = None, tags: list[str] | None = None) -> dict:
        data = [dict(s) for s in self.skills.values()]
        return {"data": data, "has_more": False, "total": len(data), "page": page, "limit": limit}

    def get(self, skill_id: str) -> dict:
        s = dict(self.skills[skill_id])
        s["files"] = [{"path": p, "content": c} for p, c in self.files[skill_id].items()]
        s["latest_published_version_number"] = len(self.versions.get(skill_id, []))
        return s

    def update_metadata(self, skill_id: str, **kw) -> dict:
        for k, v in kw.items():
            if v is not None:
                self.skills[skill_id][k] = v
        return dict(self.skills[skill_id])

    def delete(self, skill_id: str, *, confirmation_name=None) -> dict:
        del self.skills[skill_id]
        self.deleted.append(skill_id)
        return {"id": skill_id, "deleted": True}

    def upsert_text_file(self, skill_id: str, *, path, content, expected_updated_at=None) -> dict:
        self.files[skill_id][path] = content
        return self.get(skill_id)

    def mkdir(self, skill_id: str, *, path, expected_updated_at=None) -> dict:
        self.files[skill_id].setdefault(path.rstrip("/") + "/.keep", "")
        return self.get(skill_id)

    def rename_file(self, skill_id: str, *, path, target_path, expected_updated_at=None) -> dict:
        if path in self.files[skill_id]:
            self.files[skill_id][target_path] = self.files[skill_id].pop(path)
        return self.get(skill_id)

    def delete_file(self, skill_id: str, *, path, expected_updated_at=None) -> dict:
        self.files[skill_id].pop(path, None)
        return self.get(skill_id)

    def publish(self, skill_id: str, *, publish_note="", version_name=None) -> dict:
        vlist = self.versions.setdefault(skill_id, [])
        vn = len(vlist) + 1
        v = {
            "id": f"ver-{skill_id}-{vn}",
            "skill_id": skill_id,
            "version_number": vn,
            "version_name": version_name or "",
            "publish_note": publish_note,
        }
        vlist.append(v)
        self.skills[skill_id]["latest_published_version_id"] = v["id"]
        return dict(v)

    def list_versions(self, skill_id: str) -> dict:
        return {"data": list(reversed(self.versions.get(skill_id, [])))}

    def replace_agent_bindings(self, agent_id: str, *, skill_ids: list[str]) -> dict:
        self.bound.append((agent_id, skill_ids))
        return {"agent_id": agent_id, "skill_ids": skill_ids, "data": []}


class FakeDifyClient:
    def __init__(self) -> None:
        self.apps = FakeAppsClient()
        self.skills = FakeSkillsClient()


@pytest.fixture
def session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool, future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    s = factory()
    yield s
    s.close()
    engine.dispose()


@pytest.fixture
def dify() -> FakeDifyClient:
    return FakeDifyClient()
