"""
V6 Procedural Background — noise-driven nebula atmosphere.

Replaces flat black background with a slowly evolving ambient field.
Uses layered Perlin noise sampling to create a soft, volumetric feel.
Low frequency — doesn't compete with particles.

Rendered once every ~15 frames (throttled) for performance.
"""

import math

from ..config import Config
from ..utils.easing import smoothstep


class ProceduralBackground:
    """Noise-driven ambient background with state-responsive color.

    Draws semi-transparent gradient layers based on current space state,
    creating a soft nebula/atmosphere effect that breathes with the space.
    """

    def __init__(self) -> None:
        self._time: float = 0.0
        self._last_drawn: int = -100
        self._noise_seed: float = 0.0

    def update(self, dt: float) -> None:
        """Advance background time. Very slow evolution."""
        self._time += dt * 0.3

    def draw(self, py5, state: str) -> None:
        """Draw the procedural background.

        Base ambient layer drawn every frame. Decorative gradient
        circles throttled to every 15 frames for performance.

        Args:
            py5: py5 sketch.
            state: Current SpaceState name (IDLE/ACTIVE/EXCITED/CALM).
        """
        theme = Config.Palette.Theme.get(state)
        ar, ag, ab = theme["ambient"]
        pr, pg, pb = theme["primary"]

        w, h = py5.width, py5.height
        py5.no_stroke()

        # Base layer: always drawn — solid ambient fill
        py5.fill(ar, ag, ab, 255)
        py5.rect(0, 0, w, h)

        # Decorative gradient: throttled to every 15 frames
        if abs(py5.frame_count - self._last_drawn) < 15:
            return
        self._last_drawn = py5.frame_count
        cx, cy = w / 2, h / 2
        max_r = math.sqrt(cx * cx + cy * cy)
        step_count = 20

        for i in range(step_count):
            t = i / step_count
            r = max_r * (0.3 + t * 0.7)
            # Fade from center outward
            alpha = 4.0 * (1.0 - smoothstep(t))
            # Slight noise variation for organic feel
            noise_val = py5.noise(
                (cx + math.cos(t * 6.28) * 200) * 0.003,
                (cy + math.sin(t * 6.28) * 200) * 0.003,
                self._time * 0.1,
            )
            alpha *= 0.5 + noise_val * 0.5

            # Blend ambient → primary based on distance from center
            r_t = smoothstep(t)
            cr = int(ar + (pr - ar) * r_t * 0.4)
            cg = int(ag + (pg - ag) * r_t * 0.4)
            cb = int(ab + (pb - ab) * r_t * 0.4)
            py5.fill(cr, cg, cb, alpha)
            py5.circle(cx, cy, r * 2)
