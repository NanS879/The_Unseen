"""
Particle class for the generative art system.

Each particle has:
- position, velocity, acceleration (2D vectors)
- life (decrements each frame, respawns on death)
- size (randomized per particle)
- glow rendering with concentric circles
"""

import random
import math


class Particle:
    """A single glowing particle with life-cycle management.

    Particles follow the flow field, respond to dual-hand gravity,
    fade with age, and respawn at random positions when their life expires.
    """

    # Color presets
    COOL = (180, 210, 255)        # No hand — cool blue-white
    RIGHT_WARM = (255, 200, 100)  # Right hand — warm gold
    LEFT_WARM = (255, 150, 255)   # Left hand — cool magenta

    def __init__(self, width: int, height: int) -> None:
        """Create a particle at a random position within the canvas.

        Args:
            width: Canvas width in pixels.
            height: Canvas height in pixels.
        """
        self.width = width
        self.height = height
        self.position = [random.uniform(0, width), random.uniform(0, height)]
        self.velocity = [0.0, 0.0]
        self.acceleration = [0.0, 0.0]

        # Life in frames (200–400 = ~3–7 seconds at 60fps)
        self.max_life = random.uniform(200, 400)
        self.life = random.uniform(0, self.max_life)

        # Base size (radius in pixels)
        self.size = random.uniform(1.5, 4.5)

        # Previous position for trail rendering
        self.prev_x = self.position[0]
        self.prev_y = self.position[1]

        # Burst color override (set by _spawn_burst for trail particles)
        self.burst_r: float = 255.0
        self.burst_g: float = 200.0
        self.burst_b: float = 100.0

    def apply_force(self, fx: float, fy: float) -> None:
        """Accumulate a force vector onto the particle's acceleration.

        Args:
            fx: Force magnitude in x direction.
            fy: Force magnitude in y direction.
        """
        self.acceleration[0] += fx
        self.acceleration[1] += fy

    def update(self, max_speed: float = 4.0, damping: float = 0.95) -> None:
        """Integrate physics: acceleration → velocity → position.

        Applies velocity damping and clamping, then resets acceleration.

        Args:
            max_speed: Maximum velocity magnitude (pixels/frame).
            damping: Velocity multiplier per frame (0.95 = gentle friction).
        """
        # Store previous position
        self.prev_x = self.position[0]
        self.prev_y = self.position[1]

        # Integrate
        self.velocity[0] += self.acceleration[0]
        self.velocity[1] += self.acceleration[1]

        # Damping
        self.velocity[0] *= damping
        self.velocity[1] *= damping

        # Clamp speed
        speed = math.sqrt(
            self.velocity[0] ** 2 + self.velocity[1] ** 2
        )
        if speed > max_speed:
            scale = max_speed / speed
            self.velocity[0] *= scale
            self.velocity[1] *= scale

        # Apply velocity
        self.position[0] += self.velocity[0]
        self.position[1] += self.velocity[1]

        # Reset acceleration
        self.acceleration[0] = 0.0
        self.acceleration[1] = 0.0

        # Decrement life
        self.life -= 1.0

        # Wrap around edges
        self._wrap_edges()

    def _wrap_edges(self) -> None:
        """Wrap particle position around canvas edges for seamless flow."""
        margin = 10.0
        if self.position[0] < -margin:
            self.position[0] = self.width + margin
            self.prev_x = self.position[0]
        if self.position[0] > self.width + margin:
            self.position[0] = -margin
            self.prev_x = self.position[0]
        if self.position[1] < -margin:
            self.position[1] = self.height + margin
            self.prev_y = self.position[1]
        if self.position[1] > self.height + margin:
            self.position[1] = -margin
            self.prev_y = self.position[1]

    def is_dead(self) -> bool:
        """Check if the particle's life has expired."""
        return self.life <= 0.0

    def respawn(self) -> None:
        """Reset particle to a random position with full life.

        New particles appear at edges for a gentler introduction, or at
        a random position anywhere on the canvas.
        """
        # Occasionally spawn from edges for organic "flowing in" effect
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

        self.prev_x = self.position[0]
        self.prev_y = self.position[1]
        self.velocity = [0.0, 0.0]
        self.acceleration = [0.0, 0.0]
        self.max_life = random.uniform(200, 400)
        self.life = self.max_life
        self.size = random.uniform(1.5, 4.5)

    def life_ratio(self) -> float:
        """Return life as a 0.0–1.0 ratio for alpha/color calculations."""
        return max(0.0, min(1.0, self.life / self.max_life))

    def _draw_glow(self, py5, rr: float, gg: float, bb: float, lr: float,
                   x: float, y: float, r: float) -> None:
        """Draw the 4-layer glow for a particle (shared by display methods)."""
        # Outer halo — large, soft glow
        py5.no_stroke()
        py5.fill(rr, gg, bb, 18.0 * lr)
        py5.circle(x, y, r * 6.0)

        # Mid glow
        py5.fill(rr, gg, bb, 50.0 * lr)
        py5.circle(x, y, r * 3.0)

        # Inner core — bright
        py5.fill(rr, gg, bb, 160.0 * lr)
        py5.circle(x, y, r * 1.2)

        # Hot center — white
        py5.fill(255, 255, 255, 220.0 * lr)
        py5.circle(x, y, r * 0.5)

    def display(self, py5, near_hand: float = 0.0) -> None:
        """Render trail/burst particle with its stored burst color.

        Used by trail particles spawned during burst mode.

        Args:
            py5: The py5 module/sketch for drawing calls.
            near_hand: Unused (kept for API compatibility).
        """
        lr = self.life_ratio()
        self._draw_glow(py5, self.burst_r, self.burst_g, self.burst_b,
                        lr, self.position[0], self.position[1], self.size)

    def display_dual(self, py5, near_hand: float = 0.0,
                     near_left: float = 0.0, near_right: float = 0.0) -> None:
        """Render the particle with dual-hand color blending.

        Colors blend between:
        - Cool blue-white (no hand proximity)
        - Warm gold      (near right hand)
        - Cool magenta   (near left hand)

        When both hands are near, colors mix additively, creating a
        warm white-pink zone between the hands.

        Args:
            py5: The py5 module/sketch for drawing calls.
            near_hand: Overall proximity (for brightness boost).
            near_left: 0.0–1.0 proximity to left hand.
            near_right: 0.0–1.0 proximity to right hand.
        """
        lr = self.life_ratio()
        x = self.position[0]
        y = self.position[1]
        r = self.size

        # Blend: cool base + right-hand warm shift + left-hand magenta shift
        rr = (self.COOL[0]
              + (self.RIGHT_WARM[0] - self.COOL[0]) * near_right
              + (self.LEFT_WARM[0] - self.COOL[0]) * near_left)
        gg = (self.COOL[1]
              + (self.RIGHT_WARM[1] - self.COOL[1]) * near_right
              + (self.LEFT_WARM[1] - self.COOL[1]) * near_left)
        bb = (self.COOL[2]
              + (self.RIGHT_WARM[2] - self.COOL[2]) * near_right
              + (self.LEFT_WARM[2] - self.COOL[2]) * near_left)

        # Clamp
        rr = max(0.0, min(255.0, rr))
        gg = max(0.0, min(255.0, gg))
        bb = max(0.0, min(255.0, bb))

        self._draw_glow(py5, rr, gg, bb, lr, x, y, r)
