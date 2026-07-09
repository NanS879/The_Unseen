"""
Unified LLM Interface — pluggable AI backends.

All AI backends implement this protocol. The WorldBrain calls
these methods. If no backend is available, RuleEngine is the
deterministic fallback.

Design:
    - async-but-sync: AI calls return immediately, actual work
      happens in a background thread
    - All methods accept JSON dicts and return JSON dicts
    - Never send raw images/video — only structured data
"""

import json
import threading
from abc import ABC, abstractmethod
from typing import Optional


class LLMInterface(ABC):
    """Protocol for AI backends.

    Subclass this to add a new backend (Claude, OpenAI, local model...).
    All methods must be non-blocking.
    """

    @abstractmethod
    def analyze_session(self, context: dict) -> Optional[dict]:
        """Analyze the current session and return world adjustments.

        Args:
            context: {"user_behavior": {...}, "world_state": {...},
                       "organism_state": {...}, "memory": {...}}

        Returns:
            {"user_archetype": "Creator",
             "world_mood": "Hopeful",
             "weather": "Aurora",
             "lighting": "Warm",
             "organism_strategy": "Curious",
             "narrative": "The forest remembered your silence.",
             "recommended_event": "Bloom"}
        """

    @abstractmethod
    def generate_narrative(self, context: dict) -> str:
        """Generate one narrative sentence for a session.

        Args:
            context: Session summary dict.

        Returns:
            A single poetic sentence in English.
        """

    @abstractmethod
    def propose_evolution(self, context: dict) -> dict:
        """Propose world changes for the next phase.

        Args:
            context: {"world_age": ..., "total_visits": ...,
                       "total_organisms": ..., "dominant_archetype": ...}

        Returns:
            {"suggestion": "add_aurora_weather",
             "confidence": 0.7,
             "reason": "User has visited 10+ times"}
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the backend is ready to use."""


class RuleEngine(LLMInterface):
    """Deterministic fallback when no AI backend is available.

    Uses simple heuristics based on session stats — no randomness,
    no hardcoded magic. Every decision maps to a clear rule.
    """

    def is_available(self) -> bool:
        return True  # Always available

    def analyze_session(self, context: dict) -> dict:
        behavior = context.get("user_behavior", {})
        world = context.get("world_state", {})
        memory = context.get("memory", {})

        dwell = behavior.get("total_dwell_time", 0)
        distance = behavior.get("total_distance", 0)
        seeds = behavior.get("seed_count", 0)
        gestures = behavior.get("gesture_frequency", {})
        organisms = world.get("organism_count", 0)
        energy = world.get("energy", 30)
        visits = memory.get("total_visits", 1)

        # ── Archetype ──────────────────────────────────
        if seeds >= 3 and dwell > distance * 0.2:
            archetype = "Creator"
        elif distance > 3000 and gestures.get("swipe", 0) > 5:
            archetype = "Explorer"
        elif dwell > distance * 0.4:
            archetype = "Observer"
        elif gestures.get("open_palm", 0) > 3:
            archetype = "Connector"
        else:
            archetype = "Visitor"

        # ── Mood ────────────────────────────────────────
        if archetype == "Creator":
            mood = "Hope"
        elif archetype == "Explorer":
            mood = "Curiosity"
        elif archetype == "Observer":
            mood = "Calm"
        elif archetype == "Connector":
            mood = "Harmony"
        else:
            mood = "Calm"

        # ── Weather ─────────────────────────────────────
        if energy > 60:
            weather = "Aurora"
        elif energy > 40:
            weather = "Wind"
        elif organisms > 5:
            weather = "Aurora"
        else:
            weather = "Calm"

        # ── Lighting ────────────────────────────────────
        if mood in ("Hope", "Curiosity"):
            lighting = "Warm"
        elif mood == "Harmony":
            lighting = "Soft"
        else:
            lighting = "Neutral"

        # ── Organism strategy ───────────────────────────
        if archetype == "Creator":
            strategy = "Curious"
        elif archetype == "Explorer":
            strategy = "Observe"
        elif archetype == "Observer":
            strategy = "Approach"
        elif visits <= 2:
            strategy = "Curious"
        else:
            strategy = "Balanced"

        # ── Narrative ───────────────────────────────────
        if seeds >= 3:
            narrative = "The forest grew because you paused."
        elif organisms > 3:
            narrative = "Your silence shaped a living world."
        elif distance > 4000:
            narrative = "You stirred the invisible ocean."
        elif dwell > distance * 0.35:
            narrative = "The space remembers your stillness."
        elif visits > 5:
            narrative = "You have returned. The world noticed."
        else:
            narrative = "You were here. The world has changed."

        # ── Event ───────────────────────────────────────
        if archetype == "Creator" and seeds >= 2:
            event = "Bloom"
        elif archetype == "Explorer":
            event = "Gust"
        elif archetype == "Connector":
            event = "Aurora"
        else:
            event = "Calm"

        return {
            "user_archetype": archetype,
            "world_mood": mood,
            "weather": weather,
            "lighting": lighting,
            "organism_strategy": strategy,
            "narrative": narrative,
            "recommended_event": event,
        }

    def generate_narrative(self, context: dict) -> str:
        result = self.analyze_session(context)
        return result.get("narrative", "You were here. The world has changed.")

    def propose_evolution(self, context: dict) -> dict:
        visits = context.get("total_visits", 1)
        orgs = context.get("total_organisms", 0)
        archetype = context.get("dominant_archetype", "Visitor")

        if visits >= 10 and orgs < 3:
            return {"suggestion": "spawn_more_organisms",
                    "confidence": 0.8,
                    "reason": "Long-term visitor, few organisms"}
        elif archetype == "Creator" and orgs >= 5:
            return {"suggestion": "unlock_aurora_weather",
                    "confidence": 0.7,
                    "reason": "Creator archetype with thriving ecosystem"}
        elif archetype == "Explorer":
            return {"suggestion": "increase_fragment_spawn",
                    "confidence": 0.6,
                    "reason": "Explorer archetype — more to discover"}
        elif visits >= 5:
            return {"suggestion": "warm_lighting",
                    "confidence": 0.5,
                    "reason": "Returning visitor"}
        else:
            return {"suggestion": "maintain",
                    "confidence": 0.5,
                    "reason": "Default — no change needed"}
