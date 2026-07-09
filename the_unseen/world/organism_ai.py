"""
Autonomous Organism AI with state machine and perception-driven behavior.

Each OrganismAI:
- Has a position, velocity, and internal emotional state
- Perceives the world through a Perception instance
- Makes decisions via a simple behavior tree
- Moves independently (not waiting for user input)
- Has affinity/fear/curiosity emotional model

States: IDLE → EXPLORE → OBSERVE → FOLLOW → FLEE → SLEEP → FADE

Design: extends existing DLA Organism with autonomous behavior.
The DLA growth engine remains for visual structure.
"""

import math
import random
import time
from typing import Optional

from ..config import Config
from .perception import Perception


# ── Organism States ────────────────────────────────────

class OrgState:
    IDLE    = "idle"
    EXPLORE = "explore"
    OBSERVE = "observe"
    FOLLOW  = "follow"
    FLEE    = "flee"
    SLEEP   = "sleep"
    FADE    = "fade"


class OrganismAI:
    """An autonomous digital organism with emotions and behavior.

    Wraps an existing Organism (DLA growth) instance.
    Adds: perception, emotions, state machine, movement, decisions.
    """

    MAX_SPEED = 0.8          # px per frame max
    PERCEPTION_RANGE = 600.0 # px — how far organism can sense

    def __init__(self, organism, x: float, y: float) -> None:
        """Create autonomous organism at position.

        Args:
            organism: Existing Organism instance (DLA growth).
            x, y: Spawn position in pixels.
        """
        # ── Identity ────────────────────────────────────
        self.id = f"org_{int(time.time() * 1000) % 100000}"
        self.organism = organism  # DLA growth engine
        self.age: float = 0.0

        # ── Position & movement ─────────────────────────
        self.x: float = x
        self.y: float = y
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.target_x: Optional[float] = None
        self.target_y: Optional[float] = None

        # ── Energy ──────────────────────────────────────
        self.energy: float = 50.0

        # ── State machine ───────────────────────────────
        self.state: str = OrgState.IDLE
        self.state_timer: float = 0.0
        self.last_state_change: float = 0.0

        # ── Emotions (0.0–1.0) ─────────────────────────
        self.curiosity: float = 0.5
        self.fear: float = 0.1
        self.affinity: float = 0.0    # builds slowly toward user
        self.tiredness: float = 0.0   # grows with activity

        # ── Perception ──────────────────────────────────
        self.perception = Perception()

        # ── Wander target ───────────────────────────────
        self._wander_angle: float = random.uniform(0, math.pi * 2)
        self._wander_timer: float = 0.0

        # ── Short-term memory ───────────────────────────
        self._last_hand_pos: tuple[float, float] = (0, 0)
        self._times_observed: int = 0
        self._flee_cooldown: float = 0.0

    # ── Update ──────────────────────────────────────────

    def update(self, dt: float, world_state) -> None:
        """Update organism for one frame: perceive → decide → act.

        Args:
            dt: Time delta in seconds.
            world_state: WorldState singleton.
        """
        dt = min(dt, 0.1)
        self.age += dt
        self.state_timer += dt

        # ── Perceive ───────────────────────────────────
        self.perception.update(self.x, self.y, world_state)

        # ── Update emotions ────────────────────────────
        self._update_emotions(dt)

        # ── Decide ─────────────────────────────────────
        self._decide(dt)

        # ── Act ────────────────────────────────────────
        self._move(dt)

        # ── Energy decay ───────────────────────────────
        self.energy = max(0.0, min(100.0, self.energy - 0.01 * dt))
        if self.state != OrgState.SLEEP:
            self.tiredness = min(1.0, self.tiredness + 0.003 * dt)

    # ── Emotions ───────────────────────────────────────

    def _update_emotions(self, dt: float) -> None:
        """Update emotional state based on perception."""
        p = self.perception

        # Curiosity: rises when hand is near but slow
        if p.hand_is_near(400) and p.hand_is_still():
            self.curiosity = min(1.0, self.curiosity + 0.02 * dt)
        else:
            self.curiosity = max(0.2, self.curiosity - 0.005 * dt)

        # Fear: rises with fast hand movement nearby
        if p.hand_is_near(300) and p.hand_is_fast():
            self.fear = min(1.0, self.fear + 0.08 * dt)
        else:
            self.fear = max(0.05, self.fear - 0.01 * dt)

        # Affinity: slowly builds when user is calm and present
        if p.hand_is_near(500) and p.hand_is_still():
            self.affinity = min(1.0, self.affinity + 0.005 * dt)
            self._times_observed += dt
        elif not p.hand_present():
            self.affinity = max(0.0, self.affinity - 0.002 * dt)

        # Cooldowns
        self._flee_cooldown = max(0.0, self._flee_cooldown - dt)

    # ── Decision ───────────────────────────────────────

    def _decide(self, dt: float) -> None:
        """Simple behavior tree: fear > curiosity > affinity > default.

        Priority order: FLEE > OBSERVE > FOLLOW > EXPLORE > SLEEP > IDLE
        """
        p = self.perception

        # ── FLEE: high fear ────────────────────────────
        if self.fear > 0.7 and p.hand_present() and self._flee_cooldown <= 0:
            self._set_state(OrgState.FLEE)

        # ── OBSERVE: high curiosity ────────────────────
        elif self.curiosity > 0.7 and p.hand_is_near(500):
            self._set_state(OrgState.OBSERVE)

        # ── FOLLOW: high affinity ──────────────────────
        elif self.affinity > 0.6 and p.hand_is_near(400) and self.fear < 0.3:
            self._set_state(OrgState.FOLLOW)

        # ── EXPLORE: default active state ──────────────
        elif self.curiosity > 0.4 and self.tiredness < 0.7:
            self._set_state(OrgState.EXPLORE)

        # ── SLEEP: tired ───────────────────────────────
        elif self.tiredness > 0.8:
            self._set_state(OrgState.SLEEP)

        # ── IDLE: fallback ─────────────────────────────
        else:
            self._set_state(OrgState.IDLE)

    def _set_state(self, new_state: str) -> None:
        """Transition to a new state."""
        if new_state != self.state:
            self.state = new_state
            self.state_timer = 0.0

    # ── Movement ───────────────────────────────────────

    def _move(self, dt: float) -> None:
        """Execute movement based on current state."""
        if self.state == OrgState.FLEE:
            self._move_flee(dt)
        elif self.state == OrgState.OBSERVE:
            self._move_observe(dt)
        elif self.state == OrgState.FOLLOW:
            self._move_follow(dt)
        elif self.state == OrgState.EXPLORE:
            self._move_wander(dt)
        elif self.state == OrgState.SLEEP:
            self._move_drift(dt)
        else:
            self._move_drift(dt)

        # Apply velocity
        self.x += self.vx
        self.y += self.vy

        # Wrap edges
        w, h = Config.WIDTH, Config.HEIGHT
        m = 50.0
        if self.x < -m: self.x = w + m
        if self.x > w + m: self.x = -m
        if self.y < -m: self.y = h + m
        if self.y > h + m: self.y = -m

    def _move_flee(self, dt: float) -> None:
        """Move away from nearest hand."""
        p = self.perception
        dx = self.x - p.nearest_hand_x
        dy = self.y - p.nearest_hand_y
        dist = max(1.0, math.sqrt(dx * dx + dy * dy))
        speed = self.MAX_SPEED * 2.0 * self.fear
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed
        self._flee_cooldown = 3.0  # don't re-trigger flee for 3s

    def _move_observe(self, dt: float) -> None:
        """Stay at a respectful distance, slight approach."""
        self._approach_target(
            self.perception.nearest_hand_x,
            self.perception.nearest_hand_y,
            speed_factor=0.3,
            min_dist=150.0)

    def _move_follow(self, dt: float) -> None:
        """Gently follow the hand."""
        self._approach_target(
            self.perception.nearest_hand_x,
            self.perception.nearest_hand_y,
            speed_factor=0.5,
            min_dist=80.0)

    def _move_wander(self, dt: float) -> None:
        """Random walk with smooth direction changes."""
        self._wander_timer += dt
        if self._wander_timer > random.uniform(2.0, 5.0):
            self._wander_timer = 0.0
            self._wander_angle += random.uniform(-math.pi * 0.5, math.pi * 0.5)

        speed = self.MAX_SPEED * 0.4
        self.vx = math.cos(self._wander_angle) * speed
        self.vy = math.sin(self._wander_angle) * speed

    def _move_drift(self, dt: float) -> None:
        """Very slow passive drift."""
        self.vx *= 0.95
        self.vy *= 0.95

    def _approach_target(self, tx: float, ty: float,
                         speed_factor: float = 0.5,
                         min_dist: float = 100.0) -> None:
        """Move toward a target, stopping at min_dist."""
        dx = tx - self.x
        dy = ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < min_dist:
            self.vx *= 0.9
            self.vy *= 0.9
            return
        speed = self.MAX_SPEED * speed_factor
        self.vx = (dx / dist) * speed
        self.vy = (dy / dist) * speed

    # ── Display ────────────────────────────────────────

    def display(self, py5) -> None:
        """Render organism as a soft orb at current position.

        Color reflects emotional state.
        Size reflects energy.
        """
        r = 6.0 + self.energy * 0.15
        o = 0.4 + self.energy * 0.006

        # Color by state
        if self.state == OrgState.FLEE:
            cr, cg, cb = 255, 80, 80
        elif self.state == OrgState.FOLLOW:
            cr, cg, cb = 200, 220, 255
        elif self.state == OrgState.OBSERVE:
            cr, cg, cb = 180, 160, 255
        elif self.state == OrgState.EXPLORE:
            cr, cg, cb = 120, 200, 160
        elif self.state == OrgState.SLEEP:
            cr, cg, cb = 60, 60, 120
        else:
            cr, cg, cb = 100, 140, 220

        py5.no_stroke()
        # Outer glow
        py5.fill(cr, cg, cb, 40.0 * o)
        py5.circle(self.x, self.y, r * 3.0)
        # Core
        py5.fill(cr, cg, cb, 160.0 * o)
        py5.circle(self.x, self.y, r)

        # DLA structure follows the organism
        if self.organism and self.organism.growth:
            self.organism.growth.center_x = self.x
            self.organism.growth.center_y = self.y
            self.organism.growth.display(
                py5,
                color_growth=Config.Palette.GROWTH_WHITE,
                color_core=Config.Palette.LIFE_DEEP)
