import pytest

from app.schemas import SkillCreate
from app.services.skill_service import DifyNotConfiguredError, SkillConflictError, SkillNotFoundError, SkillService


def _create(svc: SkillService, **kwargs) -> "Skill":
    data = SkillCreate(display_name=kwargs.pop("display_name", "My Skill"), **kwargs)
    return svc.create(data)


def test_create_delegates_to_dify(session, dify):
    svc = SkillService(session, dify)
    s = _create(svc, name="my-skill", category="support", tags=["a"])
    assert s.dify_skill_id == "dify-skill-1"
    assert s.name == "my-skill"
    assert s.category == "support"
    assert dify.skills.skills["dify-skill-1"]["name"] == "my-skill"


def test_create_name_conflict(session, dify):
    svc = SkillService(session, dify)
    _create(svc, name="dup")
    with pytest.raises(SkillConflictError):
        _create(svc, name="dup")


def test_upsert_file_and_detail(session, dify):
    svc = SkillService(session, dify)
    s = _create(svc, name="s")
    svc.upsert_file(s.id, path="SKILL.md", content="---\nname: s\n---\n")
    detail = svc.detail(s.id)
    assert detail["files"] == [{"path": "SKILL.md", "content": "---\nname: s\n---\n"}]


def test_publish_pins_version(session, dify):
    svc = SkillService(session, dify)
    s = _create(svc, name="s")
    v = svc.publish(s.id, changelog="v1")
    assert v["version_number"] == 1
    assert s.latest_dify_skill_version_id == "ver-dify-skill-1-1"
    assert svc.list_versions(s.id)["data"][0]["version_number"] == 1


def test_bind_maps_registry_ids_to_dify_ids(session, dify):
    svc = SkillService(session, dify)
    a = _create(svc, name="a")
    b = _create(svc, name="b")
    svc.bind_to_agent("agent-1", skill_ids=[a.id, b.id])
    assert dify.skills.bound == [("agent-1", ["dify-skill-1", "dify-skill-2"])]


def test_delete_removes_both(session, dify):
    svc = SkillService(session, dify)
    s = _create(svc, name="s")
    svc.delete(s.id)
    assert "dify-skill-1" in dify.skills.deleted
    with pytest.raises(SkillNotFoundError):
        svc.get(s.id)


def test_requires_dify(session):
    svc = SkillService(session, None)
    with pytest.raises(DifyNotConfiguredError):
        _create(svc, name="s")


def test_file_op_rename_and_delete(session, dify):
    svc = SkillService(session, dify)
    s = _create(svc, name="s")
    svc.upsert_file(s.id, path="SKILL.md", content="x")
    svc.upsert_file(s.id, path="docs/guide.md", content="y")
    svc.file_op(s.id, operation="rename", path="docs/guide.md", target_path="docs/readme.md")
    svc.file_op(s.id, operation="delete", path="SKILL.md")
    files = dify.skills.files["dify-skill-1"]
    assert "docs/readme.md" in files
    assert "SKILL.md" not in files


def test_list_syncs_from_dify(session, dify):
    svc = SkillService(session, dify)
    # A skill created directly in Dify (not via dify-hub) should appear after list() syncs.
    dify.skills.skills["dify-direct-1"] = {
        "id": "dify-direct-1",
        "name": "direct-skill",
        "display_name": "Direct Skill",
        "icon": "📄",
        "description": "made in Dify",
        "tags": [],
        "latest_published_version_id": None,
    }
    items, _ = svc.list()
    assert "direct-skill" in {s.name for s in items}

    # A skill removed from Dify should disappear from the local registry after sync.
    del dify.skills.skills["dify-direct-1"]
    items, _ = svc.list()
    assert "direct-skill" not in {s.name for s in items}
