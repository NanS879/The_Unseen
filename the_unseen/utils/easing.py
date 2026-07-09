"""
Easing functions for smooth animation transitions.

smoothstep: Hermite S-curve (particle lifecycle, camera, post effects).
ease_out_cubic: fast start, slow end (camera effects).
"""


def smoothstep(t: float) -> float:
    """Smoothstep (Hermite interpolation): smooth S-curve."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out: 1 - (1-t)^3."""
    return 1.0 - (1.0 - t) ** 3
