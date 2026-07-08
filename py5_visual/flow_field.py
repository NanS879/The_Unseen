"""
Flow field using Perlin noise for organic particle movement.

A 2D grid of angle vectors is populated each frame using 3D Perlin noise
(x, y, time). Bilinear interpolation ensures smooth trajectories between
grid cells.

V2 additions:
- enabled toggle for debugging
- get_force() as the canonical public interface
- Parameters aligned with Config
"""

import math
from typing import Optional

import py5

from config import Config


class FlowField:
    """A noise-driven 2D vector field for natural particle drift.

    The field is sampled from py5.noise() in 3D: (col * ns, row * ns, time).
    The time dimension creates smooth animation over frames.

    Public interface:
        update(time)    — recalculate all flow vectors
        get_force(x, y) — interpolated force at arbitrary position
        toggle()        — enable/disable the field
    """

    def __init__(
        self,
        width: int = Config.WIDTH,
        height: int = Config.HEIGHT,
        cell_size: int = Config.FLOW_CELL_SIZE,
        noise_scale: float = Config.FLOW_NOISE_SCALE,
        time_scale: float = Config.FLOW_NOISE_SPEED,
        flow_strength: float = Config.FLOW_STRENGTH,
        enabled: bool = Config.FLOW_ENABLED,
    ) -> None:
        """Initialize the flow field grid.

        Args:
            width: Canvas width in pixels.
            height: Canvas height in pixels.
            cell_size: Grid cell size in pixels. Smaller = finer detail
                but more computation.
            noise_scale: Spatial frequency of the noise. Smaller = larger
                swirls, larger = more chaotic.
            time_scale: Temporal evolution rate. Smaller = slower evolution.
            flow_strength: Base magnitude of flow vectors (0.0–1.0).
            enabled: Whether the flow field is active.
        """
        self.cell_size = cell_size
        self.cols = int(width / cell_size) + 1
        self.rows = int(height / cell_size) + 1
        self.noise_scale = noise_scale
        self.time_scale = time_scale
        self.flow_strength = flow_strength
        self.enabled = enabled

        # Grid of (vx, vy) tuples
        self._field: list[tuple[float, float]] = [
            (0.0, 0.0)
        ] * (self.cols * self.rows)

    def update(self, time: float) -> None:
        """Recalculate all flow vectors for the given time.

        When disabled, this is a no-op — the field remains at its last
        computed state.

        Args:
            time: Monotonic time value in seconds
                (e.g., py5.millis() / 1000.0).
        """
        if not self.enabled:
            return

        ns = self.noise_scale
        ts = self.time_scale

        for row in range(self.rows):
            for col in range(self.cols):
                idx = row * self.cols + col
                # Sample 3D Perlin noise; py5.noise() returns 0.0–1.0
                noise_val = py5.noise(
                    col * self.cell_size * ns,
                    row * self.cell_size * ns,
                    time * ts,
                )
                # Map to angle in radians [0, 2π]
                angle = noise_val * math.pi * 2.0
                vx = math.cos(angle) * self.flow_strength
                vy = math.sin(angle) * self.flow_strength
                self._field[idx] = (vx, vy)

    def get_force(self, x: float, y: float) -> tuple[float, float]:
        """Get the flow force vector at an arbitrary position.

        Canonical public interface. When the field is disabled, returns
        zero force. Uses bilinear interpolation between the four nearest
        grid cells for smooth, continuous trajectories.

        Args:
            x: X position in pixels.
            y: Y position in pixels.

        Returns:
            (vx, vy) interpolated flow vector, or (0.0, 0.0) if disabled.
        """
        if not self.enabled:
            return (0.0, 0.0)

        return self._lookup(x, y)

    def _lookup(self, x: float, y: float) -> tuple[float, float]:
        """Bilinear interpolation of flow vectors at (x, y).

        Internal implementation — use get_force() as the public API.
        """
        cs = self.cell_size

        # Clamp to grid bounds
        col_f = max(0.0, min(float(self.cols - 1.001), x / cs))
        row_f = max(0.0, min(float(self.rows - 1.001), y / cs))

        col0 = int(col_f)
        row0 = int(row_f)
        col1 = min(col0 + 1, self.cols - 1)
        row1 = min(row0 + 1, self.rows - 1)

        # Fractional offsets
        fx = col_f - col0
        fy = row_f - row0

        # Four corner vectors
        v00 = self._get(col0, row0)
        v10 = self._get(col1, row0)
        v01 = self._get(col0, row1)
        v11 = self._get(col1, row1)

        # Bilinear interpolation
        vx = (
            v00[0] * (1 - fx) * (1 - fy)
            + v10[0] * fx * (1 - fy)
            + v01[0] * (1 - fx) * fy
            + v11[0] * fx * fy
        )
        vy = (
            v00[1] * (1 - fx) * (1 - fy)
            + v10[1] * fx * (1 - fy)
            + v01[1] * (1 - fx) * fy
            + v11[1] * fx * fy
        )

        return (vx, vy)

    def _get(self, col: int, row: int) -> tuple[float, float]:
        """Get the flow vector at a specific grid cell."""
        return self._field[row * self.cols + col]

    # ---- Backward compatibility ----
    def lookup(self, x: float, y: float) -> tuple[float, float]:
        """Deprecated alias for get_force(). Kept for backward compatibility."""
        return self.get_force(x, y)

    # ---- Debug ----
    def toggle(self) -> bool:
        """Toggle the flow field on/off. Returns new state."""
        self.enabled = not self.enabled
        return self.enabled
