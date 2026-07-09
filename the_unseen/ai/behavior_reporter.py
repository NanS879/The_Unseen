"""
V8 Behavior Analyzer — aggregates user behavior into structured reports.

Reads from: V3 BehaviorAnalyzer, GestureManager, AppState.
Outputs: JSON-compatible dict ready for AI consumption.

Unlike V3 BehaviorAnalyzer (which tracks raw stats), this module
produces processed summaries suitable for LLM context windows.
"""

from typing import Optional


class BehaviorReporter:
    """Aggregates session-level behavior data for AI analysis.

    Usage:
        reporter = BehaviorReporter()
        reporter.update_frame(gesture, speed, has_hands)  # each frame
        report = reporter.get_report(stats, organisms, energy)  # on demand
    """

    def __init__(self) -> None:
        # Gesture frequency counter (per session)
        self.gesture_counts: dict[str, int] = {}
        self.total_frames: int = 0
        self.frames_with_hands: int = 0
        self.frames_still: int = 0
        self.total_speed: float = 0.0
        self.peak_speed: float = 0.0

    def update_frame(self, active_gesture: str, max_speed: float,
                     has_hands: bool) -> None:
        """Record one frame of user activity.

        Args:
            active_gesture: Current gesture name (or "none").
            max_speed: Maximum hand speed this frame.
            has_hands: Whether hands are detected.
        """
        self.total_frames += 1
        if has_hands:
            self.frames_with_hands += 1
            self.total_speed += max_speed
            self.peak_speed = max(self.peak_speed, max_speed)
            if max_speed < 0.02:
                self.frames_still += 1
        if active_gesture != "none":
            self.gesture_counts[active_gesture] = (
                self.gesture_counts.get(active_gesture, 0) + 1)

    def get_report(
        self,
        v3_stats: dict,
        organism_count: int,
        energy: float,
        memory: Optional[dict] = None,
    ) -> dict:
        """Generate structured behavior report for AI.

        Args:
            v3_stats: Output of V3 BehaviorAnalyzer.get_stats().
            organism_count: Current number of living organisms.
            energy: Current energy level.
            memory: Optional world memory dict.

        Returns:
            Report dict in the format the AI expects.
        """
        # Normalize gesture counts to frequencies
        total_gesture_frames = max(1, sum(self.gesture_counts.values()))
        gesture_frequency = {
            g: round(c / total_gesture_frames, 3)
            for g, c in self.gesture_counts.items()
        }

        # Dominant gesture
        dominant = max(gesture_frequency, key=gesture_frequency.get) \
            if gesture_frequency else "none"

        # Activity ratio
        activity_ratio = self.frames_with_hands / max(1, self.total_frames)

        return {
            "user_behavior": {
                "session_duration_s": v3_stats.get("session_duration", 0),
                "total_distance_px": v3_stats.get("total_distance", 0),
                "avg_speed": v3_stats.get("avg_speed", 0),
                "peak_speed": round(self.peak_speed, 4),
                "activity_ratio": round(activity_ratio, 3),
                "still_ratio": round(
                    self.frames_still / max(1, self.frames_with_hands), 3),
                "total_dwell_time_s": v3_stats.get("total_dwell_time", 0),
                "seeds_planted": v3_stats.get("seed_count", 0),
                "interaction_count": v3_stats.get("interaction_count", 0),
                "gesture_frequency": gesture_frequency,
                "dominant_gesture": dominant,
            },
            "world_state": {
                "organism_count": organism_count,
                "energy": round(energy, 1),
                "weather": "Calm",  # filled by WorldBrain
                "exhibition_mode": "Interactive",
            },
            "organism_state": {
                "total_organisms": organism_count,
                "avg_energy": round(energy, 1),
            },
            "memory": memory or {},
        }
