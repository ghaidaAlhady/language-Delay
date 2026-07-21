"""FastAPI application entry point.

Claude Code should replace this starter with the complete versioned API while
preserving the health endpoint for CI and deployment checks.
"""
from fastapi import FastAPI

app = FastAPI(
    title="Smart Guide for Children's Language Delay API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
