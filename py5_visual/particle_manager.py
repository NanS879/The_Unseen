"""
Particle manager orchestrating three independent layers.

Layers:
    1. Background  (~1200) — slow drift, large soft particles, no trail, 2 glow layers
    2. Interaction (~600)  — main flow followers, trail, 3 glow layers
    3. Highlight   (~120)  — bright, fast, long trails, 3 glow layers

Each layer has its own Particle parameters and influence weight multiplier.
"""

from config import Config
from particle import Particle
from flow_field import FlowField
from influence_field import InfluenceField


class ParticleManager:
    """Orchestrator for three particle layers.

    Public interface:
        update(flow_field, influence_field, state_multipliers)
        display(py5, influence_field, trail_mult)
        total_count() → int
    """

    def __init__(self) -> None:
        """Create all three particle layers with per-layer config."""
        w, h = Config.WIDTH, Config.HEIGHT

        # ---- Layer 1: Background — slow, soft, no trail ----
        self.bg_particles: list[Particle] = [
            Particle(
                width=w, height=h, layer=Particle.LAYER_BG,
                max_speed=Config.PARTICLE_BG_SPEED_MAX,
                damping=Config.PARTICLE_BG_DAMPING,
                size_min=Config.PARTICLE_BG_SIZE_MIN,
                size_max=Config.PARTICLE_BG_SIZE_MAX,
                life_min=Config.PARTICLE_BG_LIFE_MIN,
                life_max=Config.PARTICLE_BG_LIFE_MAX,
                trail_length=Config.PARTICLE_BG_TRAIL_LENGTH,
                glow_layers=Config.PARTICLE_BG_GLOW_LAYERS,
                color_base=Config.Palette.BG_BASE,
                color_glow=Config.Palette.BG_GLOW,
            )
            for _ in range(Config.PARTICLE_BG_COUNT)
        ]

        # ---- Layer 2: Interaction — responsive, trails ----
        self.int_particles: list[Particle] = [
            Particle(
                width=w, height=h, layer=Particle.LAYER_INT,
                max_speed=Config.PARTICLE_INT_SPEED_MAX,
                damping=Config.PARTICLE_INT_DAMPING,
                size_min=Config.PARTICLE_INT_SIZE_MIN,
                size_max=Config.PARTICLE_INT_SIZE_MAX,
                life_min=Config.PARTICLE_INT_LIFE_MIN,
                life_max=Config.PARTICLE_INT_LIFE_MAX,
                trail_length=Config.PARTICLE_INT_TRAIL_LENGTH,
                glow_layers=Config.PARTICLE_INT_GLOW_LAYERS,
                color_base=Config.Palette.INT_BASE,
                color_glow=Config.Palette.INT_GLOW,
            )
            for _ in range(Config.PARTICLE_INT_COUNT)
        ]

        # ---- Layer 3: Highlight — bright, fast, long trails ----
        self.hl_particles: list[Particle] = [
            Particle(
                width=w, height=h, layer=Particle.LAYER_HL,
                max_speed=Config.PARTICLE_HL_SPEED_MAX,
                damping=Config.PARTICLE_HL_DAMPING,
                size_min=Config.PARTICLE_HL_SIZE_MIN,
                size_max=Config.PARTICLE_HL_SIZE_MAX,
                life_min=Config.PARTICLE_HL_LIFE_MIN,
                life_max=Config.PARTICLE_HL_LIFE_MAX,
                trail_length=Config.PARTICLE_HL_TRAIL_LENGTH,
                glow_layers=Config.PARTICLE_HL_GLOW_LAYERS,
                color_base=Config.Palette.HL_BASE,
                color_glow=Config.Palette.HL_GLOW,
            )
            for _ in range(Config.PARTICLE_HL_COUNT)
        ]

    # ============================================================
    # Update
    # ============================================================

    def update(
        self,
        flow_field: FlowField,
        influence_field: InfluenceField,
        flow_mult: float = 1.0,
        influence_mult: float = 1.0,
        trail_mult: float = 1.0,
    ) -> None:
        """Update all particles across all layers.

        Args:
            flow_field: FlowField instance.
            influence_field: InfluenceField instance.
            flow_mult: Global flow strength multiplier (from SpaceState).
            influence_mult: Global influence multiplier (from SpaceState).
            trail_mult: Global trail multiplier (from SpaceState) — unused
                in update, passed through to display.
        """
        self._update_layer(
            self.bg_particles, flow_field, influence_field,
            flow_mult, influence_mult * Config.INFLUENCE_WEIGHT_BG,
        )
        self._update_layer(
            self.int_particles, flow_field, influence_field,
            flow_mult, influence_mult * Config.INFLUENCE_WEIGHT_INT,
        )
        self._update_layer(
            self.hl_particles, flow_field, influence_field,
            flow_mult, influence_mult * Config.INFLUENCE_WEIGHT_HL,
        )

    def _update_layer(
        self,
        particles: list[Particle],
        flow_field: FlowField,
        influence_field: InfluenceField,
        flow_mult: float,
        influence_mult: float,
    ) -> None:
        """Update a single layer: forces → physics → respawn."""
        for p in particles:
            # Flow field
            fvx, fvy = flow_field.get_force(p.position[0], p.position[1])
            if flow_mult != 0.0:
                p.apply_force(fvx * flow_mult, fvy * flow_mult)

            # Influence
            if influence_mult != 0.0:
                ifx, ify = influence_field.get_force(
                    p.position[0], p.position[1]
                )
                p.apply_force(ifx * influence_mult, ify * influence_mult)

            p.update()

            if p.is_dead():
                p.respawn()

    # ============================================================
    # Display
    # ============================================================

    def display(
        self, py5, influence_field: InfluenceField, trail_mult: float = 1.0
    ) -> None:
        """Render all layers in order: BG → INT → HL.

        Perf optimizations:
        - BG layer: no influence lookup (barely affected anyway)
        - BG layer: reduced trail_mult
        - INT/HL: influence lookup for brightness boost
        """
        has_hands = influence_field.has_active_hands()

        # Background — no influence lookup, reduced trail
        for p in self.bg_particles:
            p.display(py5, influence=0.0, trail_mult=trail_mult * 0.3)

        # Interaction — full influence
        for p in self.int_particles:
            inf = influence_field.get_influence_at(
                p.position[0], p.position[1]
            ) if has_hands else 0.0
            p.display(py5, influence=inf, trail_mult=trail_mult)

        # Highlight — amplified
        for p in self.hl_particles:
            inf = influence_field.get_influence_at(
                p.position[0], p.position[1]
            ) if has_hands else 0.0
            p.display(py5, influence=inf, trail_mult=trail_mult * 1.5)

    # ============================================================
    # Info
    # ============================================================

    def total_count(self) -> int:
        return (
            len(self.bg_particles)
            + len(self.int_particles)
            + len(self.hl_particles)
        )

    def layer_counts(self) -> dict[str, int]:
        return {
            "background": len(self.bg_particles),
            "interaction": len(self.int_particles),
            "highlight": len(self.hl_particles),
        }
