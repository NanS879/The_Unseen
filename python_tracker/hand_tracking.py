"""
Hand tracking module using MediaPipe Hands.

Detects hand landmarks from webcam frames and extracts:
- Hand center position (normalized 0.0–1.0) for each hand
- Hand movement speed per hand
- Hand side (Left / Right) from MediaPipe handedness
- Supports up to 2 hands simultaneously
"""

import time
import math
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np


class HandTracker:
    """MediaPipe-based hand detector for dual-hand interaction.

    Detects up to 2 hands, identifies left vs right, tracks position and
    speed independently for each hand.
    """

    # Landmark indices
    LANDMARK_WRIST = 0
    LANDMARK_MIDDLE_FINGER_MCP = 9

    def __init__(
        self,
        max_num_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        speed_smoothing: float = 0.4,
    ) -> None:
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=max_num_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

        self.speed_smoothing = speed_smoothing

        # Per-hand state tracking, keyed by side ("Left" / "Right")
        self._hand_state: dict[str, dict] = {}

    def _get_hand_state(self, side: str) -> dict:
        """Get or create tracking state for a given hand side."""
        if side not in self._hand_state:
            self._hand_state[side] = {
                "prev_x": None,
                "prev_y": None,
                "prev_time": None,
                "smoothed_speed": 0.0,
            }
        return self._hand_state[side]

    def process_frame(self, frame: np.ndarray) -> list[dict]:
        """Process a BGR frame and extract hand data for all detected hands.

        Args:
            frame: A BGR image from OpenCV (H, W, 3) in uint8.

        Returns:
            A list of hand-data dicts, each with keys:
                hand_x: float        – normalized x [0.0, 1.0]
                hand_y: float        – normalized y [0.0, 1.0]
                hand_speed: float    – movement speed (normalized units/sec)
                hand_side: str       – "Left" or "Right"
                hand_detected: float – 1.0 (always 1.0 for detected hands)
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)
        rgb_frame.flags.writeable = True

        hands_data: list[dict] = []

        if results.multi_hand_landmarks and results.multi_handedness:
            for hand_landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                # Determine side: MediaPipe returns "Left" or "Right"
                side = handedness.classification[0].label  # "Left" or "Right"

                # Compute hand center
                wrist = hand_landmarks.landmark[self.LANDMARK_WRIST]
                mcp = hand_landmarks.landmark[self.LANDMARK_MIDDLE_FINGER_MCP]
                hand_x = (wrist.x + mcp.x) / 2.0
                hand_y = (wrist.y + mcp.y) / 2.0

                # Compute speed from position delta
                state = self._get_hand_state(side)
                now = time.perf_counter()
                if state["prev_x"] is not None and state["prev_time"] is not None:
                    dx = hand_x - state["prev_x"]
                    dy = hand_y - state["prev_y"]
                    dt = now - state["prev_time"]
                    if dt > 0.001:
                        instant_speed = math.sqrt(dx * dx + dy * dy) / dt
                        state["smoothed_speed"] = (
                            self.speed_smoothing * instant_speed
                            + (1.0 - self.speed_smoothing) * state["smoothed_speed"]
                        )

                state["prev_x"] = hand_x
                state["prev_y"] = hand_y
                state["prev_time"] = now

                hands_data.append({
                    "hand_x": hand_x,
                    "hand_y": hand_y,
                    "hand_speed": state["smoothed_speed"],
                    "hand_side": side,
                    "hand_detected": 1.0,
                })

        # Reset state for hands that disappeared this frame
        active_sides = {h["hand_side"] for h in hands_data}
        for side in list(self._hand_state.keys()):
            if side not in active_sides:
                st = self._hand_state[side]
                st["prev_x"] = None
                st["prev_y"] = None
                st["prev_time"] = None
                st["smoothed_speed"] = 0.0

        return hands_data

    def draw_debug(self, frame: np.ndarray, hands_data: list[dict]) -> np.ndarray:
        """Draw hand landmarks and center crosshair for all detected hands.

        Args:
            frame: The BGR image to draw on (modified in place).
            hands_data: The list returned by process_frame().

        Returns:
            The annotated frame (same array).
        """
        h, w = frame.shape[:2]

        if not hands_data:
            cv2.putText(
                frame,
                "No hands detected",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return frame

        # Distinct colors per side
        COLORS = {
            "Right": (0, 255, 255),   # Yellow for right hand
            "Left": (255, 120, 255),  # Magenta for left hand
        }

        y_offset = 40
        for hand in hands_data:
            side = hand["hand_side"]
            color = COLORS.get(side, (0, 255, 0))
            cx = int(hand["hand_x"] * w)
            cy = int(hand["hand_y"] * h)

            # Crosshair
            cv2.drawMarker(frame, (cx, cy), color, cv2.MARKER_CROSS, 20, 2)

            # Info text per hand
            cv2.putText(
                frame,
                f"{side}: ({hand['hand_x']:.3f}, {hand['hand_y']:.3f})",
                (30, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2,
            )
            y_offset += 24
            cv2.putText(
                frame,
                f"  Speed: {hand['hand_speed']:.4f}",
                (30, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
            )
            y_offset += 24

        return frame

    def close(self) -> None:
        """Release MediaPipe resources."""
        self.hands.close()
