"""
Organism — a living digital entity that grows from a MemorySeed.

Each organism wraps a seed and a DLA growth engine. Growth is
incremental and depends on available energy. Multiple organisms
form a simple digital ecosystem with distance-based rules.

Design:
    Organism = Seed (memory) + DLAEngine (growth) + Lifecycle
    OrganismManager = Ecosystem rules + seed creation logic
"""

import math
import time
from typing import Optional

from config import Config
from memory_seed import MemorySeed
from growth_algorithm import DLAEngine
from energy_manager import EnergyManager


class Organism:
    """A digital lifeform: MemorySeed + DLA growth.

    Lifecycle:
        seed (dormant) → growing (active DLA) → complete (full size)

    Growth speed is modulated by:
        - Global energy level
        - Hand proximity (closer = faster growth)
        - Neighbor proximity (too close = competition)
    """

    def __init__(self, seed: MemorySeed) -> None:
        """Create an organism from a memory seed.

        Args:
            seed: The MemorySeed that spawned this organism.
        """
        self.seed = seed
        self.growth = DLAEngine(
            center_x=seed.x,
            center_y=seed.y,
            max_radius=Config.DLA_MAX_RADIUS,
            stick_radius=Config.DLA_STICK_RADIUS,
        )

        # Growth state
        self.is_growing: bool = True
        self.growth_slowdown: float = 1.0  # 0–1 from neighbor competition
        self.created_at: float = time.time()

        # Mark seed as grown
        seed.mark_grown()

    def update(
        self,
        energy_manager: EnergyManager,
        growth_mult: float = 1.0,
        hand_influence: float = 0.0,
    ) -> None:
        """Update organism growth for one frame.

        Growth only happens when energy is available. Each growth
        step costs a small amount of energy.

        Args:
            energy_manager: Global energy pool.
            growth_mult: Global growth multiplier (from TimeSystem/Energy).
            hand_influence: 0–1 hand proximity boost.
        """
        if not self.is_growing:
            return

        if self.growth.is_complete():
            self.is_growing = False
            return

        # Calculate walker count based on energy and multipliers
        base_walkers = Config.DLA_WALKERS_PER_FRAME
        effective = int(
            base_walkers
            * growth_mult
            * (1.0 + hand_influence * 2.0)
            * self.growth_slowdown
        )
        effective = max(2, min(effective, base_walkers * 3))

        # Each growth step costs a tiny amount of energy
        cost = Config.ENERGY_GROWTH_COST * 0.001 * effective / base_walkers
        if energy_manager.consume(cost):
            self.growth.update(n_walkers=effective)

    def display(self, py5) -> None:
        """Render the organism's DLA cluster.

        Colors: inner core = deep blue (old/life), outer = white (new/growth).
        """
        self.growth.display(
            py5,
            color_growth=Config.Palette.GROWTH_WHITE,
            color_core=Config.Palette.LIFE_DEEP,
        )

    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within this organism's radius."""
        dx = x - self.seed.x
        dy = y - self.seed.y
        return math.sqrt(dx * dx + dy * dy) < Config.ORGANISM_MIN_DISTANCE

    def distance_to(self, other: "Organism") -> float:
        """Distance between this organism's center and another's."""
        dx = self.seed.x - other.seed.x
        dy = self.seed.y - other.seed.y
        return math.sqrt(dx * dx + dy * dy)

    def serialize(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "seed": self.seed.serialize(),
            "growth": self.growth.serialize(),
            "is_growing": self.is_growing,
            "growth_slowdown": self.growth_slowdown,
            "created_at": self.created_at,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "Organism":
        """Create from serialized dict."""
        seed = MemorySeed.deserialize(data["seed"])
        org = cls(seed)
        org.growth = DLAEngine.deserialize(data["growth"])
        org.is_growing = data.get("is_growing", True)
        org.growth_slowdown = data.get("growth_slowdown", 1.0)
        org.created_at = data.get("created_at", time.time())
        return org


class OrganismManager:
    """Manages the digital ecosystem of organisms.

    Responsibilities:
        - Seed creation from hand dwelling
        - Organism spawning when seeds are ready
        - Ecological rules between organisms
        - Rendering all organisms + connections
    """

    def __init__(self) -> None:
        """Initialize empty ecosystem."""
        self.organisms: list[Organism] = []
        self.pending_seeds: list[MemorySeed] = []
        self._dwell_timer: float = 0.0
        self._dwell_x: float = 0.0
        self._dwell_y: float = 0.0

    # ============================================================
    # Seed Creation
    # ============================================================

    def check_seed_creation(
        self,
        hand_x: float,
        hand_y: float,
        hand_speed: float,
        dt: float,
    ) -> Optional[MemorySeed]:
        """Check if hand is dwelling and create a seed if conditions met.

        Uses a smoothed dwell center (_dwell_x/y) as the reference point.
        This makes detection robust against natural hand tremor and
        MediaPipe landmark jitter (which can register as speed ~0.05
        even when the hand is perfectly still).

        Args:
            hand_x, hand_y: Primary hand position in pixels.
            hand_speed: Hand movement speed (normalized units).
            dt: Time delta in seconds.

        Returns:
            New MemorySeed if created, None otherwise.
        """
        # Initialize dwell center on first call
        if self._dwell_x == 0.0 and self._dwell_y == 0.0:
            self._dwell_x = hand_x
            self._dwell_y = hand_y

        # Distance from smoothed dwell center (not raw last position)
        dx = hand_x - self._dwell_x
        dy = hand_y - self._dwell_y
        dist_from_center = math.sqrt(dx * dx + dy * dy)

        # Dwelling: hand is within radius of dwell center AND speed is low
        if dist_from_center < Config.SEED_DWELL_RADIUS and hand_speed < Config.SEED_DWELL_SPEED_MAX:
            # Accumulate dwell time
            self._dwell_timer += dt
            # Slowly update dwell center toward hand (moving average)
            self._dwell_x += (hand_x - self._dwell_x) * 0.3
            self._dwell_y += (hand_y - self._dwell_y) * 0.3

            # Create seed after sufficient dwell time
            if self._dwell_timer >= Config.SEED_DWELL_TIME:
                # Check not too close to existing organisms
                too_close = False
                for org in self.organisms:
                    if org.contains_point(self._dwell_x, self._dwell_y):
                        too_close = True
                        break
                for s in self.pending_seeds:
                    sdx = self._dwell_x - s.x
                    sdy = self._dwell_y - s.y
                    if math.sqrt(sdx * sdx + sdy * sdy) < Config.ORGANISM_MIN_DISTANCE:
                        too_close = True
                        break

                if not too_close:
                    seed = MemorySeed(
                        x=self._dwell_x,
                        y=self._dwell_y,
                        speed=hand_speed,
                    )
                    seed.dwell_time = self._dwell_timer
                    self.pending_seeds.append(seed)
                    self._dwell_timer = 0.0
                    # Reset dwell center for next seed
                    self._dwell_x = hand_x
                    self._dwell_y = hand_y
                    total = len(self.pending_seeds) + len(self.organisms)
                    print(f"[V3] 🌱 Seed #{total} at ({seed.x:.0f}, {seed.y:.0f})")
                    return seed
        else:
            # Hand moved away — reset dwell timer, update dwell center
            self._dwell_timer = 0.0
            # Quick update toward new position
            self._dwell_x += (hand_x - self._dwell_x) * 0.5
            self._dwell_y += (hand_y - self._dwell_y) * 0.5

        return None

    # ============================================================
    # Ecosystem Update
    # ============================================================

    def update(
        self,
        energy_manager: EnergyManager,
        growth_mult: float = 1.0,
        has_hands: bool = False,
        hand_positions: list[tuple[float, float]] | None = None,
    ) -> None:
        """Update the entire ecosystem for one frame.

        Args:
            energy_manager: Global energy pool.
            growth_mult: Growth multiplier from TimeSystem.
            has_hands: Whether hands are detected.
            hand_positions: List of (x, y) hand positions for proximity.
        """
        # ---- Spawn ready seeds ----
        ready = [s for s in self.pending_seeds if s.is_ready()]
        for seed in ready:
            if len(self.organisms) >= Config.ORGANISM_MAX_COUNT:
                # Prune oldest organism
                oldest = min(self.organisms, key=lambda o: o.created_at)
                self.organisms.remove(oldest)
                print(f"[V3] Pruned oldest organism at ({oldest.seed.x:.0f}, {oldest.seed.y:.0f})")

            cost = Config.ENERGY_GROWTH_COST
            if energy_manager.consume(cost):
                org = Organism(seed)
                self.organisms.append(org)
                self.pending_seeds.remove(seed)
                print(f"[V3] Organism spawned at ({seed.x:.0f}, {seed.y:.0f}) "
                      f"— {len(self.organisms)} active")

        # ---- Update pending seeds ----
        for seed in self.pending_seeds[:]:
            # Check if hand is near this seed
            near = False
            if hand_positions:
                for hx, hy in hand_positions:
                    dx = seed.x - hx
                    dy = seed.y - hy
                    if math.sqrt(dx * dx + dy * dy) < Config.SEED_DWELL_RADIUS:
                        near = True
                        break
            seed.update(dt=1.0 / 60.0, hand_near=near)

        # ---- Ecological rules ----
        self._apply_ecology()

        # ---- Update organisms ----
        for org in self.organisms:
            # Hand proximity to this organism
            hand_influence = 0.0
            if hand_positions:
                for hx, hy in hand_positions:
                    dx = org.seed.x - hx
                    dy = org.seed.y - hy
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist < Config.INFLUENCE_RADIUS:
                        hand_influence = max(
                            hand_influence,
                            1.0 - dist / Config.INFLUENCE_RADIUS,
                        )

            org.update(energy_manager, growth_mult, hand_influence)

    def _apply_ecology(self) -> None:
        """Apply distance-based ecological rules between organisms.

        - Too close: growth slowed for both (competition)
        - Moderate: independent (neutral)
        - Far: independent (no interaction)
        """
        for i, org_a in enumerate(self.organisms):
            slowdown = 1.0
            for j, org_b in enumerate(self.organisms):
                if i == j:
                    continue
                dist = org_a.distance_to(org_b)
                if dist < Config.ORGANISM_MIN_DISTANCE * 0.5:
                    # Very close — strong competition
                    slowdown = min(slowdown, 0.2)
                elif dist < Config.ORGANISM_MIN_DISTANCE:
                    # Close — mild competition
                    t = dist / Config.ORGANISM_MIN_DISTANCE
                    slowdown = min(slowdown, 0.3 + 0.7 * t)
            org_a.growth_slowdown = slowdown

    # ============================================================
    # Display
    # ============================================================

    def display(self, py5) -> None:
        """Render all organisms and ecosystem connections.

        Draw order: seeds → organisms → connection lines.
        """
        # Draw pending seeds
        for seed in self.pending_seeds:
            seed.display(py5)

        # Draw connection lines between nearby organisms
        self._draw_connections(py5)

        # Draw organisms
        for org in self.organisms:
            org.display(py5)

    def _draw_connections(self, py5) -> None:
        """Draw subtle connection lines between nearby organisms.

        Lines form a "mycelial network" between organisms that are
        within CONNECT_DISTANCE of each other.
        """
        n = len(self.organisms)
        if n < 2:
            return

        py5.no_fill()
        for i in range(n):
            for j in range(i + 1, n):
                dist = self.organisms[i].distance_to(self.organisms[j])
                if dist < Config.ORGANISM_CONNECT_DISTANCE:
                    # Alpha: stronger for closer organisms
                    t = 1.0 - dist / Config.ORGANISM_CONNECT_DISTANCE
                    alpha = 30.0 * t * t
                    py5.stroke(
                        Config.Palette.MEMORY_DIM[0],
                        Config.Palette.MEMORY_DIM[1],
                        Config.Palette.MEMORY_DIM[2],
                        alpha,
                    )
                    py5.stroke_weight(0.5)
                    py5.line(
                        self.organisms[i].seed.x,
                        self.organisms[i].seed.y,
                        self.organisms[j].seed.x,
                        self.organisms[j].seed.y,
                    )

    # ============================================================
    # Info & Serialization
    # ============================================================

    def total_organisms(self) -> int:
        return len(self.organisms)

    def total_growth_points(self) -> int:
        return sum(org.growth.point_count() for org in self.organisms)

    def serialize(self) -> dict:
        return {
            "organisms": [org.serialize() for org in self.organisms],
            "pending_seeds": [s.serialize() for s in self.pending_seeds],
        }

    @classmethod
    def deserialize(cls, data: dict) -> "OrganismManager":
        mgr = cls()
        if "organisms" in data:
            mgr.organisms = [
                Organism.deserialize(d) for d in data["organisms"]
            ]
        if "pending_seeds" in data:
            mgr.pending_seeds = [
                MemorySeed.deserialize(d) for d in data["pending_seeds"]
            ]
        return mgr
