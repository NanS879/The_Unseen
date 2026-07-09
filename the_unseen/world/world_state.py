"""
WorldState — global singleton for the digital ecosystem.

Tracks all autonomous organisms, world-level metrics,
space weather, and exhibition mode. All world subsystems
read/write through this state.

Purpose: decouple organisms from rendering, gestures,
and camera — organisms perceive via WorldState, not MediaPipe.
"""

import time
from enum import Enum
from typing import Optional


class WeatherType(Enum):
    CALM  = "calm"    # stable flow, soft colors
    WIND  = "wind"    # faster flow, active particles
    STORM = "storm"   # chaotic flow, intense lighting
    AURORA = "aurora" # rich colors, organisms most active


class ExhibitionMode(Enum):
    IDLE        = "idle"        # no user — world auto-evolves
    ATTRACT     = "attract"     # user detected — build up visuals
    INTERACTIVE = "interactive" # full interaction
    FAREWELL    = "farewell"    # user leaving — ending animation


class WorldState:
    """Singleton world state. All subsystems share this object.

    Created once at module import. Imported by organism AI,
    ecosystem, weather, exhibition, and __main__.py.
    """

    def __init__(self) -> None:
        # ── Autonomous organisms ────────────────────────
        self.autonomous_organisms: list = []  # OrganismAI instances

        # ── World metrics ───────────────────────────────
        self.total_visits: int = 0
        self.total_organisms_created: int = 0
        self.total_energy_collected: float = 0.0
        self.world_age: float = 0.0           # seconds since first session
        self.session_start: float = time.time()

        # ── Current perception data (updated by __main__.py each frame) ──
        self.hand_positions: list[tuple[float, float]] = []
        self.hand_speeds: list[float] = []
        self.active_gesture: str = "none"
        self.space_energy: float = 30.0
        self.space_state: str = "IDLE"
        self.time_phase: str = "dawn"

        # ── Weather ─────────────────────────────────────
        self.weather: WeatherType = WeatherType.CALM
        self.weather_transition: float = 0.0
        self.weather_duration: float = 0.0
        self.weather_locked: bool = False  # brain has set weather → don't cycle

        # ── Exhibition ──────────────────────────────────
        self.exhibition: ExhibitionMode = ExhibitionMode.INTERACTIVE
        self.exhibition_timer: float = 0.0

        # ── World memory (persisted) ────────────────────
        self.memory: dict = {
            "total_visits": 0,
            "total_organisms": 0,
            "total_energy": 0.0,
            "world_age": 0.0,
            "weather_history": [],
        }

    def register_organism(self, org) -> None:
        """Register a new autonomous organism."""
        self.autonomous_organisms.append(org)
        self.total_organisms_created += 1

    def unregister_organism(self, org) -> None:
        """Remove an organism from the world."""
        if org in self.autonomous_organisms:
            self.autonomous_organisms.remove(org)

    def update_perception(self, hands, speeds, gesture, energy,
                          space_state, time_phase) -> None:
        """Update the world snapshot that organisms perceive.

        Called once per frame by __main__.py.
        """
        self.hand_positions = hands
        self.hand_speeds = speeds
        self.active_gesture = gesture
        self.space_energy = energy
        self.space_state = space_state
        self.time_phase = time_phase

    def organism_count(self) -> int:
        return len(self.autonomous_organisms)

    def serialize_memory(self) -> dict:
        return {
            "total_visits": self.total_visits,
            "total_organisms": self.total_organisms_created,
            "total_energy": self.total_energy_collected,
            "world_age": self.world_age,
        }

    def load_memory(self, data: dict) -> None:
        self.total_visits = data.get("total_visits", 0)
        self.total_organisms_created = data.get("total_organisms", 0)
        self.total_energy_collected = data.get("total_energy", 0.0)
        self.world_age = data.get("world_age", 0.0)


# ── Module-level singleton ────────────────────────────
W = WorldState()
