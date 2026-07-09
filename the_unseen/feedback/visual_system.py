"""
V6 Visual System — unified depth, lighting, camera, and particle variety.

All visual behavior driven by Config.Palette.Theme.get(state).
No hardcoded RGB values. Smooth transitions via easing.

Components:
    DepthManager    — 3-layer parallax + density
    VarietyRenderer — particle shape variety (stardust, fiber, glow)
    BreathingCamera — subtle camera drift + scale oscillation
    StateLighting   — theme-driven ambient + highlight modulation
"""

import math
import random

from ..config import Config
from ..utils.easing import smoothstep


# ============================================================
# Depth Manager — 3-layer spatial depth
# ============================================================

class DepthManager:
    """Controls per-layer depth parameters: scale, alpha, density.

    Foreground (HL): largest, brightest, fastest parallax
    Midground (INT): medium everything
    Background (BG): smallest, dimmest, slowest parallax
    """

    def __init__(self) -> None:
        # Per-layer depth factors
        self._depth = {
            "background":   {"scale": 0.7,  "alpha": 0.4,  "parallax": 0.2},
            "interaction":  {"scale": 1.0,  "alpha": 0.7,  "parallax": 0.6},
            "highlight":    {"scale": 1.4,  "alpha": 1.0,  "parallax": 1.0},
        }

    def parallax_offset(self, layer: str, hand_x: float, hand_y: float,
                        cx: float, cy: float) -> tuple[float, float]:
        """Compute parallax offset for a particle layer.

        Foreground layers shift more relative to hand position,
        creating depth illusion.

        Args:
            layer: "background", "interaction", or "highlight".
            hand_x, hand_y: Hand position.
            cx, cy: Canvas center.

        Returns:
            (dx, dy) offset in pixels.
        """
        d = self._depth.get(layer, self._depth["interaction"])
        factor = d["parallax"]
        dx = (hand_x - cx) * factor * 0.1
        dy = (hand_y - cy) * factor * 0.1
        return (dx, dy)

    def alpha_factor(self, layer: str) -> float:
        d = self._depth.get(layer, self._depth["interaction"])
        return d["alpha"]

    def scale_factor(self, layer: str) -> float:
        d = self._depth.get(layer, self._depth["interaction"])
        return d["scale"]


# ============================================================
# Particle Variety Renderer
# ============================================================

class ParticleVariety:
    """Adds visual variety to particle rendering.

    Each particle gets a random "shape type" on creation.
    The renderer draws accordingly:
        type 0 — stardust (cross pattern, ~40%)
        type 1 — soft orb (default glow, ~35%)
        type 2 — fiber (short line, ~15%)
        type 3 — spark (tiny bright point, ~10%)
    """

    SHAPE_STARDUST = 0
    SHAPE_ORB = 1
    SHAPE_FIBER = 2
    SHAPE_SPARK = 3

    @staticmethod
    def random_shape() -> int:
        """Return a random shape type with weighted distribution."""
        r = random.random()
        if r < 0.40: return ParticleVariety.SHAPE_STARDUST
        if r < 0.75: return ParticleVariety.SHAPE_ORB
        if r < 0.90: return ParticleVariety.SHAPE_FIBER
        return ParticleVariety.SHAPE_SPARK

    @staticmethod
    def draw(
        py5,
        shape_type: int,
        x: float, y: float, r: float,
        opacity: float,
        color: tuple[int, int, int],
        glow_color: tuple[int, int, int],
        angle: float = 0.0,
    ) -> None:
        """Render a particle with its shape type.

        Args:
            py5: py5 sketch.
            shape_type: SHAPE_STARDUST / SHAPE_ORB / SHAPE_FIBER / SHAPE_SPARK.
            x, y: Position.
            r: Base radius.
            opacity: 0–255.
            color: Main (r, g, b).
            glow_color: Glow (r, g, b).
            angle: Velocity angle (for fiber orientation).
        """
        o = opacity / 255.0
        cr, cg, cb = color
        gr, gg, gb = glow_color

        if shape_type == ParticleVariety.SHAPE_STARDUST:
            # Cross pattern — 4-point star
            py5.no_stroke()
            py5.fill(gr, gg, gb, 30.0 * o)
            py5.circle(x, y, r * 4.0)
            py5.fill(cr, cg, cb, 120.0 * o)
            py5.circle(x, y, r * 1.3)
            # Cross arms
            py5.stroke(255, 255, 255, 150.0 * o)
            py5.stroke_weight(r * 0.3)
            arm = r * 3.0
            py5.line(x - arm, y, x + arm, y)
            py5.line(x, y - arm, x, y + arm)
            # Hot center
            py5.stroke(255, 255, 255, 200.0 * o)
            py5.stroke_weight(r * 0.5)
            py5.point(x, y)

        elif shape_type == ParticleVariety.SHAPE_ORB:
            # Default soft glow (current style, simplified)
            py5.no_stroke()
            py5.fill(gr, gg, gb, 40.0 * o)
            py5.circle(x, y, r * 3.0)
            py5.fill(cr, cg, cb, 150.0 * o)
            py5.circle(x, y, r * 1.2)
            py5.stroke(255, 255, 255, 200.0 * o)
            py5.stroke_weight(r * 0.5)
            py5.point(x, y)

        elif shape_type == ParticleVariety.SHAPE_FIBER:
            # Short fiber aligned with velocity
            py5.no_stroke()
            py5.fill(gr, gg, gb, 20.0 * o)
            py5.circle(x, y, r * 2.5)
            # Colored line in velocity direction
            length = r * 3.0
            cos_a, sin_a = math.cos(angle), math.sin(angle)
            py5.stroke(cr, cg, cb, 100.0 * o)
            py5.stroke_weight(r * 0.4)
            py5.line(
                x - cos_a * length, y - sin_a * length,
                x + cos_a * length, y + sin_a * length,
            )
            # Core
            py5.stroke(255, 255, 255, 180.0 * o)
            py5.stroke_weight(r * 0.4)
            py5.point(x, y)

        elif shape_type == ParticleVariety.SHAPE_SPARK:
            # Tiny bright spark
            py5.no_stroke()
            py5.fill(gr, gg, gb, 50.0 * o)
            py5.circle(x, y, r * 1.8)
            py5.stroke(255, 255, 255, 220.0 * o)
            py5.stroke_weight(r * 0.6)
            py5.point(x, y)


