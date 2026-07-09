"""
HandState: smoothed hand position/speed with EMA filtering.

V4: OSC removed. HandState receives data directly from CameraTracker,
not via network. Threading and locks are no longer needed.
"""

from ..config import Config


class HandState:
    """Smoothed state for a single tracked hand.

    Camera data is smoothed with exponential moving average (EMA)
    to eliminate jitter while maintaining responsiveness.

    V4: No OSC — data comes directly from CameraTracker.update().
    """

    def __init__(self, side: str, default_x: float, default_y: float) -> None:
        self.side = side
        self.default_x = default_x
        self.default_y = default_y

        # Raw camera data (updated from CameraTracker)
        self.raw_x: float = 0.0
        self.raw_y: float = 0.0
        self.raw_speed: float = 0.0
        self.detected: bool = False
        self.has_data: bool = False

        # Smoothed pixel-space values
        self.px: float = default_x
        self.py: float = default_y
        self.speed: float = 0.0
        self.dx: float = 0.0
        self.dy: float = 0.0

    def update_smoothing(
        self,
        alpha: float,
        target_px: float,
        target_py: float,
        target_speed: float,
    ) -> None:
        """Advance EMA smoothing by one step.

        Args:
            alpha: Smoothing factor (0–1). Higher = faster response.
            target_px, target_py: Target position in pixels.
            target_speed: Target speed value.
        """
        prev_px, prev_py = self.px, self.py
        self.px += (target_px - self.px) * alpha
        self.py += (target_py - self.py) * alpha
        self.speed += (target_speed - self.speed) * alpha
        self.dx = self.px - prev_px
        self.dy = self.py - prev_py
