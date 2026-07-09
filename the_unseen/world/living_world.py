"""
V7 Living World — Ecosystem, Weather, Memory, Exhibition.

Combined module for the four world-layer systems.
Each is a thin manager that reads/writes through WorldState singleton.
"""

import math
import random
import time
from typing import Optional

from ..config import Config
from .world_state import WorldState, WeatherType, ExhibitionMode, W


# ============================================================
# Ecosystem — inter-organism rules
# ============================================================

class EcosystemManager:
    """Manages inter-organism interactions: distance, grouping, energy.

    Operates on WorldState.autonomous_organisms directly.
    """

    NEAR_DIST = 120.0      # px — "close"
    FAR_DIST = 300.0      # px — "far"
    SWARM_DIST = 200.0    # px — grouping threshold

    @staticmethod
    def update(dt: float) -> None:
        """Apply ecosystem rules to all autonomous organisms."""
        orgs = W.autonomous_organisms
        n = len(orgs)
        if n < 2:
            return

        for i, a in enumerate(orgs):
            for j, b in enumerate(orgs):
                if i >= j:
                    continue
                dx = a.x - b.x
                dy = a.y - b.y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 0.01:
                    continue

                # Too close → slight repulsion + energy exchange
                if dist < EcosystemManager.NEAR_DIST:
                    force = (1.0 - dist / EcosystemManager.NEAR_DIST) * 0.15
                    a.vx += (dx / dist) * force
                    a.vy += (dy / dist) * force
                    b.vx -= (dx / dist) * force
                    b.vy -= (dy / dist) * force
                    # Share energy
                    if a.energy > b.energy:
                        transfer = (a.energy - b.energy) * 0.001
                        a.energy -= transfer
                        b.energy += transfer

                # Moderate distance → slight attraction (swarm)
                elif dist < EcosystemManager.SWARM_DIST:
                    force = (dist / EcosystemManager.SWARM_DIST) * 0.03
                    a.vx -= (dx / dist) * force
                    a.vy -= (dy / dist) * force
                    b.vx += (dx / dist) * force
                    b.vy += (dy / dist) * force

                # Update perception of nearest organism
                if dist < a.perception.nearest_organism_dist:
                    a.perception.nearest_organism_dist = dist
                    a.perception.nearest_organism = b
                    a.perception.neighbor_count = n - 1
                if dist < b.perception.nearest_organism_dist:
                    b.perception.nearest_organism_dist = dist
                    b.perception.nearest_organism = a
                    b.perception.neighbor_count = n - 1

    @staticmethod
    def swarm_center() -> Optional[tuple[float, float]]:
        """Compute the centroid of all organisms (swarm center)."""
        orgs = W.autonomous_organisms
        if not orgs:
            return None
        cx = sum(a.x for a in orgs) / len(orgs)
        cy = sum(a.y for a in orgs) / len(orgs)
        return (cx, cy)


# ============================================================
# Space Weather
# ============================================================

