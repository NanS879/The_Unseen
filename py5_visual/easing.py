"""
Standard easing functions for smooth animation transitions.

All functions take t in [0, 1] and return a value in [0, 1].
Used by: particle lifecycle, seed pulse, glow fades, day/night.

Reference: https://easings.net/
"""

import math


def linear(t: float) -> float:
    """No easing — constant rate."""
    return t


def ease_in_quad(t: float) -> float:
    """Quadratic ease-in: slow start, fast end."""
    return t * t


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out: fast start, slow end."""
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out: slow at both ends."""
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


def ease_in_cubic(t: float) -> float:
    return t * t * t


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_cubic(t: float) -> float:
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0


def smoothstep(t: float) -> float:
    """Smoothstep (Hermite interpolation): smooth S-curve.

    Most natural-looking easing for organic animations.
    Used by: particle opacity, glow, growth transitions.
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def smootherstep(t: float) -> float:
    """Perlin's smootherstep: even smoother than smoothstep."""
    t = max(0.0, min(1.0, t))
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def pulse(t: float) -> float:
    """Sinusoidal pulse: 0→1→0 over one period.

    Args:
        t: Phase in [0, 1].
    """
    return 0.5 + 0.5 * math.sin(t * math.pi * 2.0 - math.pi / 2.0)
