"""FastAPI application entry point."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware
from app.core.rate_limit import limiter
from app.repositories.knowledge_base_repository import load_knowledge_base_repository

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    logger.info("loading_knowledge_base", path=str(settings.knowledge_base_path))
    _app.state.kb_repository = load_knowledge_base_repository(settings.knowledge_base_path)
    logger.info("knowledge_base_loaded")
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Supportive screening and home-guidance API for children's language "
        "delay. This service does not diagnose medical conditions and does "
        "not replace assessment or treatment by a qualified speech-language "
        "therapist."
    ),
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
