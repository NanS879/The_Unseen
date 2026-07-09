"""
TimeSystem — day/night cycle for the digital ecosystem.

A continuous sine-wave cycle modulates:
    - Flow field speed (faster at noon, slower at midnight)
    - Glow intensity (brighter at night)
    - Color temperature (warmer at noon, cooler at night)
    - Growth rate (faster at dawn/dusk transitions)

The cycle gives the space a "breathing" rhythm independent of
user interaction.

Design:
    Simple sine oscillator. Phase 0 = dawn, 0.25 = noon, 0.5 = dusk, 0.75 = midnight.
"""

import math
import time

from config import Config


class TimeSystem:
    """Day/night cycle oscillator.

    Attributes:
        cycle_duration: Seconds for one full cycle.
        phase: Current phase 0.0–1.0 (0=dawn, 0.25=noon, 0.5=dusk, 0.75=midnight).
        elapsed: Total elapsed seconds.
    """

    def __init__(
        self,
        cycle_duration: float = Config.TIME_CYCLE_SECONDS,
        initial_elapsed: float = 0.0,
    ) -> None:
        """Initialize the time system.

        Args:
            cycle_duration: Seconds per full day/night cycle.
            initial_elapsed: Starting elapsed time (for deserialization).
        """
        self.cycle_duration = cycle_duration
        self.elapsed = initial_elapsed
        self._start_time = time.time()

    def update(self, dt: float) -> None:
        """Advance the cycle by dt seconds."""
        self.elapsed += dt

    @property
    def phase(self) -> float:
        """Current phase 0.0–1.0."""
        return (self.elapsed % self.cycle_duration) / self.cycle_duration

    @property
    def day_factor(self) -> float:
        """0.0 (midnight) → 1.0 (noon) based on sine wave."""
        # sin(phase × 2π): 0 at dawn, 1 at noon, 0 at dusk, -1 at midnight
        raw = math.sin(self.phase * math.pi * 2.0)
        return (raw + 1.0) / 2.0  # Map [-1,1] → [0,1]

    @property
    def dawn_dusk_factor(self) -> float:
        """Peaks at dawn (phase=0) and dusk (phase=0.5), zero at noon/midnight."""
        raw = math.cos(self.phase * math.pi * 2.0)
        return abs(raw)  # 1 at dawn/dusk, 0 at noon/midnight

    def get_modulators(self) -> dict[str, float]:
        """Return system modulation factors based on time of day.

        Returns:
            Dict with keys:
                flow: Flow field strength multiplier (0.7–1.3)
                glow: Glow intensity (0.5–1.5, brightest at night)
                growth: Growth speed (0.5–1.5, fastest at dawn/dusk)
                warmth: Color warmth (0.0=cool/night, 1.0=warm/noon)
        """
        df = self.day_factor
        dd = self.dawn_dusk_factor

        return {
            "flow": 0.7 + df * 0.6,           # 0.7–1.3
            "glow": 1.3 - df * 0.6,           # 1.3→0.7 (brighter at night)
            "growth": 0.6 + dd * 0.8,         # peaks at dawn/dusk
            "warmth": df,                      # 0=cool blue night, 1=warm noon
        }

    def get_phase_name(self) -> str:
        """Human-readable phase name."""
        p = self.phase
        if p < 0.125:
            return "dawn"
        if p < 0.375:
            return "day"
        if p < 0.625:
            return "dusk"
        return "night"

    def serialize(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "elapsed": self.elapsed,
            "cycle_duration": self.cycle_duration,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "TimeSystem":
        """Create from serialized dict."""
        return cls(
            cycle_duration=data.get("cycle_duration", Config.TIME_CYCLE_SECONDS),
            initial_elapsed=data.get("elapsed", 0.0),
        )
