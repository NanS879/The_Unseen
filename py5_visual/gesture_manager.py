"""
Gesture recognition and state management for MediaPipe hands.

Detects: open_palm, fist, pinch, point, victory, swipe, hold.
Two-hand: expand, compress, cross, sync.

Architecture:
    GestureRecognizer — raw landmarks → gesture type + confidence
    GestureState — per-gesture state machine (idle→holding→cooldown)
    GestureManager — coordinates both hands + two-hand interactions

All thresholds configurable. Easy to add new gestures.
"""

import math
import time
from typing import Optional

from config import Config


# ── MediaPipe Landmark Indices ──────────────────────────
WRIST = 0
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_TIP = 12
RING_MCP = 13
RING_TIP = 16
PINKY_MCP = 17
PINKY_TIP = 20

FINGER_TIPS = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
FINGER_MCPS = [INDEX_MCP, MIDDLE_MCP, RING_MCP, PINKY_MCP]

# ── Gesture Types ───────────────────────────────────────
GESTURE_NONE       = "none"
GESTURE_OPEN_PALM  = "open_palm"
GESTURE_FIST       = "fist"
GESTURE_PINCH      = "pinch"
GESTURE_POINT      = "point"
GESTURE_VICTORY    = "victory"
GESTURE_SWIPE      = "swipe"
GESTURE_HOLD       = "hold"

TWO_HAND_EXPAND    = "two_expand"
TWO_HAND_COMPRESS  = "two_compress"
TWO_HAND_CROSS     = "two_cross"
TWO_HAND_SYNC      = "two_sync"


# ── Detection Thresholds ────────────────────────────────
class GestureConfig:
    """Tunable thresholds for gesture detection."""
    EXTENDED_RATIO = 0.50       # tip-to-MCP / MCP-to-wrist ratio for "extended"
    CURLED_RATIO = 0.70         # tip-to-wrist / MCP-to-wrist ratio for "curled"
                                # (tip closer to wrist than MCP = curled)
    PINCH_DIST = 0.06           # normalized distance thumb→index for pinch
    HOLD_SPEED = 0.015          # speed below which counts as "hold"
    HOLD_TIME = 1.5             # seconds to trigger hold
    SWIPE_SPEED = 0.06          # speed above which counts as "swipe"
    DETECTION_FRAMES = 5        # frames before gesture is "started"
    COOLDOWN_DEFAULT = 2.0      # seconds default cooldown
    COOLDOWN_PINCH = 4.0        # longer cooldown for seed-creating gestures
    TWO_HAND_EXPAND_RATIO = 0.3 # distance change ratio for expand/compress
    TWO_HAND_SYNC_ANGLE = 0.5   # radians max angle difference for "sync"


# ============================================================
# Gesture Recognizer — raw landmarks → gesture
# ============================================================

class GestureRecognizer:
    """Detects gestures from MediaPipe hand landmarks."""

    @staticmethod
    def _dist(lm: list[tuple[float, float, float]], a: int, b: int) -> float:
        """Euclidean distance between two landmarks (normalized coords)."""
        dx = lm[a][0] - lm[b][0]
        dy = lm[a][1] - lm[b][1]
        return math.sqrt(dx * dx + dy * dy)

    @staticmethod
    def _finger_extended(lm: list[tuple[float, float, float]],
                         tip_idx: int, mcp_idx: int) -> bool:
        """Check if a finger is extended."""
        tip_to_mcp = GestureRecognizer._dist(lm, tip_idx, mcp_idx)
        mcp_to_wrist = GestureRecognizer._dist(lm, mcp_idx, WRIST)
        if mcp_to_wrist < 0.02:
            return False
        return (tip_to_mcp / mcp_to_wrist) > GestureConfig.EXTENDED_RATIO

    @staticmethod
    def _finger_curled(lm: list[tuple[float, float, float]],
                       tip_idx: int, mcp_idx: int) -> bool:
        """Check if a finger is curled."""
        tip_to_wrist = GestureRecognizer._dist(lm, tip_idx, WRIST)
        mcp_to_wrist = GestureRecognizer._dist(lm, mcp_idx, WRIST)
        if mcp_to_wrist < 0.02:
            return True
        return (tip_to_wrist / mcp_to_wrist) < GestureConfig.CURLED_RATIO

    @staticmethod
    def detect(lm: list[tuple[float, float, float]],
               speed: float) -> tuple[str, float]:
        """Detect gesture from landmarks + hand speed.

        Args:
            lm: 21 (x, y, z) tuples from MediaPipe.
            speed: Current hand speed (normalized units).

        Returns:
            (gesture_type, confidence) — confidence 0.0–1.0.
        """
        if len(lm) < 21:
            return GESTURE_NONE, 0.0

        # Count extended fingers
        extended = [
            GestureRecognizer._finger_extended(lm, tip, mcp)
            for tip, mcp in zip(FINGER_TIPS, FINGER_MCPS)
        ]
        n_extended = sum(extended)

        # Count curled fingers
        curled = [
            GestureRecognizer._finger_curled(lm, tip, mcp)
            for tip, mcp in zip(FINGER_TIPS, FINGER_MCPS)
        ]
        n_curled = sum(curled)

        # ── Pinch (highest priority — thumb + index specific) ──
        pinch_dist = GestureRecognizer._dist(lm, THUMB_TIP, INDEX_TIP)
        if pinch_dist < GestureConfig.PINCH_DIST:
            conf = 1.0 - pinch_dist / GestureConfig.PINCH_DIST
            return GESTURE_PINCH, min(1.0, conf)

        # ── Point — only index extended ──
        if extended[0] and n_extended == 1 and n_curled >= 2:
            return GESTURE_POINT, 0.85

        # ── Victory — index + middle extended, ring + pinky curled ──
        if extended[0] and extended[1] and curled[2] and curled[3]:
            return GESTURE_VICTORY, 0.85

        # ── Open Palm — all 4 extended ──
        if n_extended >= 4:
            return GESTURE_OPEN_PALM, n_extended / 4.0

        # ── Fist — all 4 curled ──
        if n_curled >= 4:
            return GESTURE_FIST, n_curled / 4.0

        # ── Hold / Swipe (speed-based) ──
        if speed < GestureConfig.HOLD_SPEED:
            return GESTURE_HOLD, 0.7

        # ── Partial gestures (transitional) ──
        if n_extended >= 3:
            return GESTURE_OPEN_PALM, 0.6
        if n_curled >= 3:
            return GESTURE_FIST, 0.6

        return GESTURE_NONE, 0.0


