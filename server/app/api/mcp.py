"""MCP service factory: dynamically create/list/stop OpenAPI-backed MCP servers.

Each MCP server runs as a separate worker process (``app.mcp_worker``) on its own port,
exposed via streamable-http. The registry is in-memory (not persisted across restarts).
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException

from app.config import get_settings
from app.schemas import McpServerCreate, McpServerOut

router = APIRouter(prefix="/servers", tags=["mcp"])

# name -> {port, openapi_url, process, started_at}
_REGISTRY: dict[str, dict] = {}

_STARTUP_TIMEOUT = 20.0


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _find_free_port(start: int = 8091) -> int:
    for port in range(start, start + 1000):
        if not _port_in_use(port):
            return port
    raise HTTPException(status_code=500, detail="No free port available")


def _mcp_url(port: int) -> str:
    settings = get_settings()
    return f"http://{settings.mcp_public_host}:{port}{settings.mcp_path}"


def _to_out(name: str, entry: dict) -> McpServerOut:
    return McpServerOut(
        name=name,
        port=entry["port"],
        mcp_url=_mcp_url(entry["port"]),
        openapi_url=entry["openapi_url"],
        started_at=entry["started_at"],
    )


@router.post("", response_model=McpServerOut, status_code=201)
def create_server(payload: McpServerCreate) -> McpServerOut:
    settings = get_settings()
    if payload.name in _REGISTRY:
        raise HTTPException(status_code=409, detail=f"MCP server '{payload.name}' already exists")

    port = payload.port if payload.port is not None else _find_free_port()
    if _port_in_use(port):
        raise HTTPException(status_code=409, detail=f"Port {port} is already in use")

    worker_python = settings.mcp_worker_python or sys.executable
    cmd = [
        worker_python,
        "-m",
        "app.mcp_worker",
        "--openapi-url",
        payload.openapi_url,
        "--name",
        payload.name,
        "--port",
        str(port),
        "--host",
        settings.mcp_bind_host,
        "--path",
        settings.mcp_path,
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Wait for the worker to bind the port (or fail fast if it exits).
    deadline = time.time() + _STARTUP_TIMEOUT
    while time.time() < deadline:
        if proc.poll() is not None:
            raise HTTPException(status_code=500, detail=f"MCP worker exited early (code {proc.returncode}); is the OpenAPI URL reachable?")
        if _port_in_use(port):
            break
        time.sleep(0.5)
    else:
        proc.kill()
        raise HTTPException(status_code=500, detail="MCP worker did not start in time")

    entry = {
        "port": port,
        "openapi_url": payload.openapi_url,
        "process": proc,
        "started_at": datetime.now(UTC),
    }
    _REGISTRY[payload.name] = entry
    return _to_out(payload.name, entry)


@router.get("", response_model=list[McpServerOut])
def list_servers() -> list[McpServerOut]:
    return [_to_out(name, entry) for name, entry in _REGISTRY.items()]


@router.delete("/{name}", status_code=204, response_model=None)
def delete_server(name: str) -> None:
    entry = _REGISTRY.pop(name, None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"MCP server '{name}' not found")
    proc = entry["process"]
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
