"""
DLA (Diffusion Limited Aggregation) growth engine.

Produces organic dendritic branching structures through random walk
and sticking. Each frame releases a small number of walkers that
random-walk until they touch the existing cluster, then stick.

Design:
    - Spatial hash grid for O(1) collision detection
    - Configurable walkers/frame for performance control
    - Returns new growth points each frame for incremental rendering
"""

import math
import random
from typing import Optional, Set, Tuple

from config import Config


class DLAEngine:
    """Diffusion Limited Aggregation growth engine.

    Manages a growing cluster of stuck particles. Each frame,
    walkers are released from the cluster boundary, random-walk,
    and stick on contact.

    The cluster naturally forms fractal dendritic patterns —
    no two growths are identical.

    Public interface:
        update(n_walkers, max_steps) → list of new stuck points
        display(py5) — render the cluster
        serialize()/deserialize()
    """

    def __init__(
        self,
        center_x: float,
        center_y: float,
        max_radius: float = Config.DLA_MAX_RADIUS,
        stick_radius: float = Config.DLA_STICK_RADIUS,
    ) -> None:
        """Initialize DLA engine with a seed point at center.

        Args:
            center_x, center_y: Cluster origin in pixels.
            max_radius: Maximum cluster radius.
            stick_radius: Contact distance for sticking.
        """
        self.center_x = center_x
        self.center_y = center_y
        self.max_radius = max_radius
        self.stick_radius = stick_radius

        # Grid cell size for spatial hash
        self._cell_size = stick_radius * 2.0

        # All stuck points: list of (x, y)
        self.points: list[Tuple[float, float]] = [(center_x, center_y)]

        # Spatial hash: grid_cell → set of point indices
        self._grid: dict[Tuple[int, int], set[int]] = {}
        self._add_to_grid(0, center_x, center_y)

        # Current cluster radius (max distance from center)
        self.current_radius: float = 0.0

    # ============================================================
    # Spatial Hash
    # ============================================================

    def _cell(self, x: float, y: float) -> Tuple[int, int]:
        """Get grid cell coordinates for a position."""
        return (int(x / self._cell_size), int(y / self._cell_size))

    def _add_to_grid(self, idx: int, x: float, y: float) -> None:
        """Register a stuck point in the spatial hash."""
        cell = self._cell(x, y)
        if cell not in self._grid:
            self._grid[cell] = set()
        self._grid[cell].add(idx)

    def _check_collision(self, wx: float, wy: float) -> bool:
        """Check if a walker position touches any stuck point.

        Only checks the walker's grid cell and 8 neighbors.

        Args:
            wx, wy: Walker position.

        Returns:
            True if within stick_radius of any stuck point.
        """
        cell = self._cell(wx, wy)
        sr2 = self.stick_radius * self.stick_radius

        # Check 3×3 neighborhood
        for dcx in (-1, 0, 1):
            for dcy in (-1, 0, 1):
                nc = (cell[0] + dcx, cell[1] + dcy)
                if nc not in self._grid:
                    continue
                for idx in self._grid[nc]:
                    px, py = self.points[idx]
                    dx = wx - px
                    dy = wy - py
                    if dx * dx + dy * dy < sr2:
                        return True
        return False

    # ============================================================
    # Growth
    # ============================================================

    def update(
        self,
        n_walkers: int = Config.DLA_WALKERS_PER_FRAME,
        max_steps: int = Config.DLA_MAX_STEPS,
    ) -> list[Tuple[float, float]]:
        """Run one frame of DLA growth.

        Releases walkers from the cluster boundary. Each walker
        random-walks until it sticks or dies (too far).

        Args:
            n_walkers: Number of walkers to release this frame.
            max_steps: Max random-walk steps before walker dies.

        Returns:
            List of (x, y) tuples for newly stuck points this frame.
        """
        new_points: list[Tuple[float, float]] = []
        spawn_r = max(self.stick_radius * 3, self.current_radius + Config.DLA_SPAWN_MARGIN)
        step_size = self.stick_radius * 0.8
        max_r2 = self.max_radius * self.max_radius

        for _ in range(n_walkers):
            # Spawn at random angle on the spawn ring
            angle = random.uniform(0, math.pi * 2.0)
            wx = self.center_x + math.cos(angle) * spawn_r
            wy = self.center_y + math.sin(angle) * spawn_r

            stuck = False
            for _step in range(max_steps):
                # Random walk step
                sa = random.uniform(0, math.pi * 2.0)
                wx += math.cos(sa) * step_size
                wy += math.sin(sa) * step_size

                # Die if too far from center
                dx = wx - self.center_x
                dy = wy - self.center_y
                if dx * dx + dy * dy > max_r2:
                    break

                # Check collision
                if self._check_collision(wx, wy):
                    stuck = True
                    break

            if stuck:
                idx = len(self.points)
                self.points.append((wx, wy))
                self._add_to_grid(idx, wx, wy)
                new_points.append((wx, wy))

                # Update cluster radius
                dx = wx - self.center_x
                dy = wy - self.center_y
                dist = math.sqrt(dx * dx + dy * dy)
                if dist > self.current_radius:
                    self.current_radius = dist

        return new_points

    # ============================================================
    # Display
    # ============================================================

    def display(self, py5, color_growth: tuple, color_core: tuple) -> None:
        """Render the DLA cluster as connected glowing dots.

        Points near center = deep blue (old).
        Points near edge = white (new growth).
        Each point has a soft glow for visibility.

        Args:
            py5: The py5 sketch module.
            color_growth: (r, g, b) for outer/new growth.
            color_core: (r, g, b) for inner/old core.
        """
        if len(self.points) < 2:
            return

        max_r = max(1.0, self.current_radius)
        dot_r = max(2.0, self.stick_radius * 1.2)

        # Outer glow pass — larger, softer circles
        for px, py in self.points:
            dx = px - self.center_x
            dy = py - self.center_y
            dist = math.sqrt(dx * dx + dy * dy)
            t = min(1.0, dist / max_r)

            r = int(color_core[0] + (color_growth[0] - color_core[0]) * t)
            g = int(color_core[1] + (color_growth[1] - color_core[1]) * t)
            b = int(color_core[2] + (color_growth[2] - color_core[2]) * t)

            py5.no_stroke()
            py5.fill(r, g, b, 60.0 + 40.0 * t)  # Outer glow
            py5.circle(px, py, dot_r * 3.0)

        # Core pass — brighter centers
        for px, py in self.points:
            dx = px - self.center_x
            dy = py - self.center_y
            dist = math.sqrt(dx * dx + dy * dy)
            t = min(1.0, dist / max_r)

            r = min(255, int(color_core[0] + (color_growth[0] - color_core[0]) * t + 40))
            g = min(255, int(color_core[1] + (color_growth[1] - color_core[1]) * t + 40))
            b = min(255, int(color_core[2] + (color_growth[2] - color_core[2]) * t + 40))

            py5.no_stroke()
            py5.fill(r, g, b, 200.0)  # Bright core
            py5.circle(px, py, dot_r)

    # ============================================================
    # Serialization
    # ============================================================

    def serialize(self) -> dict:
        """Convert growth state to JSON-serializable dict.

        Only saves points, not the grid (grid is rebuilt on deserialize).
        """
        return {
            "center_x": self.center_x,
            "center_y": self.center_y,
            "max_radius": self.max_radius,
            "stick_radius": self.stick_radius,
            "points": list(self.points),
            "current_radius": self.current_radius,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "DLAEngine":
        """Rebuild DLA engine from serialized data.

        Reconstructs the spatial hash grid from saved points.
        """
        engine = cls(
            center_x=data["center_x"],
            center_y=data["center_y"],
            max_radius=data.get("max_radius", Config.DLA_MAX_RADIUS),
            stick_radius=data.get("stick_radius", Config.DLA_STICK_RADIUS),
        )
        engine.points = [tuple(p) for p in data["points"]]
        engine.current_radius = data.get("current_radius", 0.0)

        # Rebuild grid
        engine._grid = {}
        for idx, (px, py) in enumerate(engine.points):
            engine._add_to_grid(idx, px, py)

        return engine

    # ============================================================
    # Info
    # ============================================================

    def point_count(self) -> int:
        """Total stuck points in the cluster."""
        return len(self.points)

    def is_complete(self) -> bool:
        """True when cluster has reached max radius."""
        return self.current_radius >= self.max_radius * 0.95
