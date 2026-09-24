"""Phase 0 proof-of-concept.

Proves the Dify Adapter can authenticate and drive skill CRUD + app creation against a
running Dify instance, without touching Dify source.

Usage (from ``server/``):
    cp ../.env.example .env     # fill DIFY_BASE_URL + one auth strategy
    python scripts/poc.py
"""

from __future__ import annotations

import logging
import os
import sys

# Allow `python scripts/poc.py` to import the `app` package without installing it.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings  # noqa: E402
from app.dify_adapter import DifyAdapterError, DifyClient  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("poc")

_SKILL_MD = """---
name: poc-skill
description: A Phase 0 proof-of-concept skill.
---

# PoC

Answer with a brief friendly greeting.
"""


def main() -> int:
    settings = get_settings()
    client = DifyClient(settings)
    log.info("Dify target version=%s auth_mode=%s base=%s", settings.dify_target_version, client.auth_mode, settings.dify_base_url)

    try:
        # 1. Read: list skills (proves auth + read path)
        skills = client.skills.list(limit=5)
        log.info("list_skills OK: total=%s", skills.get("total"))

        # 2. Create a skill
        created = client.skills.create(display_name="PoC Skill", description="Phase 0 smoke test")
        skill_id = created["id"]
        log.info("create_skill OK: id=%s", skill_id)

        # 3. Write SKILL.md draft (text file)
        client.skills.upsert_text_file(skill_id, path="SKILL.md", content=_SKILL_MD)
        log.info("write SKILL.md OK")

        # 4. Publish version 1
        version = client.skills.publish(skill_id, publish_note="poc")
        log.info("publish OK: version_number=%s", version.get("version_number"))

        # 5. Create an app (proves app endpoint)
        app = client.apps.create(name="PoC App", mode="completion")
        log.info("create_app OK: id=%s", app.get("id"))

        # 6. Read app detail (contains the model-config shape; a full valid model-config
        #    write needs the workspace's model provider settings — see AppsClient.set_model_config)
        detail = client.apps.get(app["id"])
        log.info("get_app OK: mode=%s", detail.get("mode"))

        log.info("PHASE 0 POC PASSED")
        return 0
    except DifyAdapterError as exc:
        log.error("Phase 0 PoC failed: %s", exc)
        return 1
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
