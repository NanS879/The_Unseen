"""
V8 World Consciousness — The AI's living body.

The Core:            central glowing orb — the AI's visual identity
BreathingEngine:     synchronized world-wide breath rhythm
ThinkingEngine:      visible "thinking" animation before decisions
DecisionManager:     periodic world-level decisions with visible impact
EmotionEngine:       AI mood that colors the entire world
Personality:        long-term character that evolves with world age
AttentionSystem:    AI "looks at" the user through Core + lighting + creatures
PresenceEngine:     overall artificial presence — makes the AI feel alive

All modules unified — they are facets of ONE consciousness, not separate systems.
"""

import math
import random
import time
from typing import Optional

from ..utils.easing import smoothstep


# ============================================================
# Breathing Engine — world-wide synchronized breath
# ============================================================

class BreathingEngine:
    """Global breath rhythm. Everything breathes together.

    Breath cycle: ~6 seconds (inhale ~3s, exhale ~3s).
    Outputs a 0→1→0 sine factor used by: Core, particles, lighting, camera.
    """

    CYCLE_SECONDS = 6.0

    def __init__(self) -> None:
        self._time: float = 0.0
        self._rate: float = 1.0          # 1.0 = normal, >1 = faster

    def update(self, dt: float) -> None:
        self._time += dt * self._rate

    def set_rate(self, rate: float) -> None:
        """Change breath speed. 0.5 = half speed, 2.0 = double."""
        self._rate = max(0.3, min(3.0, rate))

    @property
    def factor(self) -> float:
        """0.0 (end-exhale) → 1.0 (peak-inhale) → 0.0"""
        raw = math.sin(self._time * math.pi * 2.0 / self.CYCLE_SECONDS)
        return (raw + 1.0) / 2.0

    @property
    def inhale(self) -> bool:
        """True during inhale phase, False during exhale."""
        return math.sin(self._time * math.pi * 2.0 / self.CYCLE_SECONDS) > 0


# ============================================================
# Emotion Engine — AI mood affecting everything
# ============================================================

class EmotionEngine:
    """AI emotional state. All visual systems read from here.

    Emotions: calm, curious, hopeful, dreaming, lonely, excited, protective, silent.
    Each emotion has a "weight" — multiple can be active at once.
    Dominant emotion determines color/lighting/flow multipliers.
    """

    EMOTIONS = ["calm", "curious", "hopeful", "dreaming",
                "lonely", "excited", "protective", "silent"]

    MOOD_COLORS = {
        "calm":       (60, 100, 180, 10),
        "curious":    (140, 160, 240, 10),
        "hopeful":    (255, 200, 100, 12),
        "dreaming":   (180, 140, 220, 12),
        "lonely":     (60, 80, 140, 8),
        "excited":    (255, 180, 80, 15),
        "protective": (100, 180, 140, 10),
        "silent":     (30, 50, 100, 6),
    }

    def __init__(self) -> None:
        self._weights: dict[str, float] = {e: 0.0 for e in self.EMOTIONS}
        self._weights["calm"] = 0.5
        self._dominant: str = "calm"
        self._transition_speed: float = 0.3

    def set(self, emotion: str, weight: float) -> None:
        """Set an emotion weight and adjust others downward."""
        if emotion in self._weights:
            self._weights[emotion] = min(1.0, weight)
            for e in self._weights:
                if e != emotion:
                    self._weights[e] *= 0.7

    def shift_toward(self, target: str, dt: float) -> None:
        """Gradually shift dominant emotion toward target."""
        if target in self._weights:
            self._weights[target] = min(1.0,
                self._weights.get(target, 0.0) + self._transition_speed * dt)
            for e in self._weights:
                if e != target:
                    self._weights[e] = max(0.0,
                        self._weights[e] - self._transition_speed * 0.3 * dt)

    def update(self, dt: float) -> None:
        """Decay all emotions slowly toward calm."""
        for e in self._weights:
            if e != "calm":
                self._weights[e] = max(0.0, self._weights[e] - 0.01 * dt)
        self._weights["calm"] = min(1.0, self._weights["calm"] + 0.005 * dt)

        # Find dominant
        best_e, best_w = "calm", 0.0
        for e, w in self._weights.items():
            if w > best_w:
                best_e, best_w = e, w
        self._dominant = best_e

    @property
    def dominant(self) -> str:
        return self._dominant

    @property
    def intensity(self) -> float:
        """How strongly the dominant emotion is felt (0–1)."""
        return self._weights.get(self._dominant, 0.3)

    def mood_color(self) -> tuple:
        return self.MOOD_COLORS.get(self._dominant,
                                     self.MOOD_COLORS["calm"])

    def flow_multiplier(self) -> float:
        m = {"calm": 0.7, "curious": 1.2, "hopeful": 1.0, "dreaming": 0.5,
             "lonely": 0.4, "excited": 1.6, "protective": 0.9, "silent": 0.3}
        return m.get(self._dominant, 1.0)

    def glow_multiplier(self) -> float:
        m = {"calm": 0.8, "curious": 1.1, "hopeful": 1.3, "dreaming": 0.9,
             "lonely": 0.5, "excited": 1.5, "protective": 1.2, "silent": 0.3}
        return m.get(self._dominant, 1.0)

    def creature_multiplier(self) -> float:
        m = {"calm": 0.6, "curious": 1.5, "hopeful": 1.2, "dreaming": 0.8,
             "lonely": 0.4, "excited": 1.8, "protective": 1.1, "silent": 0.3}
        return m.get(self._dominant, 1.0)


