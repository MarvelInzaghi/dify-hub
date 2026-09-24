"""Full e2e flow against the deployed backend (mirrors scripts/e2e.py, parameterized base).

Usage: python e2e_test.py http://localhost:8100
"""
import sys
import time
import uuid

import httpx

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8100"


def main() -> int:
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
    print(f"[1] create prompt -> {r.status_code}")
    if r.status_code != 201:
        print("    body:", r.text[:500])
        return 1
    prompt = r.json()
    print("    prompt_id =", prompt["id"])

    # 2. publish (renders into a Dify app + fetches Service API token)
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/api/publications",
        json={"prompt_id": prompt["id"], "slug": slug, "changelog": "e2e"},
        timeout=120,
    )
    print(f"[2] publish -> {r.status_code} ({time.time()-t0:.1f}s)")
    if r.status_code != 201:
        print("    body:", r.text[:500])
        return 1
    pub = r.json()
    print("    slug =", pub.get("slug"), "| dify_app_id =", pub.get("dify_app_id"), "| mode =", pub.get("mode"))

    # 3. create api key
    r = httpx.post(
        f"{BASE}/api/api-keys",
        json={"name": "e2e-key", "scopes": ["*"], "quota": -1},
        timeout=30,
    )
    print(f"[3] create api key -> {r.status_code}")
    if r.status_code != 201:
        print("    body:", r.text[:500])
        return 1
    key = r.json()
    print("    key_prefix =", key.get("key_prefix"), "…")

    # 4. run (blocking) via public API
    t0 = time.time()
    r = httpx.post(
        f"{BASE}/v1/run/{slug}",
        json={"inputs": {"topic": "人工智能"}, "response_mode": "blocking"},
        headers={"Authorization": f"Bearer {key['api_key']}"},
        timeout=300,
    )
    print(f"[4] run -> {r.status_code} ({time.time()-t0:.1f}s)")
    print("    body:", r.text[:1500])
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
