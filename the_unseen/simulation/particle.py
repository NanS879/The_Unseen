"""
Particle with full lifecycle and minimal glow rendering.

Life stages: birth → growth → peak → decay → death → respawn
Opacity and size are computed via smoothstep easing for natural feel.

V3.5: Removed trail code (cleaner, faster). Simplified rendering.
"""

import math
import random

from ..config import Config
from ..utils.easing import smoothstep


class Particle:
    """A glowing particle with lifecycle and physics.

    Lifecycle (age/life ratio):
        0.00–0.10  birth  — fade in, small → growing
        0.10–0.30  growth — approach peak
        0.30–0.70  peak   — full size and opacity
        0.70–1.00  decay  — shrink, fade out
        1.00+       dead   — ready for respawn
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
        glow_layers: int = 2,
        color_base: tuple[int, int, int] = Config.Palette.INT_BASE,
        color_glow: tuple[int, int, int] = Config.Palette.INT_GLOW,
    ) -> None:
        """Create a particle.

        Args:
            width, height: Canvas dimensions.
            layer: LAYER_BG / LAYER_INT / LAYER_HL.
            max_speed: Velocity cap.
            damping: Friction per frame (0–1).
            size_min, size_max: Base radius range.
            life_min, life_max: Lifespan range in frames.
            trail_length: Deprecated (V3.5: ignored).
            glow_layers: 1 or 2 glow circles.
            color_base, color_glow: Layer colors from Palette.
        """
        self.width = width
        self.height = height
        self.layer = layer
        self.max_speed = max_speed
        self.damping = damping
        self.size_min = size_min
        self.size_max = size_max
        self.base_size = random.uniform(size_min, size_max)
        self.color_base = color_base
        self.color_glow = color_glow
        self.glow_layers = glow_layers

        self.age: float = 0.0
        self.life: float = random.uniform(life_min, life_max)

        self.position: list[float] = [
            random.uniform(0, width),
            random.uniform(0, height),
        ]
        self.velocity: list[float] = [0.0, 0.0]
        self.acceleration: list[float] = [0.0, 0.0]
        self.current_speed: float = 0.0

    # ============================================================
    # Physics
    # ============================================================

    def apply_force(self, fx: float, fy: float) -> None:
        self.acceleration[0] += fx
        self.acceleration[1] += fy

    def update(self) -> None:
        """Integrate physics, advance age, wrap edges."""
        self.velocity[0] += self.acceleration[0]
        self.velocity[1] += self.acceleration[1]
        self.velocity[0] *= self.damping
        self.velocity[1] *= self.damping

        sp2 = self.velocity[0] ** 2 + self.velocity[1] ** 2
        max2 = self.max_speed ** 2
        if sp2 > max2:
            scale = self.max_speed / math.sqrt(sp2)
            self.velocity[0] *= scale
            self.velocity[1] *= scale
            self.current_speed = self.max_speed
        else:
            self.current_speed = math.sqrt(sp2)

        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]
        self.acceleration[0] = 0.0
        self.acceleration[1] = 0.0
        self.age += 1.0
        self._wrap()

    def _wrap(self) -> None:
        m = 10.0
        w, h = self.width, self.height
        if self.position[0] < -m:   self.position[0] = w + m
        if self.position[0] > w + m: self.position[0] = -m
        if self.position[1] < -m:    self.position[1] = h + m
        if self.position[1] > h + m: self.position[1] = -m

    # ============================================================
    # Lifecycle
    # ============================================================

    def life_ratio(self) -> float:
        if self.life <= 0:
            return 1.0
        return max(0.0, min(1.0, self.age / self.life))

    def life_stage(self) -> str:
        r = self.life_ratio()
        if r >= 1.0:                                       return "dead"
        if r < Config.LIFECYCLE_BIRTH_RATIO:               return "birth"
        if r < Config.LIFECYCLE_GROWTH_RATIO:              return "growth"
        if r < Config.LIFECYCLE_PEAK_RATIO:                return "peak"
        return "decay"

    def is_dead(self) -> bool:
        return self.age >= self.life

    def current_opacity(self, influence: float = 0.0) -> float:
        """Opacity 0–255 with smoothstep transitions."""
        stage = self.life_stage()
        r = self.life_ratio()
        if stage == "dead":
            return 0.0
        if stage == "birth":
            t = smoothstep(r / Config.LIFECYCLE_BIRTH_RATIO)
            return t * 255.0
        if stage in ("growth", "peak"):
            return 255.0
        # decay
        t = (r - Config.LIFECYCLE_PEAK_RATIO) / (1.0 - Config.LIFECYCLE_PEAK_RATIO)
        return (1.0 - smoothstep(t)) * 255.0

    def current_size(self) -> float:
        """Dynamic radius with smoothstep."""
        stage = self.life_stage()
        r = self.life_ratio()
        if stage == "dead":
            return 0.0
        if stage == "birth":
            t = smoothstep(r / Config.LIFECYCLE_BIRTH_RATIO)
            return self.base_size * (0.3 + 0.7 * t)
        if stage == "growth":
            t = (r - Config.LIFECYCLE_BIRTH_RATIO) / (
                Config.LIFECYCLE_GROWTH_RATIO - Config.LIFECYCLE_BIRTH_RATIO
            )
            return self.base_size * (1.0 + 0.1 * math.sin(smoothstep(t) * math.pi))
        if stage == "peak":
            return self.base_size
        # decay
        t = (r - Config.LIFECYCLE_PEAK_RATIO) / (1.0 - Config.LIFECYCLE_PEAK_RATIO)
        return self.base_size * (1.0 - 0.7 * smoothstep(t))

    def respawn(self) -> None:
        """Reset particle to random position with full life."""
        if random.random() < 0.3:
            edge = random.randint(0, 3)
            w, h = self.width, self.height
            if edge == 0:
                self.position[0] = random.uniform(0, w)
                self.position[1] = -10
            elif edge == 1:
                self.position[0] = random.uniform(0, w)
                self.position[1] = h + 10
            elif edge == 2:
                self.position[0] = -10
                self.position[1] = random.uniform(0, h)
            else:
                self.position[0] = w + 10
                self.position[1] = random.uniform(0, h)
        else:
            self.position[0] = random.uniform(0, self.width)
            self.position[1] = random.uniform(0, self.height)

        self.velocity = [0.0, 0.0]
        self.acceleration = [0.0, 0.0]
        self.age = 0.0
        self.base_size = random.uniform(self.size_min, self.size_max)

    # ============================================================
    # Rendering
    # ============================================================

    def display(self, py5, influence: float = 0.0) -> None:
        """Render particle glow."""
        opacity = self.current_opacity(influence)
        if opacity < 1.0:
            return
        size = self.current_size()
        if size < 0.2:
            return
        self._draw_glow(py5, self.position[0], self.position[1],
                        size, opacity, influence)

    def _draw_glow(self, py5, x: float, y: float, r: float,
                   opacity: float, influence: float) -> None:
        """Draw 1 soft glow circle + hot center point. Optimized for GPU."""
        cr, cg, cb = self.color_glow
        boost = 1.0 + influence * 0.4
        o = opacity / 255.0

        # Single glow circle
        py5.no_stroke()
        py5.fill(cr, cg, cb, 80.0 * o * boost)
        py5.circle(x, y, r * 2.5)

        # Hot center — point() is the cheapest GPU draw call
        py5.stroke(255, 255, 255, min(255, 220.0 * o * boost))
        py5.stroke_weight(max(0.5, r * 0.6))
        py5.point(x, y)
