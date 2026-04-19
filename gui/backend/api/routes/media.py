"""Portrait and era landscape generation endpoints."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse

from gui.backend.api.auth import rate_limit, require_admin_if_media
from gui.backend.api.state import manager

logger = logging.getLogger("nexus.media")

router = APIRouter(
    prefix="/api/sim/{run_id}/media",
    tags=["media"],
    dependencies=[Depends(require_admin_if_media)],
)

# Media generation calls external LLM / image providers — cap per-IP usage so
# an unauthenticated attacker can't burn the inference budget.
_MEDIA_RATE = (10, 60.0)  # 10 calls per 60 seconds

# M-5: Hard timeout on synchronous LLM calls. Prior behavior: `def` routes
# ran the provider inline and could block a worker thread for >30s on a
# hung Ollama/HF endpoint. Every media endpoint is now `async def` and uses
# `_await_with_timeout` which offloads the sync LLM call to a worker thread
# and cancels it if the timeout expires. The 504 return lets the rate
# limiter bucket fill normally even when the provider is unreachable.
_LLM_TIMEOUT_SECONDS = 30.0


async def _await_with_timeout(blocking_call, *, timeout: float = _LLM_TIMEOUT_SECONDS):
    """Run a synchronous LLM call in a worker thread with a hard timeout.

    Returns the call's result on success, None on timeout, and re-raises
    any other exception so callers see the real error.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(blocking_call),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning("LLM call timed out after %.1fs", timeout)
        return None


