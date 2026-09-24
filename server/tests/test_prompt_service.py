import pytest

from app.schemas import PromptCreate
from app.services.prompt_service import (
    PromptConflictError,
    PromptNotFoundError,
    PromptService,
    PromptValidationError,
    _build_user_input_form,
)


def _create(svc: PromptService, **kwargs) -> "Prompt":
    data = PromptCreate(name=kwargs.pop("name", "greeting"), display_name=kwargs.pop("display_name", "Greeting"), **kwargs)
    return svc.create(data)


def test_create_and_get(session):
    svc = PromptService(session)
    p = _create(svc, content="Hello {{name}}", variables=[{"name": "name"}])
    assert p.id
    got = svc.get(p.id)
    assert got.name == "greeting"
    assert got.content == "Hello {{name}}"


def test_create_name_conflict(session):
    svc = PromptService(session)
    _create(svc, name="dup")
    with pytest.raises(PromptConflictError):
        _create(svc, name="dup")


def test_update(session):
    svc = PromptService(session)
    p = _create(svc, content="v1")
    updated = svc.update(p.id, PromptUpdateFromDict(display_name="Renamed"))
    assert updated.display_name == "Renamed"


def test_publish_creates_version_and_renders_to_dify(session, dify):
    svc = PromptService(session, dify=dify)
    p = _create(svc, content="Hello {{name}}", variables=[{"name": "name"}])
    v = svc.publish(p.id, changelog="first")
    assert v.version_number == 1
    assert p.dify_app_id == "app-1"
    assert p.latest_published_version_id == v.id
    assert dify.apps.created == [{"name": "Greeting", "mode": "completion"}]
    app_id, config = dify.apps.last_config
    assert app_id == "app-1"
    assert config["pre_prompt"] == "Hello {{name}}"
    assert config["prompt_type"] == "simple"


def test_publish_increments_versions(session, dify):
    svc = PromptService(session, dify=dify)
    p = _create(svc, content="A")
    v1 = svc.publish(p.id)
    v2 = svc.publish(p.id)
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert [x.version_number for x in svc.list_versions(p.id)] == [2, 1]


def test_publish_rejects_undefined_variables(session, dify):
    svc = PromptService(session, dify=dify)
    p = _create(svc, content="Hello {{name}} and {{missing}}", variables=[{"name": "name"}])
    with pytest.raises(PromptValidationError):
        svc.publish(p.id)


def test_publish_does_not_require_dify(session):
    svc = PromptService(session, dify=None)
    p = _create(svc, content="No vars")
    v = svc.publish(p.id)
    assert v.version_number == 1
    assert p.dify_app_id is None


def test_delete_removes_versions(session, dify):
    svc = PromptService(session, dify=dify)
    p = _create(svc, content="A")
    svc.publish(p.id)
    svc.delete(p.id)
    with pytest.raises(PromptNotFoundError):
        svc.get(p.id)


def test_restore_version(session):
    svc = PromptService(session)
    p = _create(svc, content="v1 content", variables=[{"name": "x"}])
    svc.publish(p.id, changelog="v1")
    svc.update(p.id, PromptUpdateFromDict(content="v2 content"))
    assert svc.get(p.id).content == "v2 content"
    v1 = svc.list_versions(p.id)[-1]  # oldest (list is version desc)
    restored = svc.restore_version(p.id, v1.id)
    assert restored.content == "v1 content"
    assert restored.variables[0]["name"] == "x"


def test_list_filter_by_tags(session):
    svc = PromptService(session)
    _create(svc, name="a", tags=["x", "y"])
    _create(svc, name="b", tags=["z"])
    items, total = svc.list(tags=["x"])
    assert total == 1
    assert items[0].name == "a"


def test_build_user_input_form():
    form = _build_user_input_form(
        [
            {"name": "topic", "type": "string", "required": True, "label": "主题"},
            {"name": "count", "type": "number", "required": False},
            {"name": "flag", "type": "boolean", "required": False},
        ]
    )
    assert {"text-input": {"variable": "topic", "label": "主题", "required": True, "description": "", "default": ""}} in form
    assert {"number": {"variable": "count", "label": "count", "required": False, "description": "", "default": ""}} in form
    assert {"checkbox": {"variable": "flag", "label": "flag", "required": False, "description": "", "default": ""}} in form


class PromptUpdateFromDict:
    """Minimal stand-in for PromptUpdate to keep this test dependency-light."""
    def __init__(self, **kwargs):
        self._data = kwargs

    def model_dump(self, exclude_unset=False):
        return dict(self._data)
