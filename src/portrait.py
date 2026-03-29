"""
Portrait generation for protagonist agents.

Pipeline:
1. Agent data → Ollama text LLM generates a rich image prompt
2. HuggingFace Inference API (primary) or OllamaDiffuser (fallback) generates the image

Portraits are saved to output/portraits/<run_id>/agent_<id>_t<tick>.png
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PORTRAITS_DIR = Path("output/portraits")


def _ensure_dir(run_id: str) -> Path:
    d = PORTRAITS_DIR / str(run_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── LLM Prompt Generation ──────────────────────────────────────────

def generate_portrait_prompt_llm(agent, narrator) -> Optional[str]:
    """Use the text LLM (via narrator) to craft a rich image-gen prompt from agent data."""
    if not narrator or not narrator.enabled or not narrator._ensure_connected():
        return None

    mate_bonds = [b for b in agent.bonds if b.bond_type == "mate"]
    top_skill = max(agent.skills, key=agent.skills.get) if agent.skills else "survival"
    dom_emo = agent.dominant_emotion or "neutral"
    recent_mems = [m["event"] for m in agent.memory[-5:]]

    system = (
        "You are an expert portrait prompt engineer for AI image generation. "
        "You write highly detailed, evocative prompts that produce stunning character portraits. "
        "Focus on: face, expression, eyes, skin texture, lighting, clothing, props, background atmosphere. "
        "Output ONLY the image prompt, nothing else. No quotes, no preamble."
    )

    prompt = f"""Write a detailed AI image generation prompt for a character portrait based on this data:

CHARACTER: {agent.protagonist_name or f'Agent #{agent.id}'}
- Sex: {agent.sex} | Age: {agent.age} | Phase: {agent.phase} | Generation: {agent.generation}
- Health: {agent.health:.2f} | Wealth: {agent.wealth:.1f}
- Dominant emotion: {dom_emo} | Trauma: {agent.trauma:.2f}

PERSONALITY TRAITS:
- Resilience: {agent.traits.resilience:.2f} | Curiosity: {agent.traits.curiosity:.2f}
- Charisma: {agent.traits.charisma:.2f} | Aggression: {agent.traits.aggression:.2f}
- Sociability: {agent.traits.sociability:.2f}

TOP SKILL: {top_skill} ({agent.skills.get(top_skill, 0):.2f})
BONDS: {len(agent.bonds)} total, {'has a mate' if mate_bonds else 'no mate'}, {len(agent.child_ids)} children

SPECIAL STATUS:
{'- THE ANOMALY: Glowing eyes, reality warps around them' if agent.is_anomaly else ''}
{'- REDPILLED: Sees through the simulation, digital code reflected in eyes' if agent.redpilled else ''}
{'- HIGH AWARENESS: Haunted look, sees things others cannot' if agent.awareness > 0.5 else ''}
{'- SENTINEL: Unnaturally perfect, cold, wearing a dark suit' if agent.is_sentinel else ''}
{'- EXILE: Ancient, mysterious, hidden power' if agent.is_exile else ''}

RECENT LIFE EVENTS: {', '.join(recent_mems[-3:]) if recent_mems else 'nothing notable'}

STYLE REQUIREMENTS:
- Dark cinematic lighting, Matrix-inspired palette (black, deep green, occasional gold)
- Digital rain or faint code in the background
- Photorealistic concept art style, highly detailed face
- The portrait should tell this character's story through their appearance"""

    try:
        raw = narrator.active_provider.generate(system, prompt, temperature=0.8, max_tokens=300)
        if raw:
            return raw.strip()
    except Exception as e:
        logger.error(f"LLM portrait prompt generation failed: {e}")

    return None


# ── Image Generation Providers ──────────────────────────────────────