@router.post("/portrait/{agent_id}")
async def generate_portrait(run_id: str, agent_id: int, request: Request):
    """Generate a portrait for the specified agent."""
    rate_limit(request, key="media_portrait", max_calls=_MEDIA_RATE[0], window_seconds=_MEDIA_RATE[1])
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agent = next((a for a in engine.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = manager.get_config(run_id)
    if not cfg:
        raise HTTPException(status_code=500, detail="Config not found")

    try:
        from src.portrait import PortraitGenerator
        from src.narrator import Narrator

        narrator = Narrator.from_config(cfg)
        generator = PortraitGenerator()
        tick = engine.state.current_tick
        path = await _await_with_timeout(
            lambda: generator.generate_portrait(agent, narrator, run_id, tick)
        )
        if path is None:
            return {"status": "error", "message": "Portrait generation timed out"}
        if path and Path(path).exists():
            return {"status": "ok", "path": str(path), "url": f"/api/sim/{run_id}/media/portrait/{agent_id}/image"}
        else:
            return {"status": "error", "message": "Portrait generation failed — check LLM/image provider config"}
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Portrait generation module not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portrait/{agent_id}/image")
def get_portrait_image(run_id: str, agent_id: int):
    """Get the latest portrait image for an agent."""
    portrait_dir = Path(f"output/portraits/{run_id}")
    if not portrait_dir.exists():
        raise HTTPException(status_code=404, detail="No portraits found")

    # Find latest portrait for this agent
    pattern = f"agent_{agent_id}_t*.png"
    files = sorted(portrait_dir.glob(pattern), reverse=True)
    if not files:
        raise HTTPException(status_code=404, detail="No portrait found for this agent")

    return FileResponse(files[0], media_type="image/png")


@router.post("/landscape")
async def generate_landscape(run_id: str, request: Request):
    """Generate an era landscape for the current era."""
    rate_limit(request, key="media_landscape", max_calls=_MEDIA_RATE[0], window_seconds=_MEDIA_RATE[1])
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    cfg = manager.get_config(run_id)
    if not cfg:
        raise HTTPException(status_code=500, detail="Config not found")

    # Detect current era
    alive = engine.get_alive_agents()
    pop = len(alive)
    avg_iq = sum(a.intelligence for a in alive) / max(1, pop)
    techs = list(engine.world.global_techs)

    era_name, era_desc = _detect_era(pop, avg_iq, techs)

    try:
        from src.portrait import PortraitGenerator
        from src.narrator import Narrator

        narrator = Narrator.from_config(cfg)
        generator = PortraitGenerator()
        path = await _await_with_timeout(
            lambda: generator.generate_era_landscape(era_name, era_desc, narrator)
        )
        if path is None:
            return {"status": "error", "message": "Landscape generation timed out"}
        if path and Path(path).exists():
            return {
                "status": "ok",
                "era": era_name,
                "description": era_desc,
                "url": f"/api/sim/{run_id}/media/landscape/image?era={era_name}"
            }
        else:
            return {"status": "error", "message": "Landscape generation failed — check LLM/image provider config"}
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Portrait generation module not available: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/landscape/image")
def get_landscape_image(run_id: str, era: str = "genesis"):
    """Get the landscape image for an era."""
    # Sanitize era name to prevent path traversal
    safe_name = "".join(c for c in era.lower().replace(" ", "_") if c.isalnum() or c == "_")
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid era name")
    landscape_dir = Path("output/era_landscapes")
    path = landscape_dir / f"{safe_name}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No landscape found for era: {era}")

    return FileResponse(path, media_type="image/png")


@router.post("/narrate")
async def generate_narrative(run_id: str, request: Request):
    """Generate an LLM narrative about the current state."""
    rate_limit(request, key="media_narrate", max_calls=_MEDIA_RATE[0], window_seconds=_MEDIA_RATE[1])
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    cfg = manager.get_config(run_id)
    if not cfg:
        raise HTTPException(status_code=500, detail="Config not found")

    try:
        from src.narrator import Narrator
        narrator = Narrator.from_config(cfg)
        summary = engine.get_population_summary()
        narrative = await _await_with_timeout(lambda: narrator.narrate(summary))
        if narrative is None:
            return {"status": "error", "message": "Narrate timed out"}
        return {"status": "ok", "narrative": narrative}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/monologue/{agent_id}")
async def generate_monologue(run_id: str, agent_id: int, request: Request):
    """Generate an inner monologue for a protagonist."""
    rate_limit(request, key="media_monologue", max_calls=_MEDIA_RATE[0], window_seconds=_MEDIA_RATE[1])
    engine = manager.get_engine(run_id)
    if not engine:
        engine = manager.load_sim(run_id)
    if not engine:
        raise HTTPException(status_code=404, detail="Simulation not found")

    agent = next((a for a in engine.agents if a.id == agent_id), None)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    cfg = manager.get_config(run_id)
    if not cfg:
        raise HTTPException(status_code=500, detail="Config not found")

    try:
        from src.agency import protagonist_inner_monologue
        from src.narrator import Narrator
        narrator = Narrator.from_config(cfg)
        tick = engine.state.current_tick
        result = await _await_with_timeout(
            lambda: protagonist_inner_monologue(
                agent, cfg, narrator, tick, use_llm=cfg.narrator.enabled,
            )
        )
        if result is None:
            return {"status": "error", "message": "Monologue timed out"}
        if result:
            agent.inner_monologue.append({"tick": tick, **result})
        return {"status": "ok", "monologue": result}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def _detect_era(pop: int, avg_iq: float, techs: list[str]) -> tuple[str, str]:
    """Detect the current era based on population and tech."""
    if "industrialization" in techs:
        return "Industrial Age", "Machines reshape the world"
    if "trade_networks" in techs:
        return "Trade Era", "Commerce connects communities"
    if "mining" in techs:
        return "Bronze Age", "Metal tools forge a new world"
    if "agriculture" in techs:
        return "Agricultural Age", "Settled life begins"
    if avg_iq > 0.3:
        return "Age of Awakening", "Knowledge grows rapidly"
    if pop > 80:
        return "Tribal Expansion", "Clans spread across the land"
    if pop > 20:
        return "Dawn of Tribes", "Small groups form bonds"
    if pop > 0:
        return "Genesis", "Life stirs in the void"
    return "The Void", "Nothing remains..."
