"""FastAPI application — The Nexus backend."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so src imports work
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import logging  # noqa: E402
import os  # noqa: E402

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from gui.backend.api.auth import god_mode_enabled  # noqa: E402
from gui.backend.api.routes import (  # noqa: E402
    agents,
    causal,
    god_mode,
    media,
    simulation,
    websocket,
    world,
)
from gui.backend.api.state import manager  # noqa: E402

logger = logging.getLogger("nexus.api")

app = FastAPI(
    title="The Nexus — Cognitive Matrix Sim API",
    description="Backend API for the Matrix civilization simulator",
    version="2.0.0",
)

# CORS — origins read from CORS_ORIGINS env (comma-separated); in production
# (ENV=production), reject wildcards at startup to avoid accidental exposure.
_default_origins = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
_origins_raw = os.getenv("CORS_ORIGINS", _default_origins)
_cors_origins = [o.strip() for o in _origins_raw.split(",") if o.strip()]
if os.getenv("ENV", "").lower() == "production" and "*" in _cors_origins:
    raise RuntimeError("CORS_ORIGINS must not contain '*' in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Admin-Token", "Accept"],
)

# Mount routes
app.include_router(simulation.router)
app.include_router(agents.router)
app.include_router(world.router)
if god_mode_enabled():
    app.include_router(god_mode.router)
    logger.warning("GOD_MODE_ENABLED=1 — god-mode endpoints are live. Do not expose publicly.")
else:
    logger.info("God mode disabled (set GOD_MODE_ENABLED=1 to enable).")
app.include_router(websocket.router)
app.include_router(media.router)
app.include_router(causal.router)


@app.get("/api/runs")
def list_runs():
    """List all simulation runs."""
    return {"runs": manager.db.list_runs()}


@app.get("/api/config/eras")
def list_eras():
    """List available era presets."""
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    return {"eras": cfg.list_eras()}


@app.get("/api/config/scenarios")
def list_scenarios():
    """List available scenarios."""
    from src.config_loader import SimConfig
    cfg = SimConfig.load()
    return {"scenarios": cfg.list_scenarios()}


@app.get("/api/health")
def health_check():
    return {"status": "ok", "name": "the-construct"}