# ============================================================
# Gesture State Machine
# ============================================================

class GestureState:
    """Per-gesture state machine.

    States: IDLE → STARTED → HOLDING → TRIGGERED → COOLDOWN → IDLE
    """

    IDLE = "idle"
    STARTED = "started"
    HOLDING = "holding"
    TRIGGERED = "triggered"
    COOLDOWN = "cooldown"

    def __init__(self, cooldown: float = GestureConfig.COOLDOWN_DEFAULT) -> None:
        self.state: str = self.IDLE
        self.cooldown_duration: float = cooldown
        self._state_timer: float = 0.0
        self._hold_timer: float = 0.0
        self._cooldown_timer: float = 0.0
        self._detection_frames: int = 0

    def update(self, detected: bool, dt: float) -> str | None:
        """Advance state machine. Returns event name if triggered, else None.

        Args:
            detected: Whether the gesture is currently recognized.
            dt: Time delta in seconds.

        Returns:
            Gesture type string if TRIGGERED this frame, None otherwise.
        """
        if self.state == self.IDLE:
            if detected:
                self._detection_frames += 1
                if self._detection_frames >= GestureConfig.DETECTION_FRAMES:
                    self.state = self.STARTED
                    self._hold_timer = 0.0
            else:
                self._detection_frames = max(0, self._detection_frames - 1)

        elif self.state == self.STARTED:
            if detected:
                self._hold_timer += dt
                self.state = self.HOLDING
            else:
                self.state = self.IDLE
                self._detection_frames = 0

        elif self.state == self.HOLDING:
            if detected:
                self._hold_timer += dt
            else:
                # Gesture ended → trigger
                self.state = self.TRIGGERED
                self._cooldown_timer = 0.0
                return "triggered"

        elif self.state == self.TRIGGERED:
            self.state = self.COOLDOWN
            self._cooldown_timer = 0.0

        elif self.state == self.COOLDOWN:
            self._cooldown_timer += dt
            if self._cooldown_timer >= self.cooldown_duration:
                self.state = self.IDLE
                self._detection_frames = 0
                self._hold_timer = 0.0

        return None

    @property
    def hold_time(self) -> float:
        return self._hold_timer

    @property
    def cooldown_remaining(self) -> float:
        if self.state == self.COOLDOWN:
            return max(0.0, self.cooldown_duration - self._cooldown_timer)
        return 0.0


# ============================================================
# Gesture Manager
# ============================================================

