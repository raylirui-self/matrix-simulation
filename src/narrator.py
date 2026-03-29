"""
Multi-provider LLM narrator — Ollama (local) + HuggingFace (cloud) + fallback.
"""
from __future__ import annotations

import json
import logging
import os
import random
from pathlib import Path
from typing import Optional

from src.engine import WorldEvent

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"


def _load_prompt(filename: str) -> str:
    return (_PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


NARRATOR_SYSTEM = _load_prompt("narrator.txt")
EVENT_SYSTEM = _load_prompt("event_generator.txt")


def _build_narrator_prompt(summary: dict) -> str:
    cultural = summary.get("cultural_floors", {})
    world = summary.get("world", {})
    return f"""Tick {summary['tick']}. Population: {summary['alive']} alive ({summary['total_born']} born, {summary['total_died']} dead).
Phases: {json.dumps(summary['phases'])}. Max generation: {summary['max_generation']}.
Avg skills: {json.dumps(summary['avg_skills'])}. Avg health: {summary['avg_health']}.
Cultural knowledge floors: {json.dumps(cultural)}.
World: {world.get('avg_resources', '?')} avg resources, {world.get('depleted_cells', 0)} depleted cells.
Technologies unlocked: {world.get('global_techs', [])}.
Recent events: {json.dumps(summary.get('recent_events', []))}.

Narrate this civilization's current state, notable trends, and what the future may hold."""


def _build_event_prompt(summary: dict) -> str:
    return f"""Tick {summary['tick']}. Population: {summary['alive']}.
Phases: {json.dumps(summary['phases'])}. Avg skills: {json.dumps(summary['avg_skills'])}.
Avg health: {summary['avg_health']}. Max generation: {summary['max_generation']}.
Recent events: {json.dumps(summary.get('recent_events', []))}.

Generate one new world event. Respond with ONLY the JSON object."""


def _parse_event_json(raw: str, tick: int) -> Optional[WorldEvent]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    data = json.loads(text[start:end])
    effects = data.get("effects", {})
    effects["health_delta"] = max(-0.15, min(0.1, float(effects.get("health_delta", 0))))
    effects["target"] = effects.get("target", "all")
    if effects["target"] not in ("all", "elders", "children", "adults"):
        effects["target"] = "all"
    if effects.get("skill_boost") not in ("logic", "creativity", "social", "survival", "tech", None):
        effects["skill_boost"] = None
    effects["skill_boost_amount"] = max(0, min(0.1, float(effects.get("skill_boost_amount", 0.03))))
    return WorldEvent(
        tick=tick, name=data.get("name", "unknown")[:50],
        description=data.get("description", "Something happened.")[:200],
        effects=effects,
    )


class OllamaProvider:
    def __init__(self, model: str = "llama3.2"):
        self.model = model
        self._client = None

    @property
    def name(self): return f"ollama/{self.model}"

    def connect(self) -> bool:
        try:
            import ollama
            self._client = ollama.Client()
            self._client.show(self.model)
            return True
        except Exception as e:
            logger.warning(f"Ollama unavailable: {e}")
            return False

    def generate(self, system, prompt, temperature=0.8, max_tokens=400):
        if not self._client and not self.connect():
            return None
        try:
            # Thinking models (qwen3.5) use tokens for reasoning + response,
            # so we need a much higher budget
            total_budget = max_tokens * 4
            r = self._client.chat(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                options={"temperature": temperature, "num_predict": total_budget},
                stream=False,
            )
            msg = r.get("message", {})
            content = msg.get("content", "").strip()
            # If content is empty, the model put everything in thinking field
            if not content:
                thinking = msg.get("thinking", "").strip()
                if thinking:
                    content = thinking
            # Strip leaked thinking prefixes (e.g. "Thinking Process:\n...")
            if content:
                for prefix in ["Thinking Process:", "Thinking:", "Let me ", "Okay,", "Alright,"]:
                    if content.startswith(prefix):
                        # Try to find the actual JSON or monologue after the reasoning
                        # Look for JSON start
                        json_start = content.find("{")
                        if json_start > 0:
                            content = content[json_start:]
                            break
                        # Otherwise skip the first paragraph of thinking
                        parts = content.split("\n\n", 1)
                        if len(parts) > 1:
                            content = parts[1]
                        break
            return content if content else None
        except Exception as e:
            logger.error(f"Ollama failed: {e}")
            return None


class HuggingFaceProvider:
    def __init__(self, model: str = "Qwen/Qwen2.5-72B-Instruct", token: str = None):
        self.model = model
        self.token = token or os.environ.get("HF_TOKEN")
        self._client = None

    @property
    def name(self): return f"hf/{self.model.split('/')[-1]}"

    def connect(self) -> bool:
        if not self.token:
            logger.warning("No HF token")
            return False
        try:
            from huggingface_hub import InferenceClient
            self._client = InferenceClient(model=self.model, token=self.token)
            return True
        except Exception as e:
            logger.warning(f"HuggingFace unavailable: {e}")
            return False

    def generate(self, system, prompt, temperature=0.8, max_tokens=400):
        if not self._client and not self.connect():
            return None
        try:
            r = self._client.chat_completion(
                messages=[{"role": "system", "content": system}, {"role": "user", "content": prompt}],
                max_tokens=max_tokens, temperature=temperature,
            )
            return r.choices[0].message.content
        except Exception as e:
            logger.error(f"HF failed: {e}")
            return None


class Narrator:
    def __init__(self, providers=None, enabled=True):
        self.enabled = enabled
        self.providers = providers or []
        self.active_provider = None

    @classmethod
    def from_config(cls, cfg) -> Narrator:
        nc = cfg.narrator
        if not nc.enabled or nc.provider == "none":
            return cls(enabled=False)
        providers = []
        if nc.provider == "ollama":
            providers.append(OllamaProvider(nc.ollama_model))
            providers.append(HuggingFaceProvider(nc.hf_model))
        else:
            providers.append(HuggingFaceProvider(nc.hf_model))
            providers.append(OllamaProvider(nc.ollama_model))
        return cls(providers=providers, enabled=True)

    def _ensure_connected(self) -> bool:
        if self.active_provider:
            return True
        # Don't retry too frequently — wait 30 seconds between attempts
        import time
        now = time.time()
        last_attempt = getattr(self, '_last_connect_attempt', 0)
        if now - last_attempt < 30:
            return False
        self._last_connect_attempt = now
        for p in self.providers:
            if p.connect():
                self.active_provider = p
                return True
        return False

    def reset_connection(self):
        """Reset connection state so next call retries providers."""
        self.active_provider = None
        self._last_connect_attempt = 0

    @property
    def provider_name(self):
        return self.active_provider.name if self.active_provider else "fallback"

    def narrate(self, summary: dict) -> Optional[str]:
        if not self.enabled or not self._ensure_connected():
            return self._fallback_narrate(summary)
        text = self.active_provider.generate(NARRATOR_SYSTEM, _build_narrator_prompt(summary))
        return text if text else self._fallback_narrate(summary)

    def generate_event(self, summary: dict) -> Optional[WorldEvent]:
        if not self.enabled or not self._ensure_connected():
            return self._fallback_event(summary)
        raw = self.active_provider.generate(EVENT_SYSTEM, _build_event_prompt(summary), temperature=0.9, max_tokens=200)
        if raw:
            try:
                event = _parse_event_json(raw, summary["tick"])
                if event:
                    return event
            except Exception:
                pass
        return self._fallback_event(summary)

    def _fallback_narrate(self, summary: dict) -> str:
        """Generate a template-based narrative when no LLM is available."""
        tick = summary.get("tick", 0)
        pop = summary.get("alive", 0)
        dead = summary.get("total_died", 0)
        born = summary.get("total_born", 0)
        max_gen = summary.get("max_generation", 1)
        avg_health = summary.get("avg_health", 0)
        avg_intel = summary.get("avg_intelligence", 0)
        phases = summary.get("phases", {})
        techs = summary.get("world", {}).get("global_techs", [])
        recent = summary.get("recent_events", [])

        # Era flavor
        if pop == 0:
            return f"**Tick {tick}** — Silence. The last soul has faded. {born} were born across the ages, {dead} returned to dust. The simulation remembers."
        if pop < 10:
            mood = "The few remaining souls cling to existence, each heartbeat a defiance against the void."
        elif pop < 30:
            mood = "A small but resilient band endures. Bonds are forged from necessity as much as affection."
        elif pop < 80:
            mood = "The community grows. Shelters cluster together, and the first traditions take root."
        elif pop < 150:
            mood = "A thriving settlement hums with activity. Generations overlap, elders teaching the young."
        elif pop < 300:
            mood = "The civilization expands rapidly. Factions jostle for influence as resources stretch thin."
        else:
            mood = "A sprawling society teems with life. The weight of its own complexity begins to show."

        # Health color
        if avg_health > 0.7:
            health_note = "The people are healthy and strong."
        elif avg_health > 0.4:
            health_note = "Health is adequate, though hardship leaves its mark."
        else:
            health_note = "Sickness and exhaustion plague the populace."

        # Intelligence
        if avg_intel > 0.5:
            intel_note = f"Knowledge flourishes — average intelligence has reached {avg_intel:.2f}."
        elif avg_intel > 0.2:
            intel_note = f"Minds sharpen slowly, with average intelligence at {avg_intel:.2f}."
        else:
            intel_note = "Understanding comes slowly in these early days."

        # Tech
        tech_note = ""
        if techs:
            tech_note = f" Technologies discovered: {', '.join(techs)}."

        # Recent events
        event_note = ""
        if recent:
            last = recent[-1] if isinstance(recent[-1], str) else recent[-1].get("name", "an event")
            event_note = f" Most recently, *{last}* shook the world."

        # Generation
        gen_note = f"The civilization spans {max_gen} generation{'s' if max_gen != 1 else ''}."

        # Demographics
        elders = phases.get("elder", 0)
        children = phases.get("child", 0) + phases.get("infant", 0)
        demo_note = ""
        if elders > pop * 0.3:
            demo_note = " The population skews old — wisdom abounds, but the future needs youth."
        elif children > pop * 0.4:
            demo_note = " Children outnumber adults — a generation boom is underway."

        return (
            f"**Tick {tick}** — Population: {pop} ({born} born, {dead} fallen).\n\n"
            f"{mood} {health_note} {intel_note}{tech_note}{event_note}\n\n"
            f"{gen_note}{demo_note}"
        )

    def _fallback_event(self, summary: dict) -> WorldEvent:
        tick = summary.get("tick", 0)
        pop = summary.get("alive", 0)
        pool = [
            ("harsh_winter", "Bitter cold tests everyone.", {"target": "all", "health_delta": -0.05, "skill_boost": "survival", "skill_boost_amount": 0.03}),
            ("knowledge_bloom", "Ideas spread rapidly.", {"target": "all", "health_delta": 0.0, "skill_boost": "logic", "skill_boost_amount": 0.05}),
            ("plague", "Disease strikes elders.", {"target": "elders", "health_delta": -0.12, "skill_boost": None, "skill_boost_amount": 0}),
            ("tech_discovery", "A breakthrough emerges.", {"target": "adults", "health_delta": 0.0, "skill_boost": "tech", "skill_boost_amount": 0.06}),
            ("creative_renaissance", "Art flourishes.", {"target": "all", "health_delta": 0.01, "skill_boost": "creativity", "skill_boost_amount": 0.04}),
            ("drought", "Water becomes scarce.", {"target": "all", "health_delta": -0.06, "skill_boost": "survival", "skill_boost_amount": 0.04}),
        ]
        if pop < 20:
            pool = [
                ("bountiful_harvest", "Resources fuel recovery.", {"target": "all", "health_delta": 0.08, "skill_boost": "survival", "skill_boost_amount": 0.03}),
                ("unity_pact", "Communities unite.", {"target": "all", "health_delta": 0.03, "skill_boost": "social", "skill_boost_amount": 0.05}),
            ]
        name, desc, effects = random.choice(pool)
        return WorldEvent(tick=tick, name=name, description=desc, effects=effects)