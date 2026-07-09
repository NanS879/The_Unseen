"""
Inline camera + MediaPipe hand tracker for single-runtime V4.

Replaces the OSC-based two-process architecture. Camera frames are
grabbed and processed directly in the py5 draw loop.

Usage:
    tracker = CameraTracker()
    tracker.start()              # in setup()
    hands = tracker.update()     # in draw() — returns list of hand dicts
    tracker.draw_debug(py5)      # optional — overlay camera on sketch
    tracker.stop()               # on exit

Design:
    - Camera runs at 30fps (half the render rate to save GPU)
    - MediaPipe processed every frame the camera updates
    - Hand data returned directly — no OSC, no threads, no network
"""

import time
import math
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np


class CameraTracker:
    """Inline camera + MediaPipe hand tracker.

    Opens webcam, processes frames with MediaPipe Hands,
    returns per-hand position/speed data each frame.
    """

    def __init__(
        self,
        camera_index: int = 0,
        camera_width: int = 640,
        camera_height: int = 480,
        max_hands: int = 2,
        detect_conf: float = 0.7,
        track_conf: float = 0.5,
        process_every_n: int = 2,     # process every Nth draw frame
    ) -> None:
        """Initialize tracker (camera opens on start()).

        Args:
            camera_index: Webcam device index.
            camera_width, camera_height: Capture resolution.
            max_hands: Max hands to detect.
            detect_conf: MediaPipe detection confidence.
            track_conf: MediaPipe tracking confidence.
            process_every_n: Only process camera every N draw frames.
        """
        self.camera_index = camera_index
        self.cam_w = camera_width
        self.cam_h = camera_height
        self.process_every_n = process_every_n

        self._cap: Optional[cv2.VideoCapture] = None
        self._hands: Optional[mp.solutions.hands.Hands] = None
        self._frame: Optional[np.ndarray] = None
        self._frame_count: int = 0

        # MediaPipe init
        self.mp_hands = mp.solutions.hands
        self._detect_conf = detect_conf
        self._track_conf = track_conf
        self._max_hands = max_hands

        # Per-hand speed tracking state
        self._prev: dict[str, dict] = {}  # side → {x, y, time, speed}
        # Per-hand raw landmarks (21 points × 3 coords each)
        self._landmarks: dict[str, list[tuple[float, float, float]]] = {}

    # ── Lifecycle ───────────────────────────────────────

    def start(self) -> bool:
        """Open camera and init MediaPipe. Returns True on success."""
        self._cap = cv2.VideoCapture(self.camera_index)
        if not self._cap.isOpened():
            print(f"[Camera] ERROR: Cannot open camera {self.camera_index}")
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.cam_w)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.cam_h)
        actual_w = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"[Camera] Opened: {actual_w}x{actual_h} @ index {self.camera_index}")

        self._hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=self._max_hands,
            min_detection_confidence=self._detect_conf,
            min_tracking_confidence=self._track_conf,
        )
        print("[Camera] MediaPipe Hands initialized")
        return True

    def stop(self) -> None:
        """Release camera and MediaPipe resources."""
        if self._hands:
            self._hands.close()
            self._hands = None
        if self._cap:
            self._cap.release()
            self._cap = None
        print("[Camera] Released")

    # ── Frame Processing ────────────────────────────────

    def update(self) -> list[dict]:
        """Grab + process one frame. Returns list of hand data dicts.

        Each dict: {side, x, y, speed, detected}
        x, y are NORMALIZED [0.0–1.0].

        Returns empty list if camera not ready or processing skipped.
        """
        if self._cap is None or self._hands is None:
            return []

        self._frame_count += 1

        # Only process every Nth frame for performance
        if self._frame_count % self.process_every_n != 0:
            # Return last known data (stale but still valid for smooth tracking)
            return self._last_result()

        # Grab frame
        ret, frame = self._cap.read()
        if not ret:
            return self._last_result()

        # Mirror for natural interaction
        frame = cv2.flip(frame, 1)
        self._frame = frame

        # MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        # Extract hand data
        hands_data: list[dict] = []
        now = time.perf_counter()

        if results.multi_hand_landmarks and results.multi_handedness:
            for landmarks, handedness in zip(
                results.multi_hand_landmarks, results.multi_handedness
            ):
                side = handedness.classification[0].label  # "Left" / "Right"

                # Hand center: midpoint of wrist + middle finger MCP
                wrist = landmarks.landmark[0]
                mcp = landmarks.landmark[9]
                hx = (wrist.x + mcp.x) / 2.0
                hy = (wrist.y + mcp.y) / 2.0

                # Speed
                speed = 0.0
                prev = self._prev.get(side)
                if prev and prev.get("x") is not None:
                    dx = hx - prev["x"]
                    dy = hy - prev["y"]
                    dt = now - prev.get("time", now)
                    if dt > 0.001:
                        instant = math.sqrt(dx * dx + dy * dy) / dt
                        # EMA smoothing
                        prev["speed"] = (
                            0.4 * instant + 0.6 * prev.get("speed", 0.0)
                        )
                        speed = prev["speed"]

                self._prev[side] = {"x": hx, "y": hy, "time": now, "speed": speed}

                # Store raw landmarks for gesture recognition
                self._landmarks[side] = [
                    (lm.x, lm.y, lm.z) for lm in landmarks.landmark
                ]

                hands_data.append({
                    "side": side,
                    "x": hx,
                    "y": hy,
                    "speed": speed,
                    "detected": True,
                })

        # Mark missing hands
        active_sides = {h["side"] for h in hands_data}
        for side in list(self._prev.keys()):
            if side not in active_sides:
                self._prev[side]["x"] = None
                self._prev[side]["speed"] = 0.0

        return hands_data

    def _last_result(self) -> list[dict]:
        """Return last known hand positions (stale but smooth)."""
        result = []
        for side, state in self._prev.items():
            if state.get("x") is not None:
                result.append({
                    "side": side,
                    "x": state["x"],
                    "y": state["y"],
                    "speed": state.get("speed", 0.0),
                    "detected": True,
                })
        return result

    # ── Debug ───────────────────────────────────────────

    def draw_debug(self, py5) -> None:
        """Overlay the camera frame on the py5 sketch (debug only)."""
        if self._frame is None:
            return
        # Convert BGR → RGB and render as py5 image
        rgb = cv2.cvtColor(self._frame, cv2.COLOR_BGR2RGB)
        img = py5.create_image_from_numpy(rgb, "RGB")
        py5.image(img, 0, 0, 320, 240)  # small preview in corner

    def get_landmarks(self) -> dict[str, list[tuple[float, float, float]]]:
        """Return raw MediaPipe landmarks per hand.

        Returns:
            Dict mapping side ("Left"/"Right") → list of 21 (x, y, z) tuples.
            x, y are normalized [0–1]. z is relative depth.
            Empty dict if no hands or camera not ready.
        """
        return self._landmarks

    def get_frame(self) -> Optional[np.ndarray]:
        """Return the latest camera frame (BGR), or None."""
        return self._frame

    @property
    def is_ready(self) -> bool:
        return self._cap is not None and self._cap.isOpened()