class GestureManager:
    """Central coordinator for gesture recognition on both hands.

    Provides:
        - Per-hand gesture detection
        - State machines with cooldown
        - Two-hand interaction detection
        - Event-based output (triggers fire once)

    Usage:
        mgr = GestureManager()
        mgr.update(landmarks, hand_data)   # call each frame
        events = mgr.get_events()          # list of (hand, gesture) triggered
        mgr.get_active("left")             # current gesture on left hand
    """

    def __init__(self) -> None:
        # Per-hand gesture state machines
        self._states: dict[str, GestureState] = {}  # gesture → GestureState
        # Per-hand current detection
        self._current: dict[str, tuple[str, float]] = {"left": (GESTURE_NONE, 0.0),
                                                         "right": (GESTURE_NONE, 0.0)}
        self._hold_start: dict[str, float] = {"left": 0.0, "right": 0.0}

        # Events fired this frame: list of (side, gesture, extra_data)
        self._events: list[tuple[str, str, dict]] = []

        # Two-hand tracking
        self._two_hand_distance: float = 0.0
        self._prev_two_hand_distance: float = 0.0
        self._two_hand_angle: float = 0.0
        self._hands_crossed: bool = False

    # ── Update ──────────────────────────────────────────

    def update(
        self,
        landmarks: dict[str, list[tuple[float, float, float]]],
        hand_data: list[dict],
        dt: float,
    ) -> None:
        """Process one frame. Call once per draw().

        Args:
            landmarks: {"Left": [(x,y,z)*21], "Right": [...]} from CameraTracker.
            hand_data: List of {"side": "left"/"right", "speed": ...}.
            dt: Time delta in seconds.
        """
        self._events = []

        # Build speed lookup
        speeds: dict[str, float] = {}
        for h in hand_data:
            speeds[h["side"].lower()] = h.get("speed", 0.0)

        # ── Per-hand gesture detection ──────────────────
        hand_positions: dict[str, tuple[float, float]] = {}

        for side_key, lm in landmarks.items():
            side = side_key.lower()
            if side not in ("left", "right"):
                continue
            if len(lm) < 21:
                continue

            speed = speeds.get(side, 0.0)
            gesture, conf = GestureRecognizer.detect(lm, speed)
            self._current[side] = (gesture, conf)

            # Store hand center for two-hand detection
            wrist = lm[WRIST]
            mcp = lm[MIDDLE_MCP]
            hx = (wrist[0] + mcp[0]) / 2.0
            hy = (wrist[1] + mcp[1]) / 2.0
            hand_positions[side] = (hx, hy)

            # State machine
            if gesture != GESTURE_NONE:
                state = self._get_state(gesture)
                event = state.update(True, dt)
                if event:
                    self._events.append((side, gesture, {
                        "hold_time": state.hold_time,
                        "confidence": conf,
                    }))
                    state.update(False, dt)  # move to COOLDOWN
            else:
                # Tick all active states toward idle
                for g, s in list(self._states.items()):
                    s.update(False, dt)

        # ── Two-hand detection ──────────────────────────
        if len(hand_positions) >= 2:
            self._detect_two_hand(hand_positions, speeds, dt)

    def _get_state(self, gesture: str) -> GestureState:
        """Get or create state machine for a gesture type."""
        if gesture not in self._states:
            cd = GestureConfig.COOLDOWN_PINCH if gesture == GESTURE_PINCH \
                else GestureConfig.COOLDOWN_DEFAULT
            self._states[gesture] = GestureState(cooldown=cd)
        return self._states[gesture]

    # ── Two-Hand Detection ──────────────────────────────

    def _detect_two_hand(
        self,
        positions: dict[str, tuple[float, float]],
        speeds: dict[str, float],
        dt: float,
    ) -> None:
        """Detect two-hand interactions."""
        sides = list(positions.keys())
        if len(sides) < 2:
            return

        x1, y1 = positions[sides[0]]
        x2, y2 = positions[sides[1]]
        dist = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        angle = math.atan2(y2 - y1, x2 - x1)

        # Expand / Compress
        if self._prev_two_hand_distance > 0:
            delta = dist - self._prev_two_hand_distance
            threshold = GestureConfig.TWO_HAND_EXPAND_RATIO
            if delta > threshold:
                self._events.append(("both", TWO_HAND_EXPAND, {"delta": delta}))
            elif delta < -threshold:
                self._events.append(("both", TWO_HAND_COMPRESS, {"delta": -delta}))

        # Cross detection (hands swap sides on X axis)
        prev_crossed = self._hands_crossed
        self._hands_crossed = (x1 - x2) * (self._prev_x1 - self._prev_x2) < 0 \
            if hasattr(self, '_prev_x1') and hasattr(self, '_prev_x2') else False
        if self._hands_crossed and not prev_crossed:
            self._events.append(("both", TWO_HAND_CROSS, {}))

        # Sync (both hands moving in similar direction)
        if all(s > GestureConfig.HOLD_SPEED for s in speeds.values()):
            self._events.append(("both", TWO_HAND_SYNC, {"angle_diff": 0.0}))

        self._prev_two_hand_distance = dist
        self._two_hand_distance = dist
        self._prev_x1, self._prev_x2 = x1, x2
        self._two_hand_angle = angle

    # ── Query ───────────────────────────────────────────

    def get_events(self) -> list[tuple[str, str, dict]]:
        """Return gesture events triggered this frame.

        Returns:
            List of (side, gesture_type, extra_data).
            side: "left", "right", or "both".
        """
        return self._events

    def get_active(self, side: str) -> tuple[str, float]:
        """Get currently detected gesture on a hand.

        Returns:
            (gesture_type, confidence).
        """
        return self._current.get(side, (GESTURE_NONE, 0.0))

    def get_state_info(self, gesture: str) -> dict | None:
        """Get state machine info for a gesture."""
        if gesture in self._states:
            s = self._states[gesture]
            return {
                "state": s.state,
                "hold_time": s.hold_time,
                "cooldown": s.cooldown_remaining,
            }
        return None

    @property
    def two_hand_distance(self) -> float:
        return self._two_hand_distance
