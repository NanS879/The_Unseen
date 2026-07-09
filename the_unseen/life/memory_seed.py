"""
MemorySeed — the smallest unit of digital life.

A seed is planted when a user's hand dwells in one area.
It records the moment, accumulates energy, and waits to grow.

Design:
    Pure data + display. Growth logic lives in Organism.
    Serializable for persistence across sessions.
"""

import math
import time
from typing import Optional

from ..config import Config


class MemorySeed:
    """A memory anchor planted by sustained hand presence.

    Lifecycle:
        dormant → accumulating energy → ready to grow → organism

    Attributes:
        x, y: Seed position in pixel space.
        created_at: Unix timestamp of creation.
        dwell_time: Total seconds hand has stayed near this seed.
        energy: 0.0–SEED_MAX_ENERGY. Accumulates while hand stays.
        grown: True when energy reaches threshold and organism is spawned.
    """

    def __init__(
        self,
        x: float,
        y: float,
        speed: float = 0.0,
        created_at: Optional[float] = None,
        dwell_time: float = 0.0,
        energy: float = 0.0,
        grown: bool = False,
    ) -> None:
        """Create a new memory seed.

        Args:
            x, y: Seed position in pixels.
            speed: Hand speed at creation time.
            created_at: Timestamp (auto if None).
            dwell_time: Initial dwell time (for deserialization).
            energy: Initial energy (for deserialization).
            grown: Whether already grown into organism.
        """
        self.x = x
        self.y = y
        self.speed_at_creation = speed
        self.created_at = created_at if created_at is not None else time.time()
        self.dwell_time = dwell_time
        self.energy = energy
        self.grown = grown

        # Display pulse animation
        self._pulse_phase = (x * 0.01 + y * 0.01) % 1.0  # Vary per seed

    # ============================================================
    # Update
    # ============================================================

    def update(
        self,
        dt: float,
        hand_near: bool,
        hand_speed: float = 0.0,
    ) -> None:
        """Update seed state for one frame.

        When hand is near: accumulate dwell time and energy.
        When hand is absent: dwell time stops, energy slowly decays.

        Args:
            dt: Time delta in seconds.
            hand_near: Whether a hand is within SEED_DWELL_RADIUS.
            hand_speed: Current hand speed (for energy rate modulation).
        """
        if self.grown:
            return

        if hand_near:
            self.dwell_time += dt
            # Energy gain: faster when hand is more still
            stillness = max(0.0, 1.0 - hand_speed / 0.05)
            gain = Config.SEED_ENERGY_RATE * stillness * dt
            self.energy = min(Config.SEED_MAX_ENERGY, self.energy + gain)
        else:
            # Slow decay when hand leaves
            self.energy = max(0.0, self.energy - Config.SEED_ENERGY_DECAY * dt)

    def is_ready(self) -> bool:
        """Check if seed has enough energy to grow into an organism."""
        return (
            not self.grown
            and self.energy >= Config.SEED_GROWTH_THRESHOLD
            and self.dwell_time >= Config.SEED_DWELL_TIME
        )

    def mark_grown(self) -> None:
        """Mark this seed as having spawned an organism."""
        self.grown = True

    # ============================================================
    # Display
    # ============================================================

    def display(self, py5) -> None:
        """Render the seed as a glowing pulsing orb.

        Brightness and size scale with energy level.
        Ready seeds have a bright pulsing ring.
        """
        if self.grown and self.energy < 5.0:
            return

        pulse = 0.5 + 0.5 * math.sin(
            py5.frame_count * 0.06 + self._pulse_phase
        )
        energy_ratio = self.energy / max(1.0, Config.SEED_MAX_ENERGY)

        # Outer glow
        size = 6.0 + energy_ratio * 12.0 * pulse
        if self.is_ready() and not self.grown:
            # Ready — bright purple pulse
            py5.no_stroke()
            py5.fill(180, 140, 255, 70.0 * pulse)
            py5.circle(self.x, self.y, size * 2.5)
            py5.fill(200, 170, 255, 120.0 * pulse)
            py5.circle(self.x, self.y, size * 1.5)
        elif self.grown:
            py5.fill(80, 60, 180, 30.0 * pulse)
            py5.circle(self.x, self.y, size * 1.5)
        else:
            # Accumulating — subtle blue
            py5.fill(100, 130, 220, 40.0 + 30.0 * energy_ratio * pulse)
            py5.circle(self.x, self.y, size * 2.0)

        # Core
        core_size = 3.0 + energy_ratio * 5.0 * pulse
        if self.is_ready():
            py5.fill(220, 200, 255, 200.0 * pulse)
        elif self.grown:
            py5.fill(120, 100, 200, 100.0 * pulse)
        else:
            py5.fill(150, 150, 230, 120.0 + 60.0 * energy_ratio * pulse)
        py5.no_stroke()
        py5.circle(self.x, self.y, core_size)

        # Ring for ready seeds
        if self.is_ready() and not self.grown:
            py5.no_fill()
            py5.stroke(200, 170, 255, 100.0 * pulse)
            py5.stroke_weight(1.5)
            py5.circle(self.x, self.y, size + 8.0)

    # ============================================================
    # Serialization
    # ============================================================

    def serialize(self) -> dict:
        """Convert seed to JSON-serializable dict."""
        return {
            "x": self.x,
            "y": self.y,
            "speed_at_creation": self.speed_at_creation,
            "created_at": self.created_at,
            "dwell_time": self.dwell_time,
            "energy": self.energy,
            "grown": self.grown,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "MemorySeed":
        """Create a MemorySeed from serialized dict."""
        return cls(
            x=data["x"],
            y=data["y"],
            speed=data.get("speed_at_creation", 0.0),
            created_at=data.get("created_at", time.time()),
            dwell_time=data.get("dwell_time", 0.0),
            energy=data.get("energy", 0.0),
            grown=data.get("grown", False),
        )

    def __repr__(self) -> str:
        return (
            f"MemorySeed(x={self.x:.0f}, y={self.y:.0f}, "
            f"energy={self.energy:.1f}, grown={self.grown})"
        )
