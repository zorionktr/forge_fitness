"""FastAPI application factory (docs/09 §1)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.api.v1.router import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: optionally ensure the schema exists (create-if-missing), then warm caches etc.
    if settings.auto_init_db:
        from app.db.init import init_db

        await init_db()
    yield
    # shutdown: close pools/producers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Forge API",
        version="0.1.0",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.env == "local" else ["https://forge.app"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.env}

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
