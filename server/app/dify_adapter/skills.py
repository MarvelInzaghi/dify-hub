from __future__ import annotations

from typing import Any

from app.dify_adapter.client import DifyConsoleClient


class SkillsClient:
    """Console API wrapper for workspace-level skill management.

    Request/response shapes mirror ``api/controllers/console/workspace/skills.py`` and the
    ``Skill*Payload`` models in ``api/services/skill_management_service.py`` (Dify 1.17.0).
    """

    def __init__(self, client: DifyConsoleClient) -> None:
        self._c = client

    # --- CRUD ---------------------------------------------------------

    def list(self, *, page: int = 1, limit: int = 20, keyword: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "limit": limit}
        if keyword:
            params["keyword"] = keyword
        if tags:
            params["tag"] = tags  # httpx repeats list values: tag=a&tag=b
        return self._c.request("GET", "/workspaces/current/skills", params=params).json()

    def create(
        self,
        *,
        name: str | None = None,
        display_name: str | None = None,
        icon: str = "📄",
        description: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"icon": icon, "description": description, "tags": tags or []}
        if name is not None:
            body["name"] = name
        if display_name is not None:
            body["display_name"] = display_name
        return self._c.request("POST", "/workspaces/current/skills", json=body).json()

    def get(self, skill_id: str) -> dict[str, Any]:
        return self._c.request("GET", f"/workspaces/current/skills/{skill_id}").json()

    def update_metadata(
        self,
        skill_id: str,
        *,
        display_name: str | None = None,
        icon: str | None = None,
        tags: list[str] | None = None,
        expected_updated_at: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if display_name is not None:
            body["display_name"] = display_name
        if icon is not None:
            body["icon"] = icon
        if tags is not None:
            body["tags"] = tags
        if expected_updated_at is not None:
            body["expected_updated_at"] = expected_updated_at
        return self._c.request("PATCH", f"/workspaces/current/skills/{skill_id}", json=body).json()

    def delete(self, skill_id: str, *, confirmation_name: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {}
        if confirmation_name is not None:
            body["confirmation_name"] = confirmation_name
        return self._c.request("DELETE", f"/workspaces/current/skills/{skill_id}", json=body).json()

    def duplicate(self, skill_id: str) -> dict[str, Any]:
        return self._c.request("POST", f"/workspaces/current/skills/{skill_id}/duplicate").json()

    # --- Draft file editing ------------------------------------------

    def upsert_text_file(self, skill_id: str, *, path: str, content: str, expected_updated_at: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"operation": "upsert_text", "path": path, "content": content}
        if expected_updated_at is not None:
            body["expected_updated_at"] = expected_updated_at
        return self._c.request("PATCH", f"/workspaces/current/skills/{skill_id}/files", json=body).json()

    def mkdir(self, skill_id: str, *, path: str, expected_updated_at: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"operation": "mkdir", "path": path}
        if expected_updated_at is not None:
            body["expected_updated_at"] = expected_updated_at
        return self._c.request("PATCH", f"/workspaces/current/skills/{skill_id}/files", json=body).json()

    def rename_file(self, skill_id: str, *, path: str, target_path: str, expected_updated_at: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"operation": "rename", "path": path, "target_path": target_path}
        if expected_updated_at is not None:
            body["expected_updated_at"] = expected_updated_at
        return self._c.request("PATCH", f"/workspaces/current/skills/{skill_id}/files", json=body).json()

    def delete_file(self, skill_id: str, *, path: str, expected_updated_at: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"operation": "delete", "path": path}
        if expected_updated_at is not None:
            body["expected_updated_at"] = expected_updated_at
        return self._c.request("PATCH", f"/workspaces/current/skills/{skill_id}/files", json=body).json()

    # --- Versioning / publishing -------------------------------------

    def publish(self, skill_id: str, *, publish_note: str = "", version_name: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"publish_note": publish_note}
        if version_name is not None:
            body["version_name"] = version_name
        return self._c.request("POST", f"/workspaces/current/skills/{skill_id}/publish", json=body).json()

    def list_versions(self, skill_id: str) -> dict[str, Any]:
        return self._c.request("GET", f"/workspaces/current/skills/{skill_id}/versions").json()

    def restore_version(self, skill_id: str, *, version_id: str, publish_note: str = "", version_name: str | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"version_id": version_id, "publish_note": publish_note}
        if version_name is not None:
            body["version_name"] = version_name
        return self._c.request("POST", f"/workspaces/current/skills/{skill_id}/restore", json=body).json()

    def export(self, skill_id: str) -> bytes:
        """Download the published skill as a zip archive."""
        return self._c.request("GET", f"/workspaces/current/skills/{skill_id}/export").content

    def import_skill(self, *, content: bytes, filename: str) -> dict[str, Any]:
        """Import a skill zip package (multipart field ``file``).

        The zip must contain a ``SKILL.md`` whose frontmatter provides ``name``/``description``.
        Dify parses/validates the archive and returns the created skill detail.
        """
        files = {"file": (filename, content, "application/zip")}
        return self._c.request("POST", "/workspaces/current/skills/import", files=files).json()

    # --- Agent binding ------------------------------------------------

    def list_agent_bindings(self, agent_id: str) -> dict[str, Any]:
        return self._c.request("GET", f"/workspaces/current/agents/{agent_id}/skills").json()

    def replace_agent_bindings(self, agent_id: str, *, skill_ids: list[str]) -> dict[str, Any]:
        return self._c.request("PUT", f"/workspaces/current/agents/{agent_id}/skills", json={"skill_ids": skill_ids}).json()
