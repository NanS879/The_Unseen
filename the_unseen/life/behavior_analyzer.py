"""
BehaviorAnalyzer — tracks cumulative user interaction statistics.

Records movement patterns, dwell behavior, and session metrics.
Data is used by the energy system, growth logic, and (future) AI.

Design:
    Pure data collection. Reads hand states, updates running stats.
    Serializable for persistence across sessions.
"""

import time
import math
from typing import Optional


class BehaviorAnalyzer:
    """Tracks user behavior across the entire session.

    Attributes:
        total_distance: Cumulative hand travel in normalized units.
        avg_speed: Running average of hand speed.
        total_dwell_time: Seconds where hand speed < threshold.
        total_active_time: Seconds with hands present.
        total_idle_time: Seconds with no hands.
        seed_count: Total seeds created this session.
        interaction_count: Times hand entered the space.
        session_start: Unix timestamp of session start.
        last_hand_positions: For distance tracking per hand.
    """

    def __init__(
        self,
        dwell_threshold: float = 0.01,
        session_start: Optional[float] = None,
    ) -> None:
        """Initialize the behavior analyzer.

        Args:
            dwell_threshold: Speed below which hand is "dwelling".
            session_start: Timestamp (auto if None).
        """
        self.dwell_threshold = dwell_threshold

        # Cumulative stats
        self.total_distance: float = 0.0
        self.total_dwell_time: float = 0.0
        self.total_active_time: float = 0.0
        self.total_idle_time: float = 0.0
        self.seed_count: int = 0
        self.interaction_count: int = 0

        # Running averages
        self.avg_speed: float = 0.0
        self._speed_samples: int = 0

        # Session
        self.session_start = session_start if session_start else time.time()

        # Internal tracking
        self._last_positions: dict[str, tuple[float, float] | None] = {
            "left": None,
            "right": None,
        }
        self._was_active: bool = False

    def update(
        self,
        dt: float,
        has_hands: bool,
        hand_data: list[dict],
    ) -> None:
        """Update behavior stats for one frame.

        Args:
            dt: Time delta in seconds.
            has_hands: Whether any hand is detected.
            hand_data: List of dicts with 'side', 'px', 'py', 'speed'.
        """
        if has_hands:
            self.total_active_time += dt

            # Track interaction start
            if not self._was_active:
                self.interaction_count += 1
                self._was_active = True

            # Per-hand distance tracking
            for h in hand_data:
                side = h.get("side", "unknown")
                px, py = h.get("px", 0.0), h.get("py", 0.0)
                speed = h.get("speed", 0.0)

                # Distance traveled
                prev = self._last_positions.get(side)
                if prev is not None:
                    dx = px - prev[0]
                    dy = py - prev[1]
                    self.total_distance += math.sqrt(dx * dx + dy * dy)

                self._last_positions[side] = (px, py)

                # Running average speed
                self._speed_samples += 1
                self.avg_speed += (speed - self.avg_speed) / max(1, self._speed_samples)

                # Dwell tracking
                if speed < self.dwell_threshold:
                    self.total_dwell_time += dt
        else:
            self.total_idle_time += dt
            self._was_active = False

    def on_seed_created(self) -> None:
        """Notify that a new seed was created."""
        self.seed_count += 1

    def get_stats(self) -> dict:
        """Return current statistics as a dict."""
        session_duration = time.time() - self.session_start
        return {
            "total_distance": round(self.total_distance, 4),
            "avg_speed": round(self.avg_speed, 6),
            "total_dwell_time": round(self.total_dwell_time, 2),
            "total_active_time": round(self.total_active_time, 2),
            "total_idle_time": round(self.total_idle_time, 2),
            "seed_count": self.seed_count,
            "interaction_count": self.interaction_count,
            "session_duration": round(session_duration, 1),
        }

    def serialize(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "total_distance": self.total_distance,
            "avg_speed": self.avg_speed,
            "speed_samples": self._speed_samples,
            "total_dwell_time": self.total_dwell_time,
            "total_active_time": self.total_active_time,
            "total_idle_time": self.total_idle_time,
            "seed_count": self.seed_count,
            "interaction_count": self.interaction_count,
            "session_start": self.session_start,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "BehaviorAnalyzer":
        """Create from serialized dict."""
        ba = cls(
            session_start=data.get("session_start", time.time()),
        )
        ba.total_distance = data.get("total_distance", 0.0)
        ba.avg_speed = data.get("avg_speed", 0.0)
        ba._speed_samples = data.get("speed_samples", 0)
        ba.total_dwell_time = data.get("total_dwell_time", 0.0)
        ba.total_active_time = data.get("total_active_time", 0.0)
        ba.total_idle_time = data.get("total_idle_time", 0.0)
        ba.seed_count = data.get("seed_count", 0)
        ba.interaction_count = data.get("interaction_count", 0)
        return ba
