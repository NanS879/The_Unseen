"""
Particle with full lifecycle, motion trail, and glow rendering.

Each particle progresses through distinct life stages:
    birth → growth → peak → decay → death → respawn

Opacity and size are computed from the current life stage for smooth
transitions. A polyline motion trail creates the sense of flow.

V2 Perf: Reduced glow layers, batched trail rendering, point() for core.
"""

import math
import random
from collections import deque
from typing import Optional

from config import Config


class Particle:
    """A glowing particle with lifecycle, motion trail, and physics.

    Lifecycle stages (based on age/life ratio):
        0.00–0.10  birth   — fade in, small size
        0.10–0.30  growth  — size/opacity increase to peak
        0.30–0.70  peak    — full size and opacity
        0.70–1.00  decay   — shrink, fade out
        1.00+       dead    — ready for respawn
    """

    LAYER_BG = "background"
    LAYER_INT = "interaction"
    LAYER_HL = "highlight"

    def __init__(
        self,
        width: int,
        height: int,
        layer: str = LAYER_INT,
        max_speed: float = 3.5,
        damping: float = 0.95,
        size_min: float = 1.5,
        size_max: float = 4.0,
        life_min: float = 200,
        life_max: float = 400,
        trail_length: int = 12,
        glow_layers: int = 3,
        color_base: tuple[int, int, int] = Config.Palette.INT_BASE,
        color_glow: tuple[int, int, int] = Config.Palette.INT_GLOW,
    ) -> None:
        """Create a particle with configurable layer parameters.

        Args:
            width, height: Canvas dimensions in pixels.
            layer: Layer identifier (LAYER_BG, LAYER_INT, LAYER_HL).
            max_speed: Maximum velocity magnitude.
            damping: Velocity multiplier per frame (0–1).
            size_min, size_max: Base radius range.
            life_min, life_max: Lifespan range in frames.
            trail_length: Max trail history (0 = no trail).
            glow_layers: Number of glow circles (2 or 3).
            color_base: Base (r, g, b) for this layer.
            color_glow: Glow (r, g, b) for this layer.
        """
        self.width = width
        self.height = height
        self.layer = layer

        # Physics
        self.max_speed = max_speed
        self.damping = damping

        # Visual
        self.size_min = size_min
        self.size_max = size_max
        self.base_size = random.uniform(size_min, size_max)
        self.color_base = color_base
        self.color_glow = color_glow
        self.glow_layers = glow_layers  # 2 or 3
        self.draw_trail = trail_length > 0

        # Lifecycle
        self.age: float = 0.0
        self.life: float = random.uniform(life_min, life_max)

        # Position & motion
        self.position: list[float] = [
            random.uniform(0, width),
            random.uniform(0, height),
        ]
        self.velocity: list[float] = [0.0, 0.0]
        self.acceleration: list[float] = [0.0, 0.0]
        self.current_speed: float = 0.0

        # Trail
        self._trail: deque[tuple[float, float]] = deque(
            [(self.position[0], self.position[1])],
            maxlen=max(1, trail_length),
        )

    # ============================================================
    # Physics
    # ============================================================

    def apply_force(self, fx: float, fy: float) -> None:
        """Accumulate a force vector."""
        self.acceleration[0] += fx
        self.acceleration[1] += fy

    def update(self) -> None:
        """Integrate physics and advance lifecycle by one frame."""
        # Integrate acceleration
        self.velocity[0] += self.acceleration[0]
        self.velocity[1] += self.acceleration[1]

        # Damping
        self.velocity[0] *= self.damping
        self.velocity[1] *= self.damping

        # Clamp speed (use squares to avoid sqrt when under limit)
        sp2 = self.velocity[0] ** 2 + self.velocity[1] ** 2
        max2 = self.max_speed ** 2
        if sp2 > max2:
            scale = self.max_speed / math.sqrt(sp2)
            self.velocity[0] *= scale
            self.velocity[1] *= scale
            self.current_speed = self.max_speed
        else:
            self.current_speed = math.sqrt(sp2)

        # Apply velocity
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]

        # Reset acceleration
        self.acceleration[0] = 0.0
        self.acceleration[1] = 0.0

        # Lifecycle
        self.age += 1.0

        # Trail
        if self.draw_trail:
            self._trail.append((self.position[0], self.position[1]))

        # Wrap edges
        self._wrap()

    def _wrap(self) -> None:
        """Wrap around canvas edges."""
        m = 10.0
        if self.position[0] < -m:
            self.position[0] = self.width + m
        if self.position[0] > self.width + m:
            self.position[0] = -m
        if self.position[1] < -m:
            self.position[1] = self.height + m
        if self.position[1] > self.height + m:
            self.position[1] = -m

    # ============================================================
    # Lifecycle
    # ============================================================

    def life_ratio(self) -> float:
        """Life progress: 0.0 (birth) → 1.0 (death)."""
        if self.life <= 0:
            return 1.0
        return max(0.0, min(1.0, self.age / self.life))

    def life_stage(self) -> str:
        """Current lifecycle stage."""
        r = self.life_ratio()
        if r >= 1.0:
            return "dead"
        if r < Config.LIFECYCLE_BIRTH_RATIO:
            return "birth"
        if r < Config.LIFECYCLE_GROWTH_RATIO:
            return "growth"
        if r < Config.LIFECYCLE_PEAK_RATIO:
            return "peak"
        return "decay"

    def is_dead(self) -> bool:
        return self.age >= self.life

    def current_opacity(self, influence: float = 0.0) -> float:
        """Opacity 0–255 based on life stage."""
        stage = self.life_stage()
        r = self.life_ratio()
        if stage == "dead":
            return 0.0
        if stage == "birth":
            return (r / Config.LIFECYCLE_BIRTH_RATIO) * 255.0
        if stage in ("growth", "peak"):
            return 255.0
        # decay
        t = (r - Config.LIFECYCLE_PEAK_RATIO) / (1.0 - Config.LIFECYCLE_PEAK_RATIO)
        return (1.0 - t) * 255.0

    def current_size(self) -> float:
        """Dynamic radius based on life stage."""
        stage = self.life_stage()
        r = self.life_ratio()
        if stage == "dead":
            return 0.0
        if stage == "birth":
            t = r / Config.LIFECYCLE_BIRTH_RATIO
            return self.base_size * (0.3 + 0.7 * t)
        if stage == "growth":
            t = (r - Config.LIFECYCLE_BIRTH_RATIO) / (
                Config.LIFECYCLE_GROWTH_RATIO - Config.LIFECYCLE_BIRTH_RATIO
            )
            return self.base_size * (1.0 + 0.15 * math.sin(t * math.pi))
        if stage == "peak":
            return self.base_size
        # decay
        t = (r - Config.LIFECYCLE_PEAK_RATIO) / (1.0 - Config.LIFECYCLE_PEAK_RATIO)
        return self.base_size * (1.0 - 0.7 * t)

    def respawn(self) -> None:
        """Reset to random position with full life."""
        if random.random() < 0.3:
            edge = random.randint(0, 3)
            if edge == 0:
                self.position[0] = random.uniform(0, self.width)
                self.position[1] = -10
            elif edge == 1:
                self.position[0] = random.uniform(0, self.width)
                self.position[1] = self.height + 10
            elif edge == 2:
                self.position[0] = -10
                self.position[1] = random.uniform(0, self.height)
            else:
                self.position[0] = self.width + 10
                self.position[1] = random.uniform(0, self.height)
        else:
            self.position[0] = random.uniform(0, self.width)
            self.position[1] = random.uniform(0, self.height)

        self.velocity = [0.0, 0.0]
        self.acceleration = [0.0, 0.0]
        self.age = 0.0
        self.base_size = random.uniform(self.size_min, self.size_max)
        self._trail.clear()
        self._trail.append((self.position[0], self.position[1]))

    # ============================================================
    # Rendering
    # ============================================================

    def display(
        self, py5, influence: float = 0.0, trail_mult: float = 1.0
    ) -> None:
        """Render particle with glow and optional trail.

        Args:
            py5: The py5 sketch module.
            influence: Hand proximity 0–1 for brightness boost.
            trail_mult: State-driven trail length multiplier.
        """
        opacity = self.current_opacity(influence)
        if opacity < 1.0:
            return

        size = self.current_size()
        if size < 0.2:
            return

        # Trail
        if self.draw_trail:
            self._draw_trail(py5, opacity, trail_mult)

        # Glow
        self._draw_glow(py5, self.position[0], self.position[1],
                        size, opacity, influence)

    def _draw_trail(self, py5, opacity: float, trail_mult: float) -> None:
        """Draw motion trail as a fading polyline.

        Perf: Single continuous shape instead of per-segment line() calls.
        Alpha is uniform across the trail (average of head/tail) to avoid
        per-segment state changes.
        """
        n = len(self._trail)
        if n < 2:
            return

        # Dynamic trail length from speed
        sf = min(1.0, self.current_speed / max(0.01, self.max_speed))
        effective_n = max(2, int(n * (0.3 + 0.7 * sf) * trail_mult))

        # Get the most recent points without allocating a new list
        # deque doesn't support slicing, so convert just the needed suffix
        all_pts = list(self._trail)
        if len(all_pts) > effective_n:
            pts = all_pts[-effective_n:]
        else:
            pts = all_pts

        if len(pts) < 2:
            return

        # Single alpha for the whole trail — avoids per-segment stroke() calls
        trail_alpha = opacity * 0.25 * trail_mult
        if trail_alpha < 1.5:
            return

        cr, cg, cb = self.color_glow
        weight = max(0.5, self.base_size * 0.4)

        py5.no_fill()
        py5.stroke(cr, cg, cb, trail_alpha)
        py5.stroke_weight(weight)
        py5.stroke_cap(py5.ROUND)
        py5.stroke_join(py5.ROUND)

        # Batch draw: single begin_shape / end_shape
        with py5.begin_shape():
            for px, py in pts:
                py5.vertex(px, py)

    def _draw_glow(self, py5, x: float, y: float, r: float,
                   opacity: float, influence: float) -> None:
        """Draw concentric glow circles.

        Perf: 3 layers max (down from 4). Hot center uses point() instead
        of circle() for 0.5px radius core.

        Args:
            py5: py5 sketch.
            x, y: Center position.
            r: Current radius.
            opacity: 0–255.
            influence: Hand proximity boost 0–1.
        """
        cr, cg, cb = self.color_glow
        boost = 1.0 + influence * 0.5
        o = opacity / 255.0

        py5.no_stroke()

        if self.glow_layers >= 3:
            # Outer soft halo (was r*6, now r*4 — smaller = less GPU fill)
            py5.fill(cr, cg, cb, 15.0 * o * boost)
            py5.circle(x, y, r * 4.5)

        # Mid glow
        py5.fill(cr, cg, cb, 55.0 * o * boost)
        py5.circle(x, y, r * 2.5)

        # Inner core
        py5.fill(cr, cg, cb, 170.0 * o * boost)
        py5.circle(x, y, r * 1.1)

        # Hot center — use point() instead of tiny circle (much cheaper!)
        py5.stroke(255, 255, 255, 230.0 * o * boost)
        py5.stroke_weight(r * 0.6)
        py5.point(x, y)