# ============================================================
# Personality — long-term character
# ============================================================

class Personality:
    """Long-term AI character that evolves with world age and visits.

    Types: Observer, Dreamer, Creator, Guardian, Explorer.
    Shifts slowly — not every session.
    """

    TYPES = ["observer", "dreamer", "creator", "guardian", "explorer"]

    def __init__(self) -> None:
        self._type: str = "observer"
        self._stability: float = 0.8  # resistance to change
        self._evolution_timer: float = 0.0

    def update(self, dt: float, world_age: float, total_visits: int) -> None:
        """Evolve personality based on world age and visits."""
        self._evolution_timer += dt
        # Re-evaluate every 120s (2 min in-world time)
        if self._evolution_timer < 120.0:
            return
        self._evolution_timer = 0.0

        # Evolution logic
        if total_visits > 20 and world_age > 300:
            self._type = "guardian"
        elif total_visits > 10:
            self.shift("creator")
        elif world_age > 200:
            self.shift("dreamer")
        elif random.random() < 0.1:
            self.shift(random.choice(self.TYPES))

    def shift(self, target: str) -> None:
        if target in self.TYPES and random.random() > self._stability:
            self._type = target

    @property
    def current(self) -> str:
        return self._type

    def narrative_tone(self) -> str:
        """Personality influences narrative style."""
        tones = {
            "observer":  "watching, noticing, remembering",
            "dreamer":   "poetic, surreal, gentle",
            "creator":   "celebratory, generative, warm",
            "guardian":  "protective, reverent, deep",
            "explorer":  "curious, adventurous, bright",
        }
        return tones.get(self._type, "watching")


# ============================================================
# Attention System — AI "looks at" the user
# ============================================================

class AttentionSystem:
    """Tracks user position and directs AI focus.

    Core drifts toward user. Lighting highlights user area.
    Creatures orient toward user when affinity is high.
    """

    def __init__(self) -> None:
        self.user_x: float = 640.0
        self.user_y: float = 360.0
        self.user_present: bool = False
        self.focus: float = 0.0       # 0=scanning, 1=focused on user
        self._focus_target: float = 0.0

    def update(self, dt: float, user_x: float, user_y: float,
               has_hands: bool) -> None:
        """Update attention focus."""
        self.user_x = user_x
        self.user_y = user_y
        self.user_present = has_hands

        # Focus builds when user is present, decays when absent
        if has_hands:
            self._focus_target = min(1.0, self._focus_target + 0.5 * dt)
        else:
            self._focus_target = max(0.0, self._focus_target - 0.3 * dt)
        self.focus += (self._focus_target - self.focus) * min(1.0, 3.0 * dt)

    def core_offset(self) -> tuple[float, float]:
        """How much the Core should drift toward user."""
        if not self.user_present:
            return (0.0, 0.0)
        return (self.user_x - 640.0, self.user_y - 360.0)

    def spotlight_alpha(self) -> float:
        """Lighting intensity focused on user area."""
        return self.focus * 0.15


