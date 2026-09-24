from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.api_keys import router as api_keys_router
from app.api.mcp import router as mcp_router
from app.api.prompts import router as prompts_router
from app.api.public import router as public_router
from app.api.publications import router as publications_router
from app.api.skills import router as skills_router
from app.api.usage import router as usage_router
from app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="dify-hub", version="0.1.0", lifespan=lifespan)
    app.include_router(prompts_router, prefix="/api")
    app.include_router(skills_router, prefix="/api")
    app.include_router(api_keys_router, prefix="/api")
    app.include_router(publications_router, prefix="/api")
    app.include_router(usage_router, prefix="/api")
    app.include_router(mcp_router, prefix="/api/mcp")
    app.include_router(public_router)  # already prefixed with /v1
    return app


app = create_app()
