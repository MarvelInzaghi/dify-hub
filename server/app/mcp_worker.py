"""MCP worker: build an MCP server from an OpenAPI spec and serve it (streamable-http).

Spawned by the MCP manager (``app.api.mcp``) as a separate process. Not imported by the
main app directly.

    python -m app.mcp_worker --openapi-url http://host:8090/openapi.json \
        --name my-mcp --port 8091 --host 0.0.0.0 --path /mcp
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request

import uvicorn
from fastmcp import FastMCP
from httpx2 import AsyncClient


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an OpenAPI-backed MCP server (streamable-http).")
    parser.add_argument("--openapi-url", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--path", default="/mcp")
    args = parser.parse_args()

    # Fetch + parse the OpenAPI spec (stdlib urllib; the MCP client uses httpx2).
    try:
        with urllib.request.urlopen(args.openapi_url, timeout=30) as resp:
            spec = json.load(resp)
    except Exception as exc:  # noqa: BLE001 - fail fast with a clear message
        print(f"Failed to fetch OpenAPI spec from {args.openapi_url}: {exc}", file=sys.stderr)
        return 1

    # Derive the upstream base URL from the openapi URL (strip the last path segment).
    base_url = args.openapi_url.rsplit("/", 1)[0]
    client = AsyncClient(base_url=base_url, timeout=60)

    mcp = FastMCP.from_openapi(spec, client=client, name=args.name)
    app = mcp.http_app(path=args.path, transport="streamable-http")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
