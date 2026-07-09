"""
Perception system for autonomous organisms.

Each organism senses the world through a Perception instance.
These are lightweight objects updated each frame from WorldState.

Design: organisms NEVER access MediaPipe or Camera directly.
All sensory data comes through WorldState → Perception.
"""

import math
from typing import Optional


class Perception:
    """Sensory snapshot for a single organism at a given position.

    Reads from WorldState singleton — no direct hardware access.
    """

    def __init__(self) -> None:
        # Distances to nearest hand
        self.nearest_hand_dist: float = 9999.0
        self.nearest_hand_speed: float = 0.0
        self.nearest_hand_x: float = 0.0
        self.nearest_hand_y: float = 0.0
        self.hand_count: int = 0

        # Current user gesture
        self.active_gesture: str = "none"

        # World state
        self.space_energy: float = 30.0
        self.space_state: str = "IDLE"
        self.time_phase: str = "dawn"

        # Neighbor organisms
        self.nearest_organism_dist: float = 9999.0
        self.nearest_organism: object | None = None
        self.neighbor_count: int = 0

    def update(self, org_x: float, org_y: float,
               world_state) -> None:
        """Refresh perception from world state for this position.

        Args:
            org_x, org_y: This organism's position.
            world_state: WorldState singleton instance.
        """
        # ── Hand detection ──────────────────────────────
        self.hand_count = len(world_state.hand_positions)
        self.nearest_hand_dist = 9999.0
        self.nearest_hand_speed = 0.0

        for i, (hx, hy) in enumerate(world_state.hand_positions):
            dx = org_x - hx
            dy = org_y - hy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist < self.nearest_hand_dist:
                self.nearest_hand_dist = dist
                self.nearest_hand_x = hx
                self.nearest_hand_y = hy
                if i < len(world_state.hand_speeds):
                    self.nearest_hand_speed = world_state.hand_speeds[i]

        # ── World state ─────────────────────────────────
        self.active_gesture = world_state.active_gesture
        self.space_energy = world_state.space_energy
        self.space_state = world_state.space_state
        self.time_phase = world_state.time_phase

    def hand_present(self) -> bool:
        return self.hand_count > 0 and self.nearest_hand_dist < 1500.0

    def hand_is_near(self, radius: float = 300.0) -> bool:
        return self.nearest_hand_dist < radius

    def hand_is_still(self) -> bool:
        return self.nearest_hand_speed < 0.03 and self.hand_present()

    def hand_is_fast(self) -> bool:
        return self.nearest_hand_speed > 0.08
