"""Full end-to-end test against a real Dify.

Flow: create prompt -> publish (renders to a Dify app + fetches Service API token) ->
create API key -> external POST /v1/run/{slug} -> model response.

Requires the backend running (`uvicorn app.main:app`) and Dify configured in `.env`.

    cd server && py scripts/e2e.py
"""

from __future__ import annotations

import os
import sys
import time
import uuid

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:8000"


def wait_for_backend(timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"{BASE}/api/prompts", timeout=3)
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("backend not reachable")


def main() -> int:
    wait_for_backend()
    suffix = uuid.uuid4().hex[:6]
    name = f"e2e-intro-{suffix}"
    slug = name

    # 1. create prompt
    r = httpx.post(
        f"{BASE}/api/prompts",
        json={
            "name": name,
            "display_name": "E2E 简介",
            "mode": "completion",
            "content": "请用一句话介绍 {{topic}}。",
            "variables": [{"name": "topic", "type": "string", "required": True}],
        },
        timeout=30,
    )
    r.raise_for_status()
    prompt = r.json()
    print("[1] create prompt ->", prompt["id"])

    # 2. publish
    r = httpx.post(f"{BASE}/api/publications", json={"prompt_id": prompt["id"], "slug": slug, "changelog": "e2e"}, timeout=120)
    r.raise_for_status()
    pub = r.json()
    print("[2] publish -> slug:", pub["slug"], "| dify_app_id:", pub["dify_app_id"], "| mode:", pub["mode"])

    # 3. create api key
    r = httpx.post(f"{BASE}/api/api-keys", json={"name": "e2e-key", "scopes": ["*"], "quota": -1}, timeout=30)
    r.raise_for_status()
    key = r.json()
    print("[3] api key ->", key["key_prefix"], "… (plaintext returned once)")

    # 4. run
    r = httpx.post(
        f"{BASE}/v1/run/{slug}",
        json={"inputs": {"topic": "人工智能"}, "response_mode": "blocking"},
        headers={"Authorization": f"Bearer {key['api_key']}"},
        timeout=180,
    )
    print("[4] run status:", r.status_code)
    body = r.text
    print("[4] run body:", body[:1500])
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
