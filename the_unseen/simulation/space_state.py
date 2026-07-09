"""
Space state machine for tracking the environment's "mood."

The space transitions through four states based on hand presence and speed:

    IDLE ──(hand detected)──→ ACTIVE ──(fast movement)──→ EXCITED
      ↑                          ↑                            │
      │                          │                            │
      └──(timeout)── CALM ←──(slow down)─────────────────────┘

Each state outputs multipliers that modulate:
- Flow field speed
- Influence strength
- Trail visibility
- Background fade alpha

V2: Encapsulated state machine, easy to extend with new states.
"""

import time
from typing import Optional

from ..config import Config


class SpaceState:
    """State machine for the space's responsive "mood."

    States: IDLE, ACTIVE, EXCITED, CALM

    Public interface:
        update(has_hands, max_speed)  — evaluate transitions
        state → str                     — current state name
        flow_multiplier → float         — flow field speed multiplier
        influence_multiplier → float    — influence strength multiplier
        trail_alpha → int               — background fade alpha
        time_in_state → float           — seconds in current state
    """

    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    EXCITED = "EXCITED"
    CALM = "CALM"

    def __init__(
        self,
        excited_speed: float = Config.STATE_EXCITED_SPEED,
        calm_speed: float = Config.STATE_CALM_SPEED,
        excited_frames: int = Config.STATE_EXCITED_FRAMES,
        calm_frames: int = Config.STATE_CALM_FRAMES,
        hand_timeout: float = Config.STATE_HAND_TIMEOUT,
    ) -> None:
        """Initialize the state machine in IDLE.

        Args:
            excited_speed: Speed threshold to enter EXCITED.
            calm_speed: Speed threshold to enter CALM from EXCITED.
            excited_frames: Consecutive frames above threshold for ACTIVE→EXCITED.
            calm_frames: Consecutive frames below threshold for EXCITED→CALM.
            hand_timeout: Seconds without hand before returning to IDLE.
        """
        self._state: str = self.IDLE
        self._state_start: float = time.monotonic()

        # Transition parameters
        self._excited_speed = excited_speed
        self._calm_speed = calm_speed
        self._excited_frames = excited_frames
        self._calm_frames = calm_frames
        self._hand_timeout = hand_timeout

        # Hand tracking
        self._hand_present: bool = False
        self._max_speed: float = 0.0
        self._last_hand_time: float = 0.0

        # Consecutive frame counters for transition hysteresis
        self._fast_frames: int = 0
        self._slow_frames: int = 0

    # ============================================================
    # Update
    # ============================================================

    def update(
        self,
        has_hands: bool,
        max_speed: float,
        now: Optional[float] = None,
    ) -> None:
        """Evaluate state transitions for this frame.

        Call once per frame with the latest hand data.

        Args:
            has_hands: Whether any hand is currently detected.
            max_speed: Maximum speed across all detected hands.
            now: Current monotonic time (auto if None).
        """
        if now is None:
            now = time.monotonic()

        self._hand_present = has_hands
        self._max_speed = max_speed

        if has_hands:
            self._last_hand_time = now

        # ---- State transitions ----
        prev = self._state

        if self._state == self.IDLE:
            self._update_idle(now)
        elif self._state == self.ACTIVE:
            self._update_active(now)
        elif self._state == self.EXCITED:
            self._update_excited(now)
        elif self._state == self.CALM:
            self._update_calm(now)

        if self._state != prev:
            self._state_start = now

    def _update_idle(self, now: float) -> None:
        """IDLE → ACTIVE when hand detected."""
        if self._hand_present:
            self._state = self.ACTIVE

    def _update_active(self, now: float) -> None:
        """ACTIVE → EXCITED (fast) or ACTIVE → IDLE (loss)."""
        if not self._hand_present:
            if now - self._last_hand_time > self._hand_timeout:
                self._state = self.IDLE
            return

        # Count frames above excited threshold
        if self._max_speed > self._excited_speed:
            self._fast_frames += 1
            if self._fast_frames >= self._excited_frames:
                self._state = self.EXCITED
                self._fast_frames = 0
        else:
            self._fast_frames = 0

    def _update_excited(self, now: float) -> None:
        """EXCITED → CALM when speed drops, or EXCITED → IDLE when lost."""
        if not self._hand_present:
            if now - self._last_hand_time > self._hand_timeout:
                self._state = self.IDLE
            return

        if self._max_speed < self._calm_speed:
            self._slow_frames += 1
            if self._slow_frames >= self._calm_frames:
                self._state = self.CALM
                self._slow_frames = 0
        else:
            self._slow_frames = 0

    def _update_calm(self, now: float) -> None:
        """CALM → ACTIVE (speed rises) or CALM → IDLE (loss)."""
        if not self._hand_present:
            if now - self._last_hand_time > self._hand_timeout:
                self._state = self.IDLE
            return

        if self._max_speed > self._calm_speed:
            self._state = self.ACTIVE

    # ============================================================
    # Properties
    # ============================================================

    @property
    def state(self) -> str:
        """Current state name."""
        return self._state

    @property
    def flow_multiplier(self) -> float:
        """Flow field speed multiplier for current state."""
        return Config.STATE_FLOW_SPEED.get(self._state, 1.0)

    @property
    def influence_multiplier(self) -> float:
        """Influence strength multiplier for current state."""
        return Config.STATE_INFLUENCE_MULT.get(self._state, 1.0)

    @property
    def trail_alpha(self) -> int:
        """Background fade alpha for current state."""
        mapping = {
            self.IDLE: Config.FADE_ALPHA_IDLE,
            self.ACTIVE: Config.FADE_ALPHA_ACTIVE,
            self.EXCITED: Config.FADE_ALPHA_EXCITED,
            self.CALM: Config.FADE_ALPHA_ACTIVE,
        }
        return mapping.get(self._state, Config.FADE_ALPHA_IDLE)