# ============================================================
# The Core — living central consciousness orb
# ============================================================

class WorldCore:
    """The Core — a living orb at the center of the world.

    Represents the AI's consciousness visually. Never static.
    Pulsates with breath. Glows with emotion. Drifts toward user.
    "Thinking" makes it glow brighter and pulse faster.
    """

    # Base position
    _base_x: float = 640.0
    _base_y: float = 360.0

    def __init__(self) -> None:
        self.x: float = self._base_x
        self.y: float = self._base_y
        self.radius: float = 40.0
        self.glow_radius: float = 120.0
        self.pulse_phase: float = 0.0
        self.color: tuple[int, int, int] = (120, 160, 240)

        # Thinking state
        self.thinking: bool = False
        self.think_progress: float = 0.0   # 0→1 during thinking
        self.think_duration: float = 1.5   # seconds per think cycle

        # Decision state
        self.just_decided: bool = False
        self.decision_flash: float = 0.0   # 0→1→0 flash after decision
        self.decision_label: str = ""

        # Organic motion
        self._wobble_x: float = 0.0
        self._wobble_y: float = 0.0
        self._wobble_phase: float = random.uniform(0, 6.28)

    def update(self, dt: float, breath: BreathingEngine,
               attention: AttentionSystem, emotion: EmotionEngine) -> None:
        """Update Core position and appearance."""
        # ── Position: drift toward user ────────────────
        off_x, off_y = attention.core_offset()
        target_x = self._base_x + off_x * 0.3
        target_y = self._base_y + off_y * 0.3
        self.x += (target_x - self.x) * min(1.0, 2.0 * dt)
        self.y += (target_y - self.y) * min(1.0, 2.0 * dt)

        # ── Organic wobble ─────────────────────────────
        self._wobble_phase += dt * 1.3
        self._wobble_x = math.cos(self._wobble_phase) * 8.0
        self._wobble_y = math.sin(self._wobble_phase * 1.4) * 6.0

        # ── Size: breath modulation ────────────────────
        breath_base = 35.0 + breath.factor * 15.0
        # Thinking makes it larger
        if self.thinking:
            self.think_progress = min(1.0,
                self.think_progress + dt / self.think_duration)
            self.radius = breath_base + self.think_progress * 20.0
            self.glow_radius = 120.0 + self.think_progress * 180.0
        else:
            self.think_progress = max(0.0,
                self.think_progress - dt * 2.0)
            self.radius = breath_base
            self.glow_radius = 120.0

        # ── Decision flash ─────────────────────────────
        if self.just_decided:
            self.decision_flash += dt * 0.6
            if self.decision_flash > 1.5:
                self.decision_flash = 0.0
                self.just_decided = False
                self.decision_label = ""

        # ── Color from emotion ─────────────────────────
        mood_color = emotion.mood_color()
        self.color = (mood_color[0], mood_color[1], mood_color[2])

    def start_thinking(self) -> None:
        self.thinking = True
        self.think_progress = 0.0

    def finish_thinking(self, decision_label: str) -> None:
        self.thinking = False
        self.just_decided = True
        self.decision_flash = 0.0
        self.decision_label = decision_label

    def display(self, py5, breath: BreathingEngine) -> None:
        """Render the Core."""
        bx = self.x + self._wobble_x
        by = self.y + self._wobble_y
        cr, cg, cb = self.color

        # ── Outer glow (largest, softest) ──────────────
        outer_a = 15.0 + breath.factor * 10.0
        py5.no_stroke()
        py5.fill(cr, cg, cb, outer_a)
        py5.circle(bx, by, self.glow_radius)

        # ── Mid glow ────────────────────────────────────
        mid_a = 40.0 + breath.factor * 25.0
        if self.thinking:
            mid_a += 40.0 * (0.5 + 0.5 * math.sin(py5.frame_count * 0.15))
        py5.fill(cr, cg, cb, mid_a)
        py5.circle(bx, by, self.radius * 2.5)

        # ── Inner orb ───────────────────────────────────
        inner_a = 150.0 + breath.factor * 60.0
        py5.fill(cr, cg, cb, inner_a)
        py5.circle(bx, by, self.radius * 1.2)

        # ── Hot center ──────────────────────────────────
        hot_a = 230.0 + breath.factor * 20.0
        if self.thinking:
            hot_a = 255.0
        py5.fill(255, 255, 255, hot_a)
        py5.circle(bx, by, self.radius * 0.4)

        # ── Thinking rings ──────────────────────────────
        if self.thinking and self.think_progress > 0.1:
            ring_count = 3
            for i in range(ring_count):
                phase = py5.frame_count * 0.05 + i * 2.0
                r = self.glow_radius * (0.3 + i * 0.25 + self.think_progress * 0.2)
                r += math.sin(phase) * 10.0
                alpha = 60.0 * self.think_progress * (1.0 - i * 0.3)
                py5.no_fill()
                py5.stroke(cr, cg, cb, alpha)
                py5.stroke_weight(1.5)
                py5.circle(bx, by, r)

        # ── Decision flash ──────────────────────────────
        if self.just_decided and self.decision_flash < 1.0:
            f = self.decision_flash
            flash_alpha = 120.0 * (1.0 - f) * f * 4.0
            py5.no_fill()
            py5.stroke(255, 255, 255, flash_alpha)
            py5.stroke_weight(3.0 * (1.0 - f))
            py5.circle(bx, by, self.glow_radius * (1.0 + f * 2.0))

            # Decision label
            if self.decision_label and f > 0.3 and f < 0.8:
                py5.fill(255, 255, 255, 150.0 * (1.0 - abs(f - 0.55) * 4.0))
                py5.text(self.decision_label, bx + 60, by - 10)


