"""Dify upgrade smoke test.

Verifies the Dify adapter works against the pinned target version. Run after EVERY Dify
upgrade; a failure here means the adapter needs updating (never Dify itself).

    cd server && py scripts/smoke.py

Exit code 0 = pass, 1 = fail.
"""

from __future__ import annotations

import logging
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.dify_adapter import DifyAdapterError, DifyClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("smoke")

def _skill_md(name: str) -> str:
    return f"---\nname: {name}\ndescription: A Dify upgrade smoke-test skill.\n---\n\n# smoke\n"


def main() -> int:
    settings = get_settings()
    log.info("Dify target version=%s base=%s", settings.dify_target_version, settings.dify_base_url)
    client = DifyClient(settings)
    try:
        # 1. Skills: auth + read
        skills = client.skills.list(limit=1)
        log.info("[ok] skills.list total=%s", skills.get("total"))

        # 2. Skills: create -> write SKILL.md -> publish -> delete (unique name per run)
        name = f"smoke-{uuid.uuid4().hex[:8]}"
        created = client.skills.create(name=name, display_name="__smoke__", description="smoke")
        sid = created["id"]
        client.skills.upsert_text_file(sid, path="SKILL.md", content=_skill_md(name))
        client.skills.publish(sid)
        client.skills.delete(sid)
        log.info("[ok] skills create/publish/delete -> %s", sid)

        # 3. Apps: create + get (scratch app left in place; delete manually if desired)
        app = client.apps.create(name="__smoke__", mode="completion")
        client.apps.get(app["id"])
        log.info("[ok] apps create/get -> %s", app.get("id"))

        log.info("SMOKE PASSED")
        return 0
    except DifyAdapterError as exc:
        log.error("SMOKE FAILED: %s", exc)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
