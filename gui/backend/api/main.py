"""FastAPI application — The Construct backend."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path so src imports work
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from gui.backend.api.routes import simulation, agents, world, god_mode, websocket
from gui.backend.api.state import manager

app = FastAPI(
    title="The Construct — Human Matrix Sim API",
    description="Backend API for the Matrix civilization simulator",
    version="2.0.0",
)

# CORS for local dev (SvelteKit runs on different port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routes
app.include_router(simulation.router)
app.include_router(agents.router)
app.include_router(world.router)
app.include_router(god_mode.router)
app.include_router(websocket.router)


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