# ============================================================
# Decision Manager — periodic world-level decisions
# ============================================================

class DecisionManager:
    """Every 20-40s, the AI makes a visible decision about the world.

    Decision types: Bloom, Aurora, Silence, Dream, Migration, Harmony.
    Each decision triggers: Core flash, weather change, mood shift, narrative.
    """

    DECISIONS = ["Bloom", "Aurora", "Silence", "Dream", "Migration", "Harmony"]
    INTERVAL_MIN = 20.0
    INTERVAL_MAX = 40.0

    def __init__(self) -> None:
        self._timer: float = 0.0
        self._next_interval: float = random.uniform(self.INTERVAL_MIN,
                                                      self.INTERVAL_MAX)
        self._pending_decision: Optional[str] = None
        self._thinking_complete: bool = False

    def update(self, dt: float, core: WorldCore, emotion: EmotionEngine,
               personality: Personality, breath: BreathingEngine,
               has_hands: bool) -> Optional[dict]:
        """Check if it's time for a decision. Returns decision dict or None.

        When a decision is triggered: Core starts thinking → 1.5s later →
        decision fires → Core flashes → world changes.
        """
        self._timer += dt
        self._pending_decision = None

        if self._timer < self._next_interval:
            return None

        # ── Time for a decision ─────────────────────────
        self._timer = 0.0
        self._next_interval = random.uniform(self.INTERVAL_MIN,
                                              self.INTERVAL_MAX)

        # Start thinking
        if core and not core.thinking:
            core.start_thinking()

        # Pick decision based on context
        world_decisions = {
            "Bloom":    {"mood": "hopeful",   "breath_rate": 1.3,
                         "weather": "Aurora", "label": "✦ Bloom"},
            "Aurora":   {"mood": "dreaming",  "breath_rate": 0.8,
                         "weather": "Aurora", "label": "☾ Aurora"},
            "Silence":  {"mood": "silent",    "breath_rate": 0.4,
                         "weather": "Calm",   "label": "○ Silence"},
            "Dream":    {"mood": "dreaming",  "breath_rate": 0.9,
                         "weather": "Calm",   "label": "◇ Dream"},
            "Migration":{"mood": "excited",   "breath_rate": 1.6,
                         "weather": "Wind",   "label": "↗ Migration"},
            "Harmony":  {"mood": "protective","breath_rate": 1.1,
                         "weather": "Wind",  "label": "∞ Harmony"},
        }

        # User presence biases decisions
        if has_hands:
            weights = [0.25, 0.15, 0.15, 0.15, 0.15, 0.15]
        else:
            weights = [0.1, 0.15, 0.3, 0.3, 0.05, 0.1]

        choice = random.choices(list(world_decisions.keys()),
                                weights=weights, k=1)[0]
        self._pending_decision = choice
        info = world_decisions[choice]

        # Apply to world systems
        emotion.shift_toward(info["mood"], 0.5)
        breath.set_rate(info["breath_rate"])

        return {
            "decision": choice,
            "mood": info["mood"],
            "weather": info["weather"],
            "label": info["label"],
            "breath_rate": info["breath_rate"],
        }

    def complete_thinking(self, core: WorldCore) -> None:
        """Called when thinking animation duration is done."""
        if core and core.thinking and self._pending_decision:
            label = ""
            world_decisions = {
                "Bloom": "✦ Bloom", "Aurora": "☾ Aurora",
                "Silence": "○ Silence", "Dream": "◇ Dream",
                "Migration": "↗ Migration", "Harmony": "∞ Harmony",
            }
            label = world_decisions.get(self._pending_decision, "")
            core.finish_thinking(label)
            self._pending_decision = None


