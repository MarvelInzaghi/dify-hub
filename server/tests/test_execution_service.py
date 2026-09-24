import pytest
from sqlalchemy import select

from app.models import Publication, Usage
from app.services.execution_service import ExecutionError, ExecutionService, ExecutionValidationError


def _pub(session, **kwargs) -> Publication:
    p = Publication(
        slug=kwargs.pop("slug", "s"),
        name=kwargs.pop("name", "S"),
        item_type="prompt",
        item_id="p1",
        mode=kwargs.pop("mode", "completion"),
        dify_app_id=kwargs.pop("dify_app_id", "app-1"),
        service_api_token=kwargs.pop("service_api_token", "app-token-1"),
        variable_schema=kwargs.pop("variable_schema", []),
    )
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def test_run_completion_blocking_records_usage(session):
    service = FakeService()
    pub = _pub(session, variable_schema=[{"name": "name", "required": True}])
    result = ExecutionService(session, service).run(pub, inputs={"name": "Alice"}, user="u1")
    assert result["answer"] == "hi"
    assert service.calls[0][0] == "completion"
    assert service.calls[0][1] == "app-token-1"
    usage = session.scalars(select(Usage)).all()
    assert len(usage) == 1
    assert usage[0].total_tokens == 15
    assert usage[0].status == "ok"


def test_run_completion_metadata_usage(session):
    """Dify 1.x nests usage under `metadata.usage` — token counts must still be recorded."""
    service = FakeService()
    service.blocking = {
        "answer": "hi",
        "metadata": {
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    }
    pub = _pub(session, variable_schema=[{"name": "name", "required": True}])
    ExecutionService(session, service).run(pub, inputs={"name": "Alice"}, user="u1")
    usage = session.scalars(select(Usage)).all()
    assert len(usage) == 1
    assert usage[0].prompt_tokens == 10
    assert usage[0].completion_tokens == 5
    assert usage[0].total_tokens == 15


def test_run_chat_mode(session):
    service = FakeService()
    pub = _pub(session, mode="chat")
    ExecutionService(session, service).run(pub, inputs={}, query="hello")
    assert service.calls[0][0] == "chat"
    assert service.calls[0][2] == {}


def test_run_validates_required_inputs(session):
    pub = _pub(session, variable_schema=[{"name": "name", "required": True}])
    with pytest.raises(ExecutionValidationError):
        ExecutionService(session, FakeService()).run(pub, inputs={})


def test_run_not_deployed_raises(session):
    pub = _pub(session, dify_app_id=None, service_api_token=None)
    with pytest.raises(ExecutionError):
        ExecutionService(session, FakeService()).run(pub, inputs={})


def test_run_streaming_returns_response(session):
    service = FakeService()
    pub = _pub(session)
    resp = ExecutionService(session, service).run(pub, inputs={}, response_mode="streaming")
    assert list(resp.iter_lines()) == ["data: one", "data: two"]
    assert len(session.scalars(select(Usage)).all()) == 1


class FakeService:
    def __init__(self):
        self.calls = []
        self.blocking = {"answer": "hi", "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}}

    def completion_message(self, app_token, *, inputs, user, response_mode="blocking"):
        self.calls.append(("completion", app_token, inputs, user, response_mode))
        return FakeStreaming() if response_mode == "streaming" else FakeJson(self.blocking)

    def chat_message(self, app_token, *, inputs, query, user, response_mode="blocking", conversation_id=None):
        self.calls.append(("chat", app_token, inputs, query, user, response_mode))
        return FakeStreaming() if response_mode == "streaming" else FakeJson(self.blocking)


class FakeJson:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


class FakeStreaming:
    def iter_lines(self):
        return iter(["data: one", "data: two"])
