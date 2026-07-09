"""
Visual rendering utilities.

Hand aura: soft multi-layer filled glow rings.
Startup hint: subtle guidance text when no hands detected.

V3.5: Removed dead code (status overlay, vignette).
All colors from Config.Palette.
"""

import math

from ..config import Config
from ..simulation.space_state import SpaceState


def draw_hand_aura(
    py5, px: float, py: float, speed: float, state: str, color: tuple
) -> None:
    """Draw an elegant soft-glow aura around hand position.

    Uses concentric filled circles with decreasing alpha for a
    smooth gradient-like effect. More layers in EXCITED state.
    All colors from Config.Palette.

    Args:
        py5: py5 sketch module.
        px, py: Hand position in pixels.
        speed: Hand speed (0–~0.2).
        state: SpaceState name.
        color: (r, g, b) from Palette.HAND_LEFT or HAND_RIGHT.
    """
    r, g, b = color
    intensity = min(1.0, speed * 8.0)
    layers = 3 if state == SpaceState.EXCITED else 2
    base_radius = 18.0 + speed * 60.0

    py5.no_stroke()

    # Outer → inner glow layers
    for i in range(layers, 0, -1):
        t = i / layers  # 1.0 (outer) → 1/layers (inner)
        radius = base_radius * t * 1.6
        alpha = 25.0 * t * (1.0 + intensity)
        py5.fill(r, g, b, alpha)
        py5.circle(px, py, radius)

    # Soft core
    core_r = 6.0 + speed * 20.0
    py5.fill(255, 255, 255, 40.0 + intensity * 50.0)
    py5.circle(px, py, core_r)

    # Thin ring accent
    ring_r = base_radius * 0.7
    py5.no_fill()
    py5.stroke(r, g, b, 50.0 + intensity * 40.0)
    py5.stroke_weight(0.6)
    py5.circle(px, py, ring_r)


def draw_startup_hint(
    py5,
    has_hands: bool,
    has_data: bool,
    organism_count: int,
    seed_count: int,
    frame_count: int,
    font: object = None,
) -> None:
    """Draw subtle guidance text for new users.

    Shows different messages based on system state.
    Fades out after 10 seconds or when hands appear.

    Args:
        py5: py5 sketch module.
        has_hands: Whether hands are currently detected.
        has_data: Whether OSC data has ever been received.
        organism_count: Number of active organisms.
        seed_count: Number of pending seeds.
        frame_count: Current frame number (for fade timing).
        font: Optional cached py5 font.
    """
    if font:
        py5.text_font(font)
    py5.text_size(13)

    # Determine message
    if not has_data and frame_count < 600:
        msg = "Waiting for hand tracker..."
        alpha = _fade_alpha(frame_count, 0, 300, 180)
    elif not has_hands and organism_count == 0 and seed_count == 0:
        msg = "Hold your hand still to plant a seed"
        alpha = _fade_alpha(frame_count, 120, 600, 120)
    elif not has_hands and organism_count > 0:
        msg = f"{organism_count} organism{'s' if organism_count > 1 else ''} growing in the space"
        alpha = _fade_alpha(frame_count, 0, 400, 100)
    elif has_hands and seed_count > 0:
        msg = "Keep holding... seed is gaining energy"
        alpha = 100
    else:
        return  # Don't show when hands are active

    if alpha < 5:
        return

    py5.push()
    py5.text_align(py5.CENTER)
    py5.fill(180, 190, 220, alpha)
    py5.text(msg, Config.WIDTH / 2, Config.HEIGHT - 40)
    py5.text_align(py5.LEFT)
    py5.pop()


def _fade_alpha(frame: int, start: int, end: int, peak: int) -> float:
    """Compute fade-in-then-out alpha for a frame range.

    Args:
        frame: Current frame count.
        start: Frame when fade-in begins.
        end: Frame when fade-out completes.
        peak: Maximum alpha value.

    Returns:
        Alpha value 0–peak.
    """
    if frame < start:
        return 0.0
    if frame < (start + end) / 2:
        # Fade in
        t = (frame - start) / ((end - start) / 2)
        return peak * min(1.0, t)
    if frame < end:
        # Fade out
        t = (frame - (start + end) / 2) / ((end - start) / 2)
        return peak * max(0.0, 1.0 - t)
    return 0.0
