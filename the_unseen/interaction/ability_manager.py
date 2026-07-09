"""
SpaceAbilityManager + 6 concrete Space Abilities.

Abilities:
    Connect  — Open Palm → calm connection between human and space
    Gather   — Fist → focus energy, particles converge
    Create   — Pinch → birth new digital life
    Guide    — Point → direct flow along finger
    Expand   — Two Hands Expand → space breathes outward
    Merge    — Two Hands Compress → organisms connect

Architecture:
    Gesture → SpaceAbilityManager → BaseAbility → SpaceResponse
"""

import math
from typing import Optional

from ..config import Config
from .ability_base import BaseAbility, SpaceMood, AbilityState
from ..feedback.audio_hook import audio


# ============================================================
# Connect — Open Palm
# ============================================================

class ConnectAbility(BaseAbility):
    """Establish a calm connection between human and space.

    Gesture: Open Palm
    Charge: 0.5s
    Mood: Calm
    Effects: Particles softly gather, glow increases, flow slows.
    """

    def __init__(self) -> None:
        super().__init__(name="Connect", charge_time=0.5, cooldown_time=3.0)

    def mood(self) -> SpaceMood:
        return SpaceMood.CALM

    def _on_activate(self) -> dict:
        return {
            "ability": "connect",
            "mood": "calm",
            "flow_mult": 0.6,
            "glow_mult": 0.7,
            "particle_attract": 0.5,
            "energy_gain": 3.0,
            "ripple_strength": 1.5,
            "ripple_color": Config.Palette.LIFE_BLUE,
        }

    def display_feedback(self, py5) -> None:
        if self.state == AbilityState.CHARGING:
            r = 20.0 + self.charge_progress * 60.0
            alpha = 40.0 + self.charge_progress * 60.0
            py5.no_stroke()
            py5.fill(100, 160, 255, alpha * 0.3)
            py5.circle(self.x, self.y, r * 2.0)
            py5.fill(150, 200, 255, alpha * 0.5)
            py5.circle(self.x, self.y, r)
        super().display_feedback(py5)


# ============================================================
# Gather — Fist
# ============================================================

class GatherAbility(BaseAbility):
    """Focus and gather space energy.

    Gesture: Closed Fist
    Charge: 1.0s
    Mood: Focused
    Effects: Flow compresses toward fist, energy accumulates,
             nearby seeds get growth boost.
    """

    def __init__(self) -> None:
        super().__init__(name="Gather", charge_time=1.0, cooldown_time=3.0)

    def mood(self) -> SpaceMood:
        return SpaceMood.FOCUSED

    def _on_activate(self) -> dict:
        return {
            "ability": "gather",
            "mood": "focused",
            "flow_mult": 1.4,
            "glow_mult": 1.3,
            "particle_attract": 1.2,
            "energy_gain": 5.0,
            "growth_boost": 2.0,
            "ripple_strength": 2.0,
            "ripple_color": Config.Palette.ENERGY_GOLD,
        }

    def display_feedback(self, py5) -> None:
        if self.state == AbilityState.CHARGING:
            # Converging energy lines
            rings = 3
            alpha = 30.0 + self.charge_progress * 80.0
            py5.no_fill()
            for i in range(rings):
                r = 15.0 + i * 15.0 + self.charge_progress * 40.0
                py5.stroke(255, 200, 80, alpha * (1.0 - i * 0.3))
                py5.stroke_weight(1.0 + self.charge_progress)
                py5.circle(self.x, self.y, r)
        super().display_feedback(py5)


# ============================================================
# Create — Pinch
# ============================================================

class CreateAbility(BaseAbility):
    """Create new digital life.

    Gesture: Pinch (thumb + index)
    Charge: 1.5s
    Mood: Hope
    Effects: Golden seed appears, grows into organism, ripple.
    """

    def __init__(self) -> None:
        super().__init__(name="Create", charge_time=1.5, cooldown_time=5.0)

    def mood(self) -> SpaceMood:
        return SpaceMood.HOPE

    def _on_activate(self) -> dict:
        return {
            "ability": "create",
            "mood": "hope",
            "create_seed": True,
            "seed_energy": Config.SEED_GROWTH_THRESHOLD,
            "energy_cost": Config.ENERGY_GROWTH_COST,
            "ripple_strength": 2.5,
            "ripple_color": Config.Palette.MEMORY_PURPLE,
        }

    def display_feedback(self, py5) -> None:
        if self.state == AbilityState.CHARGING:
            # Golden seed forming
            pulse = 0.6 + 0.4 * math.sin(py5.frame_count * 0.1)
            r = 5.0 + self.charge_progress * 30.0
            alpha = 80.0 + self.charge_progress * 120.0
            py5.no_stroke()
            # Outer glow
            py5.fill(255, 210, 80, alpha * 0.3 * pulse)
            py5.circle(self.x, self.y, r * 2.5)
            # Core
            py5.fill(255, 240, 200, alpha * pulse)
            py5.circle(self.x, self.y, r * 0.8)
        super().display_feedback(py5)


# ============================================================
# Guide — Point
# ============================================================

