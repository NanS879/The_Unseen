"""
Camera Background + Real-time Filter System.

Uses the existing CameraTracker frame data (no second camera device).
Applies 10 real-time OpenCV/numpy filters. All filters return numpy
arrays compatible with py5.create_image_from_numpy().

Filter names mirror AI moods for automatic switching:
    mood → filter
    Hope/Warm → warm, Calm → normal, Dream → dream,
    Silence → noir, Curiosity → ai_vision, Bloom/Excited → glitch

Performance:
    - Filters use numpy vectorized ops (no Python loops)
    - Sketch filter throttled to every 3 frames (Sobel is expensive)
    - Pixel filter uses cv2.resize (hardware accelerated)
    - All filters release intermediate arrays immediately
"""

import cv2
import numpy as np
import random
from typing import Optional


# ============================================================
# Filter Manager — 10 real-time camera filters
# ============================================================

class FilterManager:
    """Applies real-time color/effect filters to camera frames.

    All methods take a BGR numpy array (H, W, 3) and return a new
    BGR or RGB numpy array. No side effects on input.
    """

    # Current filter name
    current: str = "normal"
    # Cache last filter name for transition detection
    _last: str = "normal"
    # Frame counter for throttled filters
    _frame_count: int = 0
    # Cached sketch edges (expensive, recalculated every 3 frames)
    _sketch_cache: Optional[np.ndarray] = None
    # Pixel cache
    _pixel_cache: Optional[np.ndarray] = None
    _pixel_scale: float = 0.15

    @classmethod
    def apply(cls, frame: np.ndarray, filter_name: str = "normal") -> np.ndarray:
        """Apply named filter to frame. Returns RGB image for py5.

        Args:
            frame: BGR numpy array (H, W, 3) from OpenCV.
            filter_name: One of: normal, grayscale, warm, cold, dream,
                noir, ai_vision, sketch, pixel, glitch.

        Returns:
            RGB numpy array same shape as input.
        """
        cls._frame_count += 1
        cls.current = filter_name

        # Dispatch to filter method
        methods = {
            "normal":     cls._normal,
            "grayscale":  cls._grayscale,
            "warm":       cls._warm,
            "cold":       cls._cold,
            "dream":      cls._dream,
            "noir":       cls._noir,
            "ai_vision":  cls._ai_vision,
            "sketch":     cls._sketch,
            "pixel":      cls._pixel,
            "glitch":     cls._glitch,
        }
        fn = methods.get(filter_name, cls._normal)
        result = fn(frame)
        # Ensure RGB output for py5
        if result.shape[-1] == 3:
            return result
        return result

    # ── Filter implementations ──────────────────────────

    @staticmethod
    def _normal(frame: np.ndarray) -> np.ndarray:
        """Original camera feed, BGR→RGB."""
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    @staticmethod
    def _grayscale(frame: np.ndarray) -> np.ndarray:
        """Black and white. Convert to gray, stack to 3 channels."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)

    @staticmethod
    def _warm(frame: np.ndarray) -> np.ndarray:
        """Warm golden tone. Boost red, reduce blue."""
        result = frame.astype(np.float32)
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.3, 0, 255)  # R +30%
        result[:, :, 0] = np.clip(result[:, :, 0] * 0.7, 0, 255)  # B -30%
        # Add slight yellow tint
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.1, 0, 255)  # G +10%
        rgb = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB)
        return rgb

    @staticmethod
    def _cold(frame: np.ndarray) -> np.ndarray:
        """Cool blue tone. Boost blue, reduce red."""
        result = frame.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.4, 0, 255)  # B +40%
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.6, 0, 255)  # R -40%
        rgb = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB)
        return rgb

    @staticmethod
    def _dream(frame: np.ndarray) -> np.ndarray:
        """Purple-blue dreamlike. Boost blue+red, soften."""
        # Gaussian blur for softness
        soft = cv2.GaussianBlur(frame, (7, 7), 3.0)
        result = soft.astype(np.float32)
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.3, 0, 255)  # B
        result[:, :, 2] = np.clip(result[:, :, 2] * 1.2, 0, 255)  # R
        # Purple tint: add uniform blue-red overlay
        overlay = np.zeros_like(result)
        overlay[:, :, 0] = 20  # B
        overlay[:, :, 2] = 15  # R
        result = np.clip(result + overlay, 0, 255)
        rgb = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB)
        return rgb

    @staticmethod
    def _noir(frame: np.ndarray) -> np.ndarray:
        """Film noir: desaturated, high contrast, vignette."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Increase contrast
        gray = cv2.convertScaleAbs(gray, alpha=1.5, beta=-30)
        # Slight blue tint for film look
        color = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        result = color.astype(np.float32)
        # Vignette: darken edges
        h, w = result.shape[:2]
        Y, X = np.ogrid[:h, :w]
        cx, cy = w / 2, h / 2
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
        max_dist = np.sqrt(cx ** 2 + cy ** 2)
        vignette = 1.0 - 0.5 * (dist / max_dist)
        vignette = np.clip(vignette, 0.3, 1.0)
        for c in range(3):
            result[:, :, c] = np.clip(result[:, :, c] * vignette, 0, 255)
        rgb = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB)
        return rgb

    @staticmethod
    def _ai_vision(frame: np.ndarray) -> np.ndarray:
        """Cyan-green futuristic tech look. Shift colors toward cyan."""
        result = frame.astype(np.float32)
        # Push toward cyan (high G, high B, low R)
        result[:, :, 2] = np.clip(result[:, :, 2] * 0.4, 0, 255)  # R low
        result[:, :, 1] = np.clip(result[:, :, 1] * 1.3, 0, 255)  # G high
        result[:, :, 0] = np.clip(result[:, :, 0] * 1.4, 0, 255)  # B high
        # Cyan overlay tint
        result[:, :, 0] = np.clip(result[:, :, 0] + 10, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] + 10, 0, 255)
        rgb = cv2.cvtColor(result.astype(np.uint8), cv2.COLOR_BGR2RGB)
        return rgb

    @classmethod
    def _sketch(cls, frame: np.ndarray) -> np.ndarray:
        """Edge detection sketch. Expensive — throttled to every 3 frames."""
        # Use cache for 2 out of 3 frames
        if cls._frame_count % 3 != 0 and cls._sketch_cache is not None:
            return cls._sketch_cache
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        # Sobel edge detection in X and Y
        sobel_x = cv2.Sobel(blur, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(blur, cv2.CV_64F, 0, 1, ksize=3)
        edges = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        edges = np.clip(edges, 0, 255).astype(np.uint8)
        # Invert: white edges on black → black edges on white
        edges = 255 - edges
        rgb = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
        cls._sketch_cache = rgb
        return rgb

    @classmethod
    def _pixel(cls, frame: np.ndarray) -> np.ndarray:
        """Low-res pixel art style."""
        if cls._pixel_cache is not None and cls._frame_count % 2 == 0:
            return cls._pixel_cache
        h, w = frame.shape[:2]
        small_h = max(4, int(h * cls._pixel_scale))
        small_w = max(4, int(w * cls._pixel_scale))
        small = cv2.resize(frame, (small_w, small_h), interpolation=cv2.INTER_NEAREST)
        pixelated = cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
        rgb = cv2.cvtColor(pixelated, cv2.COLOR_BGR2RGB)
        cls._pixel_cache = rgb
        return rgb

    @staticmethod
    def _glitch(frame: np.ndarray) -> np.ndarray:
        """Subtle glitch effect: horizontal shift + color channel offset."""
        h, w = frame.shape[:2]
        result = frame.copy()
        # Random horizontal slice shift
        if random.random() < 0.3:
            y1 = random.randint(0, h - 50)
            y2 = y1 + random.randint(10, 40)
            shift = random.randint(-15, 15)
            slice_data = result[y1:y2, :].copy()
            if shift > 0:
                result[y1:y2, shift:] = slice_data[:, :-shift]
            elif shift < 0:
                result[y1:y2, :shift] = slice_data[:, -shift:]
        # Color channel offset (red channel shift)
        if random.random() < 0.5:
            offset = random.randint(-3, 3)
            ch_r = result[:, :, 2].copy()
            if offset > 0:
                result[:-offset, :, 2] = ch_r[offset:, :]
        rgb = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
        return rgb

    # ── AI mood → filter mapping ──────────────────────

    MOOD_FILTER_MAP = {
        "Calm":      "normal",
        "Hope":      "warm",
        "Curiosity": "ai_vision",
        "Dream":     "dream",
        "Harmony":   "warm",
        "Bloom":     "glitch",
        "Silence":   "noir",
        "Lonely":    "cold",
        "":          "normal",
    }

    @classmethod
    def from_mood(cls, mood: str) -> str:
        """Get filter name for an AI mood string."""
        return cls.MOOD_FILTER_MAP.get(mood, "normal")


# ============================================================
# Camera Background Manager
# ============================================================

class CameraBgManager:
    """Reads frames from existing CameraTracker, applies filter, renders.

    Performance:
        - Camera raw is 640x480 (4:3). Canvas is 1280x720 (16:9).
        - Center-crops camera to 16:9 (640x360), then downscales to PROCESS_WxPROCESS_H.
        - GPU upload every 3 frames (~20fps); cached py5 image reused.
    """

    PROCESS_W = 320
    PROCESS_H = 180       # 16:9 — matches canvas (1280×720)
    CAMERA_RAW_W = 640
    CAMERA_RAW_H = 480   # 4:3
    UPDATE_EVERY_N = 3

    def __init__(self) -> None:
        self.filter_name: str = "normal"
        self._cached_img: object = None   # py5 image, reused across frames
        self._last_display_w: int = 0
        self._last_display_h: int = 0
        self._draw_count: int = 0

    def set_filter(self, name: str) -> None:
        """Set the active filter by name."""
        if name in ("normal", "grayscale", "warm", "cold", "dream",
                     "noir", "ai_vision", "sketch", "pixel", "glitch"):
            self.filter_name = name
            self._cached_img = None  # force refresh on filter change

    def set_filter_from_mood(self, mood: str) -> None:
        """Set filter based on AI mood string."""
        name = FilterManager.from_mood(mood)
        if name != self.filter_name:
            self.filter_name = name
            self._cached_img = None

    def draw_background(self, py5, camera_tracker) -> None:
        """Draw filtered camera feed as fullscreen background.

        Camera raw is 640×480 (4:3). Canvas is 1280×720 (16:9).
        We center-crop camera to 16:9 → downscale → filter → GPU upload.

        Throttled: GPU upload every 3 frames; between updates, cached
        image is blitted (pure GPU texture draw, near-zero cost).
        """
        w, h = py5.width, py5.height
        canvas_aspect = w / h  # ~1.778 (16:9)

        update_now = (self._draw_count % self.UPDATE_EVERY_N == 0
                      or self._cached_img is None
                      or self._last_display_w != w
                      or self._last_display_h != h)
        self._draw_count += 1

        if update_now and camera_tracker is not None:
            raw = camera_tracker.get_frame()
            if raw is not None:
                try:
                    # ── Center-crop raw 4:3 → 16:9 ─────────────
                    raw_h, raw_w = raw.shape[:2]
                    raw_aspect = raw_w / raw_h
                    if raw_aspect > canvas_aspect:
                        # Raw wider than canvas — crop sides
                        new_w = int(raw_h * canvas_aspect)
                        sx = (raw_w - new_w) // 2
                        cropped = raw[:, sx:sx + new_w]
                    else:
                        # Raw taller than canvas — crop top/bottom
                        new_h = int(raw_w / canvas_aspect)
                        sy = (raw_h - new_h) // 2
                        cropped = raw[sy:sy + new_h, :]

                    # ── Downscale → filter → GPU upload ─────────
                    small = cv2.resize(cropped, (self.PROCESS_W, self.PROCESS_H),
                                       interpolation=cv2.INTER_AREA)
                    rgb = FilterManager.apply(small, self.filter_name)
                    self._cached_img = py5.create_image_from_numpy(rgb, "RGB")
                    self._last_display_w = w
                    self._last_display_h = h
                except Exception:
                    self._cached_img = None

        # ── Blit cached image (every frame, GPU-only) ──
        if self._cached_img is not None:
            py5.image(self._cached_img, 0, 0, w, h)
