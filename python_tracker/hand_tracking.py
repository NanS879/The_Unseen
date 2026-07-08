"""
Hand tracking module using MediaPipe Hands.

Detects hand landmarks from webcam frames and extracts:
- Hand center position (normalized 0.0–1.0)
- Hand movement speed
- Detection status
"""

import time
import math
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np


class HandTracker:
    """MediaPipe-based hand detector that extracts hand center and speed.

    Uses landmark 9 (middle finger MCP) and landmark 0 (wrist) averaged
    together for a stable hand-center position.
    """

    # Landmark indices
    LANDMARK_WRIST = 0
    LANDMARK_MIDDLE_FINGER_MCP = 9

    def __init__(
        self,
        max_num_hands: int = 1,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        speed_smoothing: float = 0.4,
    ) -> None:
        """Initialize MediaPipe Hands.

        Args:
            max_num_hands: Maximum number of hands to detect (1 is sufficient
                for single-user interaction).
            min_detection_confidence: Minimum confidence for hand detection
                (0.0–1.0). Higher values reduce false positives.
            min_tracking_confidence: Minimum confidence for landmark tracking
                (0.0–1.0). Higher values improve stability.
            speed_smoothing: EMA alpha for speed smoothing. Lower = smoother
                but more lag. 0.4 is a good balance for 30fps.
        """
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

        # State tracking
        self._prev_x: Optional[float] = None
        self._prev_y: Optional[float] = None
        self._prev_time: Optional[float] = None
        self._smoothed_speed: float = 0.0

    def process_frame(self, frame: np.ndarray) -> dict:
        """Process a BGR frame and extract hand data.

        Args:
            frame: A BGR image from OpenCV (H, W, 3) in uint8.

        Returns:
            A dict with keys:
                hand_x: float       – normalized x [0.0, 1.0]
                hand_y: float       – normalized y [0.0, 1.0]
                hand_speed: float   – movement speed (normalized units / sec)
                hand_detected: float – 1.0 if hand present, else 0.0
        """
        # MediaPipe expects RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.hands.process(rgb_frame)
        rgb_frame.flags.writeable = True

        if results.multi_hand_landmarks:
            # Use the first detected hand
            hand_landmarks = results.multi_hand_landmarks[0]

            # Compute hand center from wrist + middle finger MCP
            wrist = hand_landmarks.landmark[self.LANDMARK_WRIST]
            mcp = hand_landmarks.landmark[self.LANDMARK_MIDDLE_FINGER_MCP]

            hand_x = (wrist.x + mcp.x) / 2.0
            hand_y = (wrist.y + mcp.y) / 2.0

            # Compute speed from position delta
            now = time.perf_counter()
            if self._prev_x is not None and self._prev_time is not None:
                dx = hand_x - self._prev_x
                dy = hand_y - self._prev_y
                dt = now - self._prev_time

                if dt > 0.001:
                    instant_speed = math.sqrt(dx * dx + dy * dy) / dt
                    # Exponential moving average smoothing
                    self._smoothed_speed = (
                        self.speed_smoothing * instant_speed
                        + (1.0 - self.speed_smoothing) * self._smoothed_speed
                    )

            self._prev_x = hand_x
            self._prev_y = hand_y
            self._prev_time = now

            return {
                "hand_x": hand_x,
                "hand_y": hand_y,
                "hand_speed": self._smoothed_speed,
                "hand_detected": 1.0,
            }
        else:
            # No hand detected — reset tracking state
            self._prev_x = None
            self._prev_y = None
            self._prev_time = None
            self._smoothed_speed = 0.0

            return {
                "hand_x": 0.0,
                "hand_y": 0.0,
                "hand_speed": 0.0,
                "hand_detected": 0.0,
            }

    def draw_debug(self, frame: np.ndarray, hand_data: dict) -> np.ndarray:
        """Draw hand landmarks and center crosshair on the frame.

        Args:
            frame: The BGR image to draw on (modified in place).
            hand_data: The dict returned by process_frame().

        Returns:
            The annotated frame (same array).
        """
        if hand_data["hand_detected"] < 0.5:
            # Show "no hand" text
            cv2.putText(
                frame,
                "No hand detected",
                (30, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            return frame

        h, w = frame.shape[:2]
        cx = int(hand_data["hand_x"] * w)
        cy = int(hand_data["hand_y"] * h)

        # Draw crosshair at hand center
        crosshair_color = (0, 255, 255)  # yellow
        cv2.drawMarker(
            frame, (cx, cy), crosshair_color, cv2.MARKER_CROSS, 20, 2
        )

        # Draw info text
        cv2.putText(
            frame,
            f"Hand: ({hand_data['hand_x']:.3f}, {hand_data['hand_y']:.3f})",
            (30, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )
        cv2.putText(
            frame,
            f"Speed: {hand_data['hand_speed']:.4f}",
            (30, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2,
        )

        return frame

    def close(self) -> None:
        """Release MediaPipe resources."""
        self.hands.close()