class GuideAbility(BaseAbility):
    """Guide space flow with pointing finger.

    Gesture: Point (index finger extended)
    Charge: 0.3s
    Mood: Curiosity
    Effects: Flow follows finger direction, particles trail.
    """

    def __init__(self) -> None:
        super().__init__(name="Guide", charge_time=0.3, cooldown_time=1.0)

    def mood(self) -> SpaceMood:
        return SpaceMood.CURIOSITY

    def _on_activate(self) -> dict:
        return {
            "ability": "guide",
            "mood": "curiosity",
            "flow_mult": 1.2,
            "glow_mult": 0.9,
            "ripple_strength": 0.6,
            "ripple_color": Config.Palette.GROWTH_PALE,
        }

    def display_feedback(self, py5) -> None:
        if self.state == AbilityState.CHARGING:
            # Small trail dots
            py5.no_stroke()
            alpha = 80.0 * self.charge_progress
            py5.fill(200, 210, 255, alpha)
            py5.circle(self.x, self.y, 4.0)
        super().display_feedback(py5)


# ============================================================
# Expand — Two Hands Expand
# ============================================================

class ExpandAbility(BaseAbility):
    """Expand the space outward — a deep breath.

    Gesture: Two Hands Expand
    Charge: 0.8s
    Mood: Freedom
    Effects: Flow slows dramatically, particles spread, ripples.
    """

    def __init__(self) -> None:
        super().__init__(name="Expand", charge_time=0.8, cooldown_time=4.0)

    def mood(self) -> SpaceMood:
        return SpaceMood.FREEDOM

    def _on_activate(self) -> dict:
        return {
            "ability": "expand",
            "mood": "freedom",
            "flow_mult": 0.5,
            "glow_mult": 0.6,
            "particle_spread": True,
            "ripple_strength": 1.8,
            "ripple_color": (180, 210, 255),
        }

    def display_feedback(self, py5) -> None:
        if self.state == AbilityState.CHARGING:
            r = 40.0 + self.charge_progress * 100.0
            alpha = 20.0 + self.charge_progress * 50.0
            py5.no_fill()
            py5.stroke(180, 210, 255, alpha)
            py5.stroke_weight(1.5)
            py5.circle(self.x, self.y, r)
        super().display_feedback(py5)


# ============================================================
# Merge — Two Hands Compress
# ============================================================

class MergeAbility(BaseAbility):
    """Merge two organisms — harmony through connection.

    Gesture: Two Hands Compress (holding)
    Charge: 2.0s (longest — requires commitment)
    Mood: Harmony
    Effects: Nearest organisms connect, energy flows between them.
    """

    def __init__(self) -> None:
        super().__init__(name="Merge", charge_time=2.0, cooldown_time=6.0)

    def mood(self) -> SpaceMood:
        return SpaceMood.HARMONY

    def _on_activate(self) -> dict:
        return {
            "ability": "merge",
            "mood": "harmony",
            "flow_mult": 0.8,
            "glow_mult": 1.1,
            "connect_organisms": True,
            "energy_gain": 10.0,
            "ripple_strength": 3.0,
            "ripple_color": Config.Palette.MEMORY_DIM,
        }

    def display_feedback(self, py5) -> None:
        if self.state == AbilityState.CHARGING:
            # Building connection bridge
            alpha = 30.0 + self.charge_progress * 100.0
            py5.stroke(160, 120, 240, alpha)
            py5.stroke_weight(1.0 + self.charge_progress * 2.0)
            py5.no_fill()
            # Vertical pulse line
            pulse_y = self.y + math.sin(py5.frame_count * 0.08) * 20.0
            r = 30.0 + self.charge_progress * 60.0
            py5.circle(self.x, pulse_y, r)
        super().display_feedback(py5)


# ============================================================
# Space Ability Manager
# ============================================================

