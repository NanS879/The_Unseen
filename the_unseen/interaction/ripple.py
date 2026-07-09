"""
Ripple system — the core interaction language of V4.

Every user action generates ripples: expanding rings that affect
particles, glow, and flow. Ripples are lightweight (max 20, 30-frame
lifespan) and create immediate visual feedback.

Triggers:
    - Hand speed change (move / stop)
    - Seed creation
    - Organism growth
    - Fragment collection
"""

import math
import random


class Ripple:
    """Single expanding ring ripple."""

    def __init__(self, x: float, y: float, strength: float = 1.0,
                 color: tuple[int, int, int] = (180, 200, 255)) -> None:
        self.x = x
        self.y = y
        self.strength = strength       # affects radius and push force
        self.color = color
        self.age: float = 0.0
        self.life: float = 30.0        # frames (~0.5s at 60fps)
        self.radius: float = 0.0
        self.max_radius: float = 80.0 + strength * 60.0
        self.alive: bool = True

    def update(self) -> None:
        """Advance one frame."""
        self.age += 1.0
        t = self.age / self.life
        # Fast expand at start, slow at end
        self.radius = self.max_radius * (1.0 - (1.0 - t) ** 3)
        if self.age >= self.life:
            self.alive = False

    def alpha(self) -> float:
        """Current alpha 0–80 based on remaining life."""
        t = self.age / self.life
        return 70.0 * (1.0 - t) * (1.0 - t)

    def push_force(self, px: float, py: float) -> tuple[float, float]:
        """Compute radial push force on a particle at (px, py)."""
        dx = px - self.x
        dy = py - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        ring_width = 20.0
        if dist < 0.01:
            return (0.0, 0.0)
        zone = abs(dist - self.radius)
        if zone > ring_width:
            return (0.0, 0.0)
        force = self.strength * (1.0 - zone / ring_width) * self.alpha() / 70.0
        ndx = dx / dist
        ndy = dy / dist
        return (ndx * force * 0.3, ndy * force * 0.3)

    def flow_modulation(self, x: float, y: float) -> float:
        """Flow field boost factor near ripple ring (0=none, 1=max)."""
        dx = x - self.x
        dy = y - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 0.01:
            return 0.0
        zone = abs(dist - self.radius)
        if zone > 40.0:
            return 0.0
        return self.strength * 0.15 * (1.0 - zone / 40.0) * self.alpha() / 70.0

    def camera_shake_strength(self) -> float:
        """Camera shake derived from this ripple."""
        return self.strength * 0.08 * self.alpha() / 70.0


class RippleManager:
    """Manages active ripples — spawn, update, display."""

    MAX_RIPPLES = 25

    def __init__(self) -> None:
        self.ripples: list[Ripple] = []

    def spawn(self, x: float, y: float, strength: float = 1.0,
              color: tuple[int, int, int] | None = None) -> None:
        """Create a new ripple at position.

        Args:
            x, y: Center position.
            strength: 0.5–3.0 (affects size and force).
            color: Override color (default blue-white).
        """
        if len(self.ripples) >= self.MAX_RIPPLES:
            # Remove oldest
            self.ripples.pop(0)

        if color is None:
            color = (180, 200, 255)
        self.ripples.append(Ripple(x, y, strength, color))

    def update(self, particles: list | None = None) -> None:
        """Update all ripples, optionally push particles."""
        for r in self.ripples[:]:
            r.update()
            if not r.alive:
                self.ripples.remove(r)
                continue

            if particles is not None and r.strength > 0.3:
                for p in particles:
                    fx, fy = r.push_force(p.position[0], p.position[1])
                    if fx != 0.0 or fy != 0.0:
                        p.apply_force(fx, fy)

    def display(self, py5) -> None:
        """Draw all active ripples as fading circles — multi-layer."""
        for r in self.ripples:
            a = r.alpha()
            if a < 2.0:
                continue
            cr, cg, cb = r.color

            # Outer ring
            py5.no_fill()
            py5.stroke(cr, cg, cb, a * 0.5)
            py5.stroke_weight(max(0.3, r.strength * 0.6 * (1.0 - r.age / r.life)))
            py5.circle(r.x, r.y, r.radius + 5.0)

            # Main ring
            py5.stroke(cr, cg, cb, a)
            py5.stroke_weight(max(0.5, r.strength * 1.2 * (1.0 - r.age / r.life)))
            py5.circle(r.x, r.y, r.radius)

    # ── Flow / Camera / Lighting queries ──────────────

    def get_flow_modulation(self, x: float, y: float) -> float:
        """Cumulative flow boost from all active ripples at a point."""
        total = 0.0
        for r in self.ripples:
            total += r.flow_modulation(x, y)
        return min(1.0, total)

    def get_camera_shake(self) -> float:
        """Cumulative camera shake from all active ripples."""
        total = 0.0
        for r in self.ripples:
            total += r.camera_shake_strength()
        return min(3.0, total)

    def get_glow_boost(self) -> float:
        """Lighting glow boost from active ripples."""
        total = 0.0
        for r in self.ripples:
            total += r.strength * 0.08 * r.alpha() / 70.0
        return min(0.5, total)

    @property
    def active_count(self) -> int:
        return len(self.ripples)
