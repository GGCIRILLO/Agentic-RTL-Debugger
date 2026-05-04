"""FastAPI application – bridge between browser and Temporal.

This server does NOT run Temporal activities or workflows — it only
communicates with the Temporal server via temporalio.client, forwarding
HTTP requests to workflow start / query / signal calls.

Run with:
    uvicorn app.api.main:app --reload --port 8000
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from temporalio.client import Client

from app.config import config

logger = logging.getLogger(__name__)

# Global Temporal client — initialised at startup, reused across requests.
temporal_client: Client | None = None


def get_client() -> Client:
    """Return the shared Temporal client (raises if not yet initialised)."""
    if temporal_client is None:
        raise RuntimeError("Temporal client not initialised")
    return temporal_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    global temporal_client
    logger.info("Connecting to Temporal at %s …", config.temporal_host)
    temporal_client = await Client.connect(config.temporal_host)
    logger.info("Temporal client ready")
    yield
    logger.info("Shutting down API server")


app = FastAPI(
    title="Agentic RTL Debugger",
    version="1.0.0",
    lifespan=lifespan,
)

# ── Routers ────────────────────────────────────────────────────────────────
from app.api.routers import workflows, cases  # noqa: E402  (after app creation)

app.include_router(workflows.router)
app.include_router(cases.router)

# ── Static web UI ──────────────────────────────────────────────────────────
_WEB_DIR = Path(__file__).parent.parent.parent / "web"
if _WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_WEB_DIR), html=True), name="web")