class SpaceAbilityManager:
    """Central coordinator for all space abilities.

    Routes gesture events to abilities, manages ability lifecycle,
    tracks current space mood, and renders ability feedback.

    Usage:
        mgr = SpaceAbilityManager()
        mgr.trigger(gesture_name, side, x, y)  # on gesture event
        mgr.update(dt, gesture_states)          # each frame
        mgr.display(py5)                         # render feedback
        current_mood = mgr.current_mood          # affects space
    """

    def __init__(self) -> None:
        # Gesture → Ability mapping
        self._abilities: dict[str, BaseAbility] = {
            "open_palm":     ConnectAbility(),
            "fist":          GatherAbility(),
            "pinch":         CreateAbility(),
            "point":         GuideAbility(),
            "two_expand":    ExpandAbility(),
            "two_compress":  MergeAbility(),
        }

        # Track which gesture is currently held (for charging)
        self._held_gesture: str | None = None
        self._held_side: str = ""

        # Current space mood (persists after ability ends)
        self.current_mood: SpaceMood = SpaceMood.NEUTRAL
        self._mood_decay_timer: float = 0.0
        self._mood_duration: float = 5.0  # seconds mood persists

        # Feedback composer (set by main.py)
        self._composer = None
        self._ripple_manager = None
        self._energy_manager = None
        self._organism_manager = None

    def set_composer(self, composer) -> None:
        """Wire feedback composer for cinematic effects."""
        self._composer = composer

    def set_managers(self, ripple_manager=None, energy_manager=None,
                     organism_manager=None) -> None:
        """Wire managers for ability side-effects."""
        self._ripple_manager = ripple_manager
        self._energy_manager = energy_manager
        self._organism_manager = organism_manager

    # ── Trigger (one-shot, from gesture events) ──────

    def trigger(self, gesture: str, side: str, x: float, y: float) -> None:
        """One-shot trigger from gesture event (release-based).

        For ability gestures, prefer feed() which drives charging
        continuously while the gesture is held.
        """
        ability = self._abilities.get(gesture)
        if ability is None:
            return
        if ability.state != AbilityState.IDLE:
            return
        ability.start(x, y)

    def feed(self, gesture: str, side: str, x: float, y: float) -> None:
        """Feed gesture data to ability every frame while gesture is held.

        If the ability is IDLE, starts it. If already charging, updates
        position. This is the primary driver for ability charging.

        Args:
            gesture: Gesture type string.
            side: "left" or "right".
            x, y: Hand position in pixels.
        """
        ability = self._abilities.get(gesture)
        if ability is None:
            return

        if ability.state == AbilityState.IDLE:
            ability.start(x, y)
        elif ability.state in (AbilityState.PREPARING, AbilityState.CHARGING):
            # Update position to follow the hand
            ability.x = x
            ability.y = y

    # ── Update ───────────────────────────────────────

    def update(self, dt: float, active_gestures: dict[str, bool]) -> None:
        """Update all abilities each frame.

        Each ability charges while its corresponding gesture is held.
        When charge completes, ability activates and applies mood.

        Args:
            dt: Time delta.
            active_gestures: {"open_palm": True, "fist": False, ...}
                Whether each gesture is currently detected.
        """
        # Update mood decay
        if self.current_mood != SpaceMood.NEUTRAL:
            self._mood_decay_timer += dt
            if self._mood_decay_timer >= self._mood_duration:
                self.current_mood = SpaceMood.NEUTRAL

        # Update each ability — charge if held, cancel if not
        for gesture, ability in self._abilities.items():
            is_held = active_gestures.get(gesture, False)
            effects = ability.update(dt, is_held)

            if effects:
                # Ability activated — apply mood + spawn ripple
                mood_name = effects.get("mood", "neutral")
                for m in SpaceMood:
                    if m.value == mood_name:
                        self.current_mood = m
                        self._mood_decay_timer = 0.0
                        break

                # ── Cinematic feedback ──────────────────
                ability_name = effects.get("ability", "unknown")
                if self._composer:
                    self._composer.play(ability_name, ability.x, ability.y)
                    audio.on_ability(ability_name, "activate")

                # ── Ripple ──────────────────────────────
                if self._ripple_manager:
                    strength = effects.get("ripple_strength", 1.0)
                    color = effects.get("ripple_color", Config.Palette.LIFE_BLUE)
                    self._ripple_manager.spawn(ability.x, ability.y,
                                               strength=strength, color=color)

                # ── Energy ──────────────────────────────
                if self._energy_manager:
                    gain = effects.get("energy_gain", 0.0)
                    cost = effects.get("energy_cost", 0.0)
                    if gain > 0:
                        self._energy_manager.energy = min(
                            Config.ENERGY_MAX,
                            self._energy_manager.energy + gain)
                    if cost > 0:
                        self._energy_manager.consume(cost)

                # ── Create seed (for Create ability) ────
                if effects.get("create_seed") and self._organism_manager:
                    from ..life.memory_seed import MemorySeed
                    seed = MemorySeed(x=ability.x, y=ability.y, speed=0.0)
                    seed.dwell_time = 2.0
                    seed.energy = Config.SEED_GROWTH_THRESHOLD
                    self._organism_manager.pending_seeds.append(seed)

    # ── Display ──────────────────────────────────────

    def display(self, py5) -> None:
        """Render visual feedback for all active abilities."""
        for ability in self._abilities.values():
            if ability.state not in (AbilityState.IDLE, AbilityState.COOLDOWN):
                ability.display_feedback(py5)

    # ── Query ────────────────────────────────────────

    def get_active_ability(self) -> Optional[BaseAbility]:
        """Return the currently charging/active ability, if any."""
        for a in self._abilities.values():
            if a.is_active:
                return a
        return None

    def get_ability_state(self, gesture: str) -> Optional[str]:
        """Get state string for a gesture's ability."""
        a = self._abilities.get(gesture)
        return a.state.value if a else None

    def get_ability_states(self) -> dict[str, str]:
        """Get all ability states {gesture: state}."""
        return {g: a.state.value for g, a in self._abilities.items()}

    # ── Effects ──────────────────────────────────────

    def get_mood_modifiers(self) -> dict[str, float]:
        """Get flow/glow modifiers from current mood."""
        return {
            "flow": self.current_mood.flow_multiplier(),
            "glow": self.current_mood.glow_multiplier(),
            "color_shift": self.current_mood.color_shift(),
        }