# ============================================================
# Presence Engine — ties everything together
# ============================================================

class PresenceEngine:
    """Orchestrates all consciousness modules into one cohesive presence.

    This is the ONLY module __main__.py needs to interact with
    for the entire AI presence system.
    """

    def __init__(self) -> None:
        self.breath = BreathingEngine()
        self.emotion = EmotionEngine()
        self.personality = Personality()
        self.attention = AttentionSystem()
        self.core = WorldCore()
        self.decisions = DecisionManager()

    def update(self, dt: float, has_hands: bool,
               user_x: float, user_y: float,
               world_age: float, total_visits: int,
               brain_mood: str = "") -> None:
        """Update all consciousness modules each frame.

        Args:
            dt: Time delta.
            has_hands: Whether user hands are detected.
            user_x, user_y: User hand position (or screen center if absent).
            world_age: World age in seconds.
            total_visits: Total lifetime visits.
            brain_mood: Optional mood override from WorldBrain AI.
        """
        # ── Breathing ──────────────────────────────────
        self.breath.update(dt)

        # ── Emotion ────────────────────────────────────
        if brain_mood:
            self.emotion.shift_toward(brain_mood.lower(), dt)
        self.emotion.update(dt)

        # ── Personality ────────────────────────────────
        self.personality.update(dt, world_age, total_visits)

        # ── Attention ──────────────────────────────────
        self.attention.update(dt, user_x, user_y, has_hands)

        # ── Core ───────────────────────────────────────
        self.core.update(dt, self.breath, self.attention, self.emotion)

        # ── Decisions ──────────────────────────────────
        decision = self.decisions.update(
            dt, self.core, self.emotion, self.personality,
            self.breath, has_hands)

        # When Core finishes thinking animation, complete the decision
        if self.core.thinking and self.core.think_progress > 0.95:
            self.decisions.complete_thinking(self.core)

    def display(self, py5) -> None:
        """Render the Core and all consciousness visuals."""
        self.core.display(py5, self.breath)

    # ── Queries for external systems ───────────────────

    def mood_color(self) -> tuple:
        return self.emotion.mood_color()

    def flow_mult(self) -> float:
        return self.emotion.flow_multiplier()

    def glow_mult(self) -> float:
        return self.emotion.glow_multiplier()

    def creature_mult(self) -> float:
        return self.emotion.creature_multiplier()

    def breath_factor(self) -> float:
        return self.breath.factor

    def spotlight_alpha(self) -> float:
        return self.attention.spotlight_alpha()

    def personality_type(self) -> str:
        return self.personality.current

    def dominant_emotion(self) -> str:
        return self.emotion.dominant