class HuggingFaceImageProvider:
    """Primary: HuggingFace Inference API for image generation."""

    def __init__(self, model: str = "black-forest-labs/FLUX.1-schnell",
                 token: str = None):
        self.model = model
        self.token = token or os.environ.get("HF_TOKEN")
        self._client = None

    @property
    def name(self):
        return f"hf/{self.model.split('/')[-1]}"

    def connect(self) -> bool:
        if not self.token:
            logger.warning("No HF token for image generation")
            return False
        try:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(token=self.token)
            return True
        except Exception as e:
            logger.error(f"HF image provider connect failed: {e}")
            return False

    def generate(self, prompt: str, output_path: str,
                 width: int = 768, height: int = 1024) -> bool:
        if not self._client and not self.connect():
            return False
        try:
            image = self._client.text_to_image(
                prompt=prompt,
                model=self.model,
                width=width,
                height=height,
            )
            image.save(output_path)
            logger.info(f"HF portrait saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"HF image generation failed: {e}")
            return False


class OllamaDiffuserProvider:
    """Fallback: OllamaDiffuser for local image generation."""

    def __init__(self, model: str = "flux.1-schnell"):
        self.model = model
        self._engine = None
        self._loaded = False

    @property
    def name(self):
        return f"ollamadiffuser/{self.model}"

    def connect(self) -> bool:
        try:
            from ollamadiffuser.core.models.manager import model_manager
            self._manager = model_manager
            return True
        except Exception as e:
            logger.error(f"OllamaDiffuser import failed: {e}")
            return False

    def _ensure_model(self) -> bool:
        if self._loaded and self._manager.is_model_loaded():
            return True
        try:
            success = self._manager.load_model(self.model)
            if success:
                self._engine = self._manager.loaded_model
                self._loaded = True
                return True
            logger.error(f"OllamaDiffuser failed to load model: {self.model}")
            return False
        except Exception as e:
            logger.error(f"OllamaDiffuser model load failed: {e}")
            return False

    def generate(self, prompt: str, output_path: str,
                 width: int = 768, height: int = 1024) -> bool:
        if not self._manager and not self.connect():
            return False
        if not self._ensure_model():
            return False
        try:
            image = self._engine.generate_image(
                prompt=prompt,
                width=width,
                height=height,
                num_inference_steps=4,
                guidance_scale=7.5,
            )
            image.save(output_path)
            logger.info(f"OllamaDiffuser portrait saved: {output_path}")
            return True
        except Exception as e:
            logger.error(f"OllamaDiffuser generation failed: {e}")
            return False


# ── Portrait Generator (orchestrator) ──────────────────────────────

class PortraitGenerator:
    """Orchestrates LLM prompt generation + image generation with provider fallback."""

    def __init__(self, hf_token: str = None,
                 hf_model: str = "black-forest-labs/FLUX.1-schnell",
                 diffuser_model: str = "flux.1-schnell"):
        self.providers = [
            HuggingFaceImageProvider(model=hf_model, token=hf_token),
            OllamaDiffuserProvider(model=diffuser_model),
        ]
        self.active_provider = None

    def _ensure_connected(self) -> bool:
        if self.active_provider:
            return True
        for p in self.providers:
            if p.connect():
                self.active_provider = p
                logger.info(f"Portrait provider: {p.name}")
                return True
        return False

    @property
    def provider_name(self) -> str:
        return self.active_provider.name if self.active_provider else "none"

    def generate_portrait(self, agent, narrator, run_id: str,
                          tick: int) -> Optional[str]:
        """Generate a portrait for an agent. Returns the file path or None."""
        if not self._ensure_connected():
            logger.warning("No image generation provider available")
            return None

        out_dir = _ensure_dir(run_id)
        filename = f"agent_{agent.id}_t{tick}.png"
        output_path = str(out_dir / filename)

        # Step 1: Generate prompt via LLM, fall back to template
        prompt = generate_portrait_prompt_llm(agent, narrator)
        if not prompt:
            from dashboard.state import generate_portrait_prompt
            prompt = generate_portrait_prompt(agent)
            logger.info("Using template portrait prompt (LLM unavailable)")

        # Step 2: Generate image — try each provider
        for provider in self.providers:
            if not provider.connect():
                continue
            success = provider.generate(prompt, output_path)
            if success:
                return output_path

        logger.error("All image generation providers failed")
        return None

    def generate_era_landscape(self, era_name: str, era_desc: str,
                               narrator=None) -> Optional[str]:
        """Generate a landscape image for a civilization era. Returns file path or None."""
        if not self._ensure_connected():
            return None

        out_dir = Path("output/era_landscapes")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_name = era_name.lower().replace(" ", "_")
        output_path = str(out_dir / f"{safe_name}.png")

        if Path(output_path).exists():
            return output_path

        # Generate prompt via LLM or use template
        prompt = None
        if narrator and narrator.enabled and narrator._ensure_connected():
            system = (
                "You are an expert landscape prompt engineer for AI image generation. "
                "Output ONLY the image prompt, nothing else."
            )
            llm_prompt = (
                f"Write a detailed AI image generation prompt for a wide cinematic landscape "
                f"representing the '{era_name}' era of a civilization simulation.\n"
                f"Era description: {era_desc}\n\n"
                f"The landscape should visually represent this stage of civilization — "
                f"show the environment, any settlements or structures appropriate to the era, "
                f"lighting that matches the mood, and a sense of scale.\n"
                f"Style: dark cinematic, Matrix-inspired green/black palette with accent colors, "
                f"digital rain subtly in the sky, wide panoramic aspect ratio, concept art."
            )
            try:
                prompt = narrator.active_provider.generate(system, llm_prompt, temperature=0.8, max_tokens=250)
            except Exception:
                pass

        if not prompt:
            era_prompts = {
                "genesis": "A vast dark void with a single spark of green light emerging. Particles forming into the outline of terrain. Digital rain falling from an empty sky. Black and green palette, cinematic wide shot.",
                "dawn_of_tribes": "A primordial landscape with small clusters of glowing figures gathered around green-lit fires. Vast dark wilderness surrounds them. Matrix-style digital rain in the night sky. Cinematic wide panorama.",
                "tribal_expansion": "Rolling hills dotted with primitive camps, trails connecting settlements. Agents moving across terrain, carrying tools. Green bioluminescent vegetation. Dark atmosphere with green digital aurora.",
                "age_of_awakening": "A settlement with crude structures and gathering places. Agents studying, debating, sharing knowledge. Glowing symbols and patterns in the air. Matrix green circuits visible in the ground. Dramatic lighting.",
                "agricultural_age": "Terraced fields glowing with green-tinged crops. Irrigation channels like circuit boards. Simple but organized village at the center. Warm golden accents against the dark green palette. Wide cinematic shot.",
                "bronze_age": "Forges glowing with green-gold fire. Metal tools and early weapons. Fortified settlement with walls. Smoke and digital particles mix in the sky. Dark cinematic atmosphere with copper and green accents.",
                "trade_era": "A bustling marketplace with caravans of glowing data-streams connecting distant settlements. Ships on digital seas. Wealth and color amid the dark landscape. Matrix code flowing through trade routes.",
                "industrial_age": "Massive machines and factories with green-glowing smokestacks. Gears and circuits visible in architecture. Dark sky lit by industrial fires and digital lightning. Sprawling cityscape, cinematic wide angle.",
            }
            safe_key = safe_name.replace("_", " ").lower().replace(" ", "_")
            prompt = era_prompts.get(safe_key,
                f"Wide cinematic landscape of a civilization in the '{era_name}' era. {era_desc}. "
                f"Dark atmosphere, Matrix-inspired green and black palette, digital rain in sky, concept art style."
            )

        # Generate image (wider aspect for banner)
        for provider in self.providers:
            if not provider.connect():
                continue
            success = provider.generate(prompt, output_path, width=1024, height=384)
            if success:
                return output_path

        return None
