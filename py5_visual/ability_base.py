"""
BaseAbility — abstract foundation for all Space Abilities.

Each ability has a state machine:
    IDLE → PREPARING → CHARGING → ACTIVATED → COOLDOWN → IDLE

Gestures trigger abilities. Abilities affect the space holistically
(not just one particle effect). This decouples gesture input from
visual output — new abilities can be added without touching gestures.

Design:
    Gesture → Intent → Space Ability → Space Mood → Visual Response
"""

import math
import time
from enum import Enum
from typing import Optional


# ── Space Mood ──────────────────────────────────────────

class SpaceMood(Enum):
    """Moods that abilities can evoke in the space.

    Mood affects: color temperature, flow speed, glow intensity,
    particle behavior, and (future) sound.
    """
    NEUTRAL   = "neutral"
    CALM      = "calm"
    FOCUSED   = "focused"
    HOPE      = "hope"
    CURIOSITY = "curiosity"
    FREEDOM   = "freedom"
    HARMONY   = "harmony"

    def flow_multiplier(self) -> float:
        return {
            "neutral": 1.0, "calm": 0.6, "focused": 1.4,
            "hope": 0.9, "curiosity": 1.2, "freedom": 0.5,
            "harmony": 0.8,
        }.get(self.value, 1.0)

    def glow_multiplier(self) -> float:
        return {
            "neutral": 1.0, "calm": 0.7, "focused": 1.3,
            "hope": 1.2, "curiosity": 0.9, "freedom": 0.6,
            "harmony": 1.1,
        }.get(self.value, 1.0)

    def color_shift(self) -> tuple[float, float, float]:
        """RGB multipliers for mood color influence."""
        return {
            "neutral":   (1.0, 1.0, 1.0),
            "calm":      (0.8, 0.9, 1.2),
            "focused":   (1.1, 0.9, 0.7),
            "hope":      (1.0, 1.1, 0.8),
            "curiosity": (0.9, 1.0, 1.1),
            "freedom":   (0.7, 1.0, 1.1),
            "harmony":   (1.0, 0.8, 1.1),
        }.get(self.value, (1.0, 1.0, 1.0))


# ── Ability States ──────────────────────────────────────

class AbilityState(Enum):
    IDLE       = "idle"
    PREPARING  = "preparing"
    CHARGING   = "charging"
    ACTIVATED  = "activated"
    COOLDOWN   = "cooldown"


# ── Base Ability ────────────────────────────────────────

class BaseAbility:
    """Abstract base for all space abilities.

    Subclasses must implement:
        _on_activate() → dict  — called when ability fires
        _visual_feedback(py5, progress) — per-frame rendering
        mood() → SpaceMood

    Lifecycle:
        1. start() called when gesture is first detected
        2. update(dt) called each frame — advances state machine
        3. _on_activate() called when charge completes
        4. State returns to IDLE after cooldown
    """

    def __init__(
        self,
        name: str,
        charge_time: float = 1.0,
        cooldown_time: float = 2.0,
    ) -> None:
        self.name = name
        self.charge_time = charge_time
        self.cooldown_time = cooldown_time

        self.state: AbilityState = AbilityState.IDLE
        self.charge_progress: float = 0.0   # 0→1
        self.cooldown_progress: float = 0.0 # 0→1
        self._state_timer: float = 0.0

        # Position where ability was triggered
        self.x: float = 0.0
        self.y: float = 0.0

    # ── Public API ───────────────────────────────────

    def start(self, x: float, y: float) -> None:
        """Begin the ability at a position. Called when gesture detected."""
        if self.state != AbilityState.IDLE:
            return  # Still in cooldown
        self.x = x
        self.y = y
        self.state = AbilityState.PREPARING
        self.charge_progress = 0.0
        self._state_timer = 0.0

    def update(self, dt: float, gesture_held: bool) -> Optional[dict]:
        """Advance state machine. Returns effect dict if activated.

        Args:
            dt: Time delta in seconds.
            gesture_held: Whether the triggering gesture is still active.

        Returns:
            Dict of effects if ability just activated, None otherwise.
        """
        if self.state == AbilityState.IDLE:
            return None

        if self.state == AbilityState.COOLDOWN:
            self._state_timer += dt
            self.cooldown_progress = min(1.0, self._state_timer / self.cooldown_time)
            if self._state_timer >= self.cooldown_time:
                self.state = AbilityState.IDLE
                self.charge_progress = 0.0
                self.cooldown_progress = 0.0
            return None

        if self.state == AbilityState.PREPARING:
            if gesture_held:
                self.state = AbilityState.CHARGING
                self._state_timer = 0.0
            else:
                # Gesture dropped before charging started
                self.state = AbilityState.IDLE
            return None

        if self.state == AbilityState.CHARGING:
            if not gesture_held:
                # Gesture released before charge complete — cancel
                self.state = AbilityState.IDLE
                self.charge_progress = 0.0
                return None

            self._state_timer += dt
            self.charge_progress = min(1.0, self._state_timer / self.charge_time)

            if self._state_timer >= self.charge_time:
                # Charge complete → activate
                self.state = AbilityState.ACTIVATED
                effects = self._on_activate()
                # Immediately enter cooldown
                self.state = AbilityState.COOLDOWN
                self._state_timer = 0.0
                self.cooldown_progress = 0.0
                return effects
            return None

        return None

    def cancel(self) -> None:
        """Cancel the ability, returning to IDLE."""
        self.state = AbilityState.IDLE
        self.charge_progress = 0.0

    # ── Subclass Interface ───────────────────────────

    def _on_activate(self) -> dict:
        """Called when ability fires. Override in subclasses.

        Returns:
            Dict with 'ability', 'mood', and ability-specific effects.
        """
        return {"ability": self.name, "mood": self.mood().value}

    def mood(self) -> SpaceMood:
        """The mood this ability evokes. Override in subclasses."""
        return SpaceMood.NEUTRAL

    def display_feedback(self, py5) -> None:
        """Render ability-specific visual feedback. Override in subclasses.

        Args:
            py5: The py5 sketch module.
        """
        # Draw charge ring
        if self.state == AbilityState.CHARGING:
            r = 30.0 + self.charge_progress * 50.0
            alpha = 60.0 * self.charge_progress
            py5.no_fill()
            py5.stroke(200, 200, 255, alpha)
            py5.stroke_weight(2.0 * self.charge_progress)
            py5.circle(self.x, self.y, r)

    @property
    def is_active(self) -> bool:
        return self.state not in (AbilityState.IDLE, AbilityState.COOLDOWN)
