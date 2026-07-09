"""
V8 Narrative Engine, Memory Curator, and Evolution Planner.

NarrativeEngine: Generates one poetic sentence per session.
MemoryCurator: Persists long-term visit history across sessions.
EvolutionPlanner: Proposes world changes based on history.

All read through WorldBrain. None directly control anything.
"""

import json
import os
import time
from typing import Optional

from ..world.world_state import W


# ============================================================
# Memory Curator
# ============================================================

class MemoryCurator:
    """Long-term visit memory persisted across all sessions.

    Stored as world_memory.json — separate from V3 organism state.
    Records: visit count, first visit, favorite ability, total stats.
    """

    FILE = "world_memory.json"

    def __init__(self) -> None:
        self._base_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        self._path = os.path.join(self._base_dir, self.FILE)
        self._data: dict = self._load()

    def _load(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "first_visit": time.time(),
                "total_visits": 0,
                "favorite_ability": "none",
                "ability_counts": {},
                "total_organisms_ever": 0,
                "peak_energy": 0.0,
                "longest_session_s": 0,
                "narrative_history": [],
            }

    def save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError:
            pass

    def record_visit(self) -> None:
        self._data["total_visits"] += 1

    def record_ability_use(self, ability: str) -> None:
        if ability != "none":
            self._data["ability_counts"][ability] = (
                self._data["ability_counts"].get(ability, 0) + 1)
            # Find favorite
            if self._data["ability_counts"]:
                self._data["favorite_ability"] = max(
                    self._data["ability_counts"],
                    key=self._data["ability_counts"].get)

    def record_session_end(self, stats: dict, narrative: str) -> None:
        """Record end-of-session stats."""
        duration = stats.get("session_duration", 0)
        if duration > self._data["longest_session_s"]:
            self._data["longest_session_s"] = duration
        if narrative:
            self._data["narrative_history"].append({
                "time": time.time(),
                "narrative": narrative,
            })
            # Keep only last 20
            if len(self._data["narrative_history"]) > 20:
                self._data["narrative_history"] = (
                    self._data["narrative_history"][-20:])

    def record_organism_count(self, count: int) -> None:
        if count > self._data["total_organisms_ever"]:
            self._data["total_organisms_ever"] = count

    def record_energy_peak(self, energy: float) -> None:
        if energy > self._data["peak_energy"]:
            self._data["peak_energy"] = energy

    def get_memory(self) -> dict:
        return dict(self._data)

    def last_narrative(self) -> Optional[str]:
        history = self._data.get("narrative_history", [])
        if history:
            return history[-1].get("narrative", "")
        return None

    def visit_count(self) -> int:
        return self._data.get("total_visits", 0)

    def days_since_first(self) -> int:
        first = self._data.get("first_visit", time.time())
        return int((time.time() - first) / 86400)


# ============================================================
# Narrative Engine
# ============================================================

class NarrativeEngine:
    """Generates one narrative sentence per session.

    If WorldBrain has an LLM, delegates to it. Otherwise
    uses a template system based on session archetype.
    """

    @staticmethod
    def generate(world_brain, stats: dict, organism_count: int,
                 energy: float, memory: dict) -> str:
        """Generate narrative for this session.

        Args:
            world_brain: WorldBrain instance.
            stats: V3 behavior stats.
            organism_count, energy: Current world state.
            memory: MemoryCurator.get_memory() dict.

        Returns:
            One poetic sentence.
        """
        # Try AI
        context = {
            "user_behavior": stats,
            "world_state": {"organism_count": organism_count,
                            "energy": energy},
            "memory": memory,
        }
        narrative = world_brain._llm.generate_narrative(context)

        # If AI returned generic, try to contextualize with visit count
        visits = memory.get("total_visits", 1)
        if visits > 5 and "first" not in narrative.lower():
            narrative = f"Visit {visits}. {narrative}"

        return narrative


# ============================================================
# Evolution Planner
# ============================================================

class EvolutionPlanner:
    """Proposes world changes based on AI analysis + history.

    Runs rarely (every few sessions). Proposals are stored
    and can be reviewed/approved before applying.
    """

    @staticmethod
    def propose(world_brain, memory_curator: MemoryCurator) -> Optional[dict]:
        """Get an evolution proposal. None if not needed yet."""
        memory = memory_curator.get_memory()
        context = {
            "total_visits": memory.get("total_visits", 1),
            "total_organisms": memory.get("total_organisms_ever", 0),
            "dominant_archetype": "Visitor",
            "world_age_days": memory_curator.days_since_first(),
        }

        # Only propose every 3+ visits
        if memory.get("total_visits", 0) % 3 != 0:
            return None

        return world_brain._llm.propose_evolution(context)

    @staticmethod
    def apply_proposal(proposal: dict) -> None:
        """Apply an approved evolution proposal to world state."""
        suggestion = proposal.get("suggestion", "")
        if suggestion == "spawn_more_organisms":
            # Increase fragment spawn rate
            from ..config import Config
            Config.INFLUENCE_RADIUS = min(400, Config.INFLUENCE_RADIUS + 20)
        elif suggestion == "unlock_aurora_weather":
            # Bias weather toward Aurora
            pass  # WeatherSystem already handles this
        elif suggestion == "increase_fragment_spawn":
            pass  # Fragment spawn is configurable