# ============================================================
# Breathing Camera — subtle drift + scale
# ============================================================

class BreathingCamera:
    """Subtle camera oscillation for organic feel.

    Slow sinusoidal drift + gentle scale breathing.
    Very mild — should be barely noticeable, not distracting.
    """

    def __init__(self) -> None:
        self._phase: float = 0.0
        self._breath_amplitude: float = 0.001   # 0.1% scale — barely perceptible
        self._drift_amplitude: float = 0.6      # pixels — very subtle

    def update(self, dt: float) -> None:
        self._phase += dt * 0.4  # very slow

    def apply(self, py5) -> None:
        """Apply breathing camera transform inside push_matrix."""
        w, h = py5.width, py5.height

        # Gentle scale breathing
        breath = 1.0 + math.sin(self._phase) * self._breath_amplitude
        drift_x = math.cos(self._phase * 1.3) * self._drift_amplitude
        drift_y = math.sin(self._phase * 0.7) * self._drift_amplitude

        py5.translate(w / 2, h / 2)
        py5.scale(breath)
        py5.translate(drift_x, drift_y)
        py5.translate(-w / 2, -h / 2)


# ============================================================
# State Lighting — theme-driven ambient glow
# ============================================================

class StateLighting:
    """Unified lighting driven by space state + theme palette.

    Applies ambient glow, highlight modulation, and per-frame
    state color interpolation.
    """

    def __init__(self) -> None:
        self._current_state: str = "IDLE"
        self._prev_state: str = "IDLE"
        self._transition: float = 0.0

    def set_state(self, state: str) -> None:
        if state != self._current_state:
            self._prev_state = self._current_state
            self._current_state = state
            self._transition = 0.0

    def update(self, dt: float) -> None:
        if self._transition < 1.0:
            self._transition = min(1.0, self._transition + dt * 1.5)

    @property
    def current_theme(self) -> dict:
        """Interpolated theme between previous and current state."""
        if self._transition >= 1.0:
            return Config.Palette.Theme.get(self._current_state)

        prev = Config.Palette.Theme.get(self._prev_state)
        curr = Config.Palette.Theme.get(self._current_state)
        t = smoothstep(self._transition)
        return {
            k: _interp_color(prev[k], curr[k], t)
            if k in ("primary", "secondary", "ambient", "particle", "glow")
            else prev[k] + (curr[k] - prev[k]) * t
            for k in prev
        }

    def ambient_alpha(self) -> float:
        """Ambient layer alpha (increases with activity)."""
        state_alpha = {"IDLE": 0.0, "ACTIVE": 0.05, "EXCITED": 0.12, "CALM": 0.03}
        return state_alpha.get(self._current_state, 0.0)


def _interp_color(
    a: tuple[int, int, int],
    b: tuple[int, int, int],
    t: float,
) -> tuple[int, int, int]:
    """Interpolate between two RGB tuples."""
    return (
        int(a[0] + (b[0] - a[0]) * t),
        int(a[1] + (b[1] - a[1]) * t),
        int(a[2] + (b[2] - a[2]) * t),
    )
