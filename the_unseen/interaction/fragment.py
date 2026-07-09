"""
Memory Fragments — collectible particles that drive exploration.

Fragments spawn randomly in space. When a hand approaches, they
accelerate toward it. On collection: energy boost, ripple spawn,
and a burst of highlight particles.

Design:
    - Max ~15 active fragments
    - Spawn ~1 every 3-5 seconds
    - Each fragment has a unique energy value and color
    - Collection triggers ripple + energy gain
"""

import math
import random

from ..config import Config


class MemoryFragment:
    """A glowing collectible that drifts until drawn toward a hand."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.energy_value: float = random.uniform(5.0, 20.0)
        self.size: float = random.uniform(3.0, 7.0)
        self.alive: bool = True
        self.age: float = 0.0

        # Color — varies per fragment
        hue = random.random()
        if hue < 0.4:
            self.color = Config.Palette.ENERGY_GOLD
        elif hue < 0.7:
            self.color = Config.Palette.MEMORY_PURPLE
        else:
            self.color = Config.Palette.LIFE_BLUE

        # Movement
        self.vx: float = random.uniform(-0.3, 0.3)
        self.vy: float = random.uniform(-0.3, 0.3)
        self._pulse_offset: float = random.uniform(0, math.pi * 2)

    def update(self, dt: float, hand_positions: list[tuple[float, float]]) -> None:
        """Update fragment position.

        If hands are present, fragment is attracted toward the nearest one.
        Otherwise it drifts slowly.

        Args:
            dt: Time delta.
            hand_positions: List of (x, y) hand positions.
        """
        self.age += dt

        # Attraction toward nearest hand
        if hand_positions:
            nearest_dist = float("inf")
            nearest_x, nearest_y = 0.0, 0.0
            for hx, hy in hand_positions:
                dx = self.x - hx
                dy = self.y - hy
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_x, nearest_y = hx, hy

            # Fragments are attracted from a larger range than particles
            attract_range = Config.INFLUENCE_RADIUS * 2.5  # ~625px
            if nearest_dist < attract_range:
                # Accelerate toward hand (stronger when closer)
                t = 1.0 - nearest_dist / attract_range
                pull_strength = 15.0 * t * t  # quadratic falloff
                dx = nearest_x - self.x
                dy = nearest_y - self.y
                if nearest_dist > 1.0:
                    self.vx += (dx / nearest_dist) * pull_strength
                    self.vy += (dy / nearest_dist) * pull_strength

        # Damping
        self.vx *= 0.97
        self.vy *= 0.97

        # Clamp speed
        spd = math.sqrt(self.vx * self.vx + self.vy * self.vy)
        if spd > 5.0:
            self.vx *= 5.0 / spd
            self.vy *= 5.0 / spd

        self.x += self.vx
        self.y += self.vy

        # Wrap edges
        w, h = Config.WIDTH, Config.HEIGHT
        if self.x < -20: self.x = w + 20
        if self.x > w + 20: self.x = -20
        if self.y < -20: self.y = h + 20
        if self.y > h + 20: self.y = -20

    def check_collected(self, hand_positions: list[tuple[float, float]],
                        collect_radius: float = 30.0) -> bool:
        """Check if fragment is close enough to any hand to be collected."""
        for hx, hy in hand_positions:
            dx = self.x - hx
            dy = self.y - hy
            if math.sqrt(dx * dx + dy * dy) < collect_radius:
                self.alive = False
                return True
        return False

    def display(self, py5) -> None:
        """Render fragment as a pulsing glowing orb."""
        pulse = 0.6 + 0.4 * math.sin(
            py5.frame_count * 0.08 + self._pulse_offset
        )
        r, g, b = self.color
        sz = self.size * pulse

        # Outer glow
        py5.no_stroke()
        py5.fill(r, g, b, 30.0 * pulse)
        py5.circle(self.x, self.y, sz * 3.0)

        # Core
        py5.fill(r, g, b, 180.0 * pulse)
        py5.circle(self.x, self.y, sz)

        # Spark
        py5.fill(255, 255, 255, 200.0 * pulse)
        py5.circle(self.x, self.y, sz * 0.4)


class FragmentManager:
    """Spawns, updates, and collects Memory Fragments."""

    MAX_FRAGMENTS = 15
    SPAWN_INTERVAL = 4.0  # seconds

    def __init__(self) -> None:
        self.fragments: list[MemoryFragment] = []
        self._spawn_timer: float = 0.0
        self.collected_count: int = 0

    def update(
        self, dt: float,
        hand_positions: list[tuple[float, float]],
        energy_manager,
        ripple_manager,
    ) -> None:
        """Update all fragments, handle spawning and collection.

        Args:
            dt: Time delta.
            hand_positions: List of (x, y) hand positions.
            energy_manager: EnergyManager for energy gain on collect.
            ripple_manager: RippleManager for collection effects.
        """
        # Spawn timer
        self._spawn_timer += dt
        spawn_every = self.SPAWN_INTERVAL * (0.5 if hand_positions else 1.0)
        if self._spawn_timer >= spawn_every and len(self.fragments) < self.MAX_FRAGMENTS:
            self._spawn_timer = 0.0
            self._spawn()

        # Update
        for f in self.fragments[:]:
            f.update(dt, hand_positions)

            # Check collection
            if hand_positions and f.check_collected(hand_positions):
                self._on_collect(f, energy_manager, ripple_manager)

            if not f.alive:
                self.fragments.remove(f)

    def _spawn(self) -> None:
        """Create a fragment at a random position (edges or interior)."""
        w, h = Config.WIDTH, Config.HEIGHT
        # 60% chance: spawn at edge; 40%: spawn anywhere
        if random.random() < 0.4:
            x = random.uniform(100, w - 100)
            y = random.uniform(100, h - 100)
        else:
            edge = random.randint(0, 3)
            if edge == 0:
                x, y = random.uniform(50, w - 50), -20.0
            elif edge == 1:
                x, y = random.uniform(50, w - 50), h + 20.0
            elif edge == 2:
                x, y = -20.0, random.uniform(50, h - 50)
            else:
                x, y = w + 20.0, random.uniform(50, h - 50)
        self.fragments.append(MemoryFragment(x, y))

    def _on_collect(self, f: MemoryFragment, energy_manager,
                    ripple_manager) -> None:
        """Handle fragment collection."""
        self.collected_count += 1

        # Add energy
        if energy_manager:
            energy_manager.energy = min(
                Config.ENERGY_MAX,
                energy_manager.energy + f.energy_value,
            )

        # Spawn ripple
        if ripple_manager:
            ripple_manager.spawn(
                f.x, f.y,
                strength=1.0 + f.energy_value / 20.0,
                color=f.color,
            )

    def display(self, py5) -> None:
        """Render all active fragments."""
        for f in self.fragments:
            f.display(py5)

    @property
    def active_count(self) -> int:
        return len(self.fragments)
