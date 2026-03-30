"""Portrait and era landscape generation endpoints."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from gui.backend.api.state import manager

router = APIRouter(prefix="/api/sim/{run_id}/media", tags=["media"])


@router.post("/portrait/{agent_id}")
def generate_portrait(run_id: str, agent_id: int):
    """Generate a portrait for the specified agent."""
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
        path = generator.generate_portrait(agent, narrator, run_id, tick)
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
def generate_landscape(run_id: str):
    """Generate an era landscape for the current era."""
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
        path = generator.generate_era_landscape(era_name, era_desc, narrator)
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
    safe_name = era.lower().replace(" ", "_")
    landscape_dir = Path("output/era_landscapes")
    path = landscape_dir / f"{safe_name}.png"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No landscape found for era: {era}")

    return FileResponse(path, media_type="image/png")


@router.post("/narrate")
def generate_narrative(run_id: str):
    """Generate an LLM narrative about the current state."""
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
        narrative = narrator.narrate(summary)
        return {"status": "ok", "narrative": narrative}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/monologue/{agent_id}")
def generate_monologue(run_id: str, agent_id: int):
    """Generate an inner monologue for a protagonist."""
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
        result = protagonist_inner_monologue(agent, cfg, narrator, tick, use_llm=cfg.narrator.enabled)
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