class WeatherSystem:
    """Space weather that evolves over time and responds to user activity.

    Weather affects: flow speed, color shift, organism behavior multiplier.

    Transition: CALM ⇄ WIND ⇄ STORM (plus AURORA at high energy).
    """

    # How each weather type modulates the world
    MODIFIERS = {
        WeatherType.CALM:   {"flow": 0.7,  "glow": 0.8,  "organism_speed": 0.6,
                             "color_shift": (0.85, 0.90, 1.05)},
        WeatherType.WIND:   {"flow": 1.3,  "glow": 1.0,  "organism_speed": 1.0,
                             "color_shift": (0.95, 1.0, 1.1)},
        WeatherType.STORM:  {"flow": 1.8,  "glow": 1.4,  "organism_speed": 1.5,
                             "color_shift": (1.1, 1.0, 0.85)},
        WeatherType.AURORA: {"flow": 1.1,  "glow": 1.3,  "organism_speed": 1.3,
                             "color_shift": (0.8, 0.85, 1.2)},
    }

    @staticmethod
    def update(dt: float) -> None:
        """Evolve weather over time. Influenced by energy and organisms."""
        W.weather_duration += dt

        # Natural cycle: change every 20-40 seconds
        cycle_duration = 20.0 + random.uniform(-5, 5) * (1.0 + W.organism_count() * 0.05)

        if W.weather_duration > cycle_duration:
            W.weather_duration = 0.0
            # Weight random choice by world state
            if W.space_energy > 70 and random.random() < 0.3:
                W.weather = WeatherType.AURORA
            elif W.space_energy > 50 and W.space_state == "EXCITED":
                W.weather = WeatherType.STORM
            elif W.space_state == "ACTIVE":
                W.weather = WeatherType.WIND
            else:
                W.weather = WeatherType.CALM

    @staticmethod
    def get_modifiers() -> dict:
        """Return current weather modifiers."""
        return WeatherSystem.MODIFIERS.get(W.weather,
                WeatherSystem.MODIFIERS[WeatherType.CALM])

    @staticmethod
    def get_color_shift() -> tuple[float, float, float]:
        return WeatherSystem.get_modifiers()["color_shift"]


# ============================================================
# World Memory — long-term persistence
# ============================================================

class WorldMemory:
    """Persists world-level stats across sessions.

    Stored alongside V3 organism data in the_unseen_state.json.
    """

    KEY = "world_memory"

    @staticmethod
    def serialize() -> dict:
        W.memory["total_visits"] = W.total_visits
        W.memory["total_organisms"] = W.total_organisms_created
        W.memory["total_energy"] = W.total_energy_collected
        W.memory["world_age"] = W.world_age
        return W.memory

    @staticmethod
    def deserialize(data: dict) -> None:
        W.load_memory(data)
        W.total_visits += 1  # increment visit count on load
        W.world_age = data.get("world_age", 0.0) + (
            time.time() - W.session_start) if data else 0.0

    @staticmethod
    def get_age_string() -> str:
        """Human-readable world age."""
        seconds = int(W.world_age)
        if seconds < 60:
            return f"{seconds}s"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m"
        hours = minutes // 60
        return f"{hours}h {minutes % 60}m"


# ============================================================
# Exhibition Mode
# ============================================================

class ExhibitionController:
    """Manages exhibition lifecycle: IDLE → ATTRACT → INTERACTIVE → FAREWELL."""

    ATTRACT_TIMEOUT = 8.0     # seconds of no hand before ATTRACT
    FAREWELL_TIMEOUT = 15.0   # seconds before FAREWELL starts
    FAREWELL_DURATION = 4.0   # seconds of ending animation

    @staticmethod
    def update(dt: float, has_hands: bool) -> None:
        """Update exhibition state based on user presence."""
        W.exhibition_timer += dt

        if has_hands:
            W.exhibition_timer = 0.0
            if W.exhibition != ExhibitionMode.INTERACTIVE:
                W.exhibition = ExhibitionMode.INTERACTIVE
        else:
            if W.exhibition == ExhibitionMode.INTERACTIVE:
                if W.exhibition_timer > ExhibitionController.ATTRACT_TIMEOUT:
                    W.exhibition = ExhibitionMode.ATTRACT
            elif W.exhibition == ExhibitionMode.ATTRACT:
                if W.exhibition_timer > ExhibitionController.FAREWELL_TIMEOUT:
                    W.exhibition = ExhibitionMode.FAREWELL
            elif W.exhibition == ExhibitionMode.FAREWELL:
                if W.exhibition_timer > ExhibitionController.FAREWELL_DURATION:
                    W.exhibition = ExhibitionMode.IDLE

    @staticmethod
    def get_ambient_modifier() -> float:
        """Visual intensity multiplier for current mode."""
        return {
            ExhibitionMode.IDLE: 0.3,
            ExhibitionMode.ATTRACT: 0.7,
            ExhibitionMode.INTERACTIVE: 1.0,
            ExhibitionMode.FAREWELL: 0.4,
        }.get(W.exhibition, 1.0)
