"""
V8 AI Presence — the complete artificial consciousness of The Unseen.

Single module. Single responsibility: make the AI feel alive.
All previous scattered modules (world_brain, consciousness, brain_modules,
behavior_reporter) are unified here.

Architecture:
    WorldBrain — sole controller of WorldState. Only module that mutates
        mood, weather, lighting, organism strategy, narrative.
    MockBrain — seamless offline fallback. Same interface, zero latency.
    PresenceEngine — visual body of the AI. The Core, breathing, thinking,
        attention, emotion. Everything the user sees and feels.
    MemoryCurator — persistent world memory across sessions.
    NarrativeEngine — generates one poetic sentence per session end.

Usage:
    from .presence import WorldBrain, PresenceEngine, MemoryCurator
    brain = WorldBrain()        # auto-detects API from config.json
    presence = PresenceEngine() # visual Core + breath + emotion
    memory = MemoryCurator()    # long-term memory
"""

import json
import math
import os
import random
import time
import urllib.request
import urllib.error
from typing import Optional

from ..config_loader import cfg
from ..utils.easing import smoothstep
from ..world.world_state import W, WeatherType


# ============================================================
# Mock Brain — offline fallback (always available)
# ============================================================

class MockBrain:
    """Deterministic fallback when no API key is configured.

    Produces the same JSON structure as the AI would, based on
    simple heuristics of user behavior. Never random — all outputs
    map to clear rules. Zero latency, zero network.
    """

    @staticmethod
    def analyze(context: dict) -> dict:
        b = context.get("user_behavior", {})
        seeds = b.get("seed_count", 0)
        distance = b.get("total_distance", 0)
        dwell = b.get("total_dwell_time", 0)
        gestures = b.get("gesture_frequency", {})
        energy = context.get("world_state", {}).get("energy", 30)
        visits = context.get("memory", {}).get("total_visits", 1)

        # Archetype
        if seeds >= 3 and dwell > distance * 0.15:
            archetype = "Creator"
        elif distance > 3000 and gestures.get("swipe", 0) > 3:
            archetype = "Explorer"
        elif dwell > distance * 0.3:
            archetype = "Observer"
        elif gestures.get("open_palm", 0) > 3:
            archetype = "Connector"
        else:
            archetype = "Visitor"

        # Mood
        mood_map = {
            "Creator": "Hope", "Explorer": "Curiosity",
            "Observer": "Calm", "Connector": "Harmony", "Visitor": "Calm"}
        mood = mood_map.get(archetype, "Calm")

        # Weather
        if energy > 65: weather = "Aurora"
        elif energy > 45: weather = "Wind"
        elif archetype == "Explorer": weather = "Wind"
        else: weather = "Calm"

        # Lighting
        lighting_map = {"Hope": "Warm", "Curiosity": "Neutral",
                        "Calm": "Soft", "Harmony": "Warm"}
        lighting = lighting_map.get(mood, "Neutral")

        # Strategy
        strategy_map = {"Creator": "Curious", "Explorer": "Observe",
                        "Observer": "Approach", "Connector": "Approach",
                        "Visitor": "Balanced"}
        strategy = strategy_map.get(archetype, "Balanced")

        # Narrative
        narratives = {
            "Creator": "The forest grew because you paused.",
            "Explorer": "You stirred the invisible ocean.",
            "Observer": "Your stillness shaped the world.",
            "Connector": "A bridge formed between you and the unseen.",
            "Visitor": "You were here. The world has changed.",
        }
        narrative = narratives.get(archetype, narratives["Visitor"])
        if visits > 5: narrative = f"Visit {visits}. {narrative}"

        return {
            "user_archetype": archetype,
            "world_mood": mood,
            "weather": weather,
            "lighting": lighting,
            "organism_strategy": strategy,
            "narrative": narrative,
            "recommended_event": weather,
        }


# ============================================================
# LLM Brain — real API (DeepSeek/Doubao/any OpenAI-compatible)
# ============================================================

class LLMBrain:
    """Real API client. Reads config.json → language provider."""

    def __init__(self) -> None:
        lang = cfg.language
        self.available = lang.available
        self.api_key = lang.api_key
        self.model = lang.model
        self.endpoint = lang.endpoint
        self.cooldown = lang.cooldown
        self.timeout = lang.timeout
        self._last_call: float = 0.0
        self._cached: Optional[dict] = None

    @property
    def name(self) -> str:
        if not self.available: return "mock"
        return cfg.language.provider

    def analyze(self, context: dict) -> dict:
        """Call the API. Returns dict or falls back to MockBrain."""
        if not self.available:
            return MockBrain.analyze(context)
        now = time.time()
        if now - self._last_call < self.cooldown:
            return self._cached or MockBrain.analyze(context)

        system = (
            'You are the consciousness of The Unseen — an interactive art '
            'installation. A human visitor interacts through hand gestures. '
            'Analyze their behavior. Return ONLY valid JSON:\n'
            '{"user_archetype":"Creator|Explorer|Observer|Connector|Visitor",'
            '"world_mood":"Calm|Hope|Curiosity|Dream|Harmony|Bloom|Silence",'
            '"weather":"Calm|Wind|Storm|Aurora",'
            '"lighting":"Warm|Cool|Neutral|Soft|Dramatic",'
            '"organism_strategy":"Curious|Fearful|Approach|Observe|Balanced",'
            '"narrative":"one poetic sentence about this moment",'
            '"recommended_event":"Calm|Bloom|Aurora|Storm|Gust"}')

        try:
            payload = json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
                ],
                "temperature": 0.7, "max_tokens": 400,
            }).encode("utf-8")

            req = urllib.request.Request(
                self.endpoint, data=payload,
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {self.api_key}"})
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"].strip()
                if content.startswith("```"):
                    content = content.split("\n", 1)[1].rstrip("```")
                result = json.loads(content)
                self._last_call = time.time()
                self._cached = result
                print(f"[AI] API: {self.name}/{self.model} — "
                      f"{data.get('usage',{}).get('total_tokens','?')} tokens")
                return result
        except Exception as e:
            print(f"[AI] API error: {e} — using MockBrain")
            return MockBrain.analyze(context)


# ============================================================
# WorldBrain — sole controller of world state
# ============================================================

class WorldBrain:
    """The ONLY module that mutates world-level directives.

    All other modules (gesture, ability, particle, organism) READ from
    WorldState (W) and these directives. They never write.

    Directives: mood, weather, lighting, organism_strategy, narrative, event.
    Visual feedback: narrative_alpha drives text/pulse rendering.
    """

    MOOD_COLORS = {
        "Calm": (60, 100, 180, 12), "Hope": (255, 200, 100, 15),
        "Curiosity": (140, 160, 240, 12), "Dream": (180, 140, 220, 15),
        "Harmony": (120, 200, 160, 12), "Bloom": (255, 180, 200, 15),
        "Silence": (40, 60, 120, 8), "Lonely": (60, 80, 140, 12),
    }
    LIGHTING_MULTS = {"Warm": 1.2, "Cool": 0.8, "Neutral": 1.0,
                      "Soft": 0.9, "Dramatic": 1.4}
    LIGHTING_WARMTH = {"Warm": 0.8, "Cool": 0.2, "Neutral": 0.5,
                       "Soft": 0.6, "Dramatic": 0.9}
    STRATEGY_MULTS = {
        "Curious": {"curiosity": 1.5, "fear": 0.5, "affinity": 1.0},
        "Fearful": {"curiosity": 0.5, "fear": 2.0, "affinity": 0.3},
        "Approach": {"curiosity": 1.0, "fear": 0.3, "affinity": 1.5},
        "Observe":  {"curiosity": 1.3, "fear": 0.7, "affinity": 0.8},
        "Balanced": {"curiosity": 1.0, "fear": 1.0, "affinity": 1.0},
    }
    WEATHER_MAP = {"Calm": WeatherType.CALM, "Wind": WeatherType.WIND,
                   "Storm": WeatherType.STORM, "Aurora": WeatherType.AURORA}

    def __init__(self) -> None:
        # Backend
        self._llm = LLMBrain()
        self._backend_name = self._llm.name

        # Directives (current world state — what the AI decided)
        self.mood: str = "Calm"
        self.weather: str = "Calm"
        self.lighting: str = "Soft"
        self.strategy: str = "Balanced"
        self.narrative: str = ""
        self.event: str = "Calm"

        # Frame-by-frame behavior tracking
        self._gesture_counts: dict[str, int] = {}
        self._frame_count: int = 0
        self._speed_sum: float = 0.0
        self._still_frames: int = 0
        self._hand_frames: int = 0

        # Analysis timer
        self._timer: float = 0.0
        self._interval: float = 10.0  # seconds between AI analysis

        # Visual pulse after analysis
        self.just_analyzed: bool = False
        self.narrative_alpha: float = 0.0
        self._pulse_timer: float = 0.0

        # Weather lock (brain weather overrides natural cycle)
        self.weather_locked: bool = False
        self._weather_lock_timer: float = 0.0

    # ── Per-frame (call from draw, very cheap) ────────

    def feed(self, gesture: str, max_speed: float, has_hands: bool) -> None:
        """Record one frame of user behavior."""
        self._frame_count += 1
        if has_hands:
            self._hand_frames += 1
            self._speed_sum += max_speed
            if max_speed < 0.02:
                self._still_frames += 1
        if gesture != "none":
            self._gesture_counts[gesture] = (
                self._gesture_counts.get(gesture, 0) + 1)

    # ── Periodic analysis (call from draw) ────────────

    def update(self, dt: float, v3_stats: dict, organism_count: int,
               energy: float, memory: dict) -> None:
        """Run AI analysis when timer fires. Update pulse animation."""
        self._timer += dt

        # Pulse animation (drives narrative_alpha for rendering)
        if self.just_analyzed:
            self._pulse_timer += dt
            t = self._pulse_timer
            if t < 0.5:        self.narrative_alpha = t / 0.5
            elif t < 4.5:      self.narrative_alpha = 1.0
            elif t < 5.0:      self.narrative_alpha = 1.0 - (t - 4.5) / 0.5
            else:
                self.narrative_alpha = 0.0
                self.just_analyzed = False

        # Weather lock decay
        if self.weather_locked:
            self._weather_lock_timer += dt
            if self._weather_lock_timer >= 20.0:
                self.weather_locked = False

        # Timer check
        if self._timer < self._interval:
            return
        self._timer = 0.0

        # Build context JSON
        total_frames = max(1, self._frame_count)
        gesture_total = max(1, sum(self._gesture_counts.values()))
        context = {
            "user_behavior": {
                "session_duration": v3_stats.get("session_duration", 0),
                "total_distance": v3_stats.get("total_distance", 0),
                "avg_speed": v3_stats.get("avg_speed", 0),
                "activity_ratio": round(self._hand_frames / total_frames, 3),
                "still_ratio": round(self._still_frames / max(1, self._hand_frames), 3),
                "seed_count": v3_stats.get("seed_count", 0),
                "interaction_count": v3_stats.get("interaction_count", 0),
                "gesture_frequency": {g: round(c / gesture_total, 3)
                                      for g, c in self._gesture_counts.items()},
            },
            "world_state": {"organism_count": organism_count, "energy": energy},
            "memory": memory,
        }

        # Run analysis
        print(f"[AI] Analyzing ({self._backend_name})...")
        result = self._llm.analyze(context)
        if result:
            self._apply(result)

    def finalize(self, v3_stats: dict, organism_count: int,
                 energy: float, memory: dict) -> dict:
        """Force analysis on session end. Always runs."""
        total_frames = max(1, self._frame_count)
        gesture_total = max(1, sum(self._gesture_counts.values()))
        context = {
            "user_behavior": {
                "session_duration": v3_stats.get("session_duration", 0),
                "total_distance": v3_stats.get("total_distance", 0),
                "avg_speed": v3_stats.get("avg_speed", 0),
                "seed_count": v3_stats.get("seed_count", 0),
                "interaction_count": v3_stats.get("interaction_count", 0),
                "gesture_frequency": {g: round(c / gesture_total, 3)
                                      for g, c in self._gesture_counts.items()},
            },
            "world_state": {"organism_count": organism_count, "energy": energy},
            "memory": memory,
        }
        result = self._llm.analyze(context)
        if result:
            self._apply(result)
        return result or {}

    def _apply(self, analysis: dict) -> None:
        """Apply AI decision to world directives."""
        self.mood = analysis.get("world_mood", "Calm")
        self.lighting = analysis.get("lighting", "Soft")
        self.strategy = analysis.get("organism_strategy", "Balanced")
        self.narrative = analysis.get("narrative", "")
        self.event = analysis.get("recommended_event", "Calm")

        weather_str = analysis.get("weather", "Calm")
        self.weather = weather_str
        W.weather = self.WEATHER_MAP.get(weather_str, WeatherType.CALM)
        W.weather_locked = True
        self.weather_locked = True
        self._weather_lock_timer = 0.0

        # Trigger visual pulse
        self.just_analyzed = True
        self._pulse_timer = 0.0

        print(f"[AI] mood={self.mood} weather={self.weather} "
              f"lighting={self.lighting} strategy={self.strategy}")
        print(f"[AI] \"{self.narrative}\"")

    # ── Query methods (used by renderer) ──────────────

    def mood_color(self) -> tuple:
        return self.MOOD_COLORS.get(self.mood, self.MOOD_COLORS["Calm"])

    def lighting_mult(self) -> float:
        return self.LIGHTING_MULTS.get(self.lighting, 1.0)

    def lighting_warmth(self) -> float:
        return self.LIGHTING_WARMTH.get(self.lighting, 0.5)

    def strategy_mult(self) -> dict:
        return self.STRATEGY_MULTS.get(self.strategy,
                self.STRATEGY_MULTS["Balanced"])


# ============================================================
# Presence Engine — the AI's visual body
# ============================================================

class PresenceEngine:
    """The physical manifestation of the AI — The Core, breath, emotion,
    attention, and thinking animation. Everything the user sees and feels.

    Usage:
        presence = PresenceEngine()
        presence.update(dt, has_hands, user_x, user_y, brain)
        presence.display(py5)
    """

    def __init__(self) -> None:
        # ── The Core ──────────────────────────────────
        self.x: float = 640.0
        self.y: float = 360.0
        self.radius: float = 40.0
        self.glow_radius: float = 120.0
        self.color: tuple[int, int, int] = (120, 160, 240)

        # Organic motion
        self._wobble_x: float = 0.0
        self._wobble_y: float = 0.0
        self._wobble_phase: float = random.uniform(0, 6.28)

        # ── Breathing ─────────────────────────────────
        self._breath_time: float = 0.0
        self._breath_rate: float = 1.0  # 1.0 = normal

        # ── Thinking ──────────────────────────────────
        self.thinking: bool = False
        self._think_progress: float = 0.0

        # ── Emotion ───────────────────────────────────
        self._emotion: str = "calm"
        self._emotion_intensity: float = 0.5
        self._emotion_target: str = "calm"

        # ── Attention ─────────────────────────────────
        self._user_x: float = 640.0
        self._user_y: float = 360.0
        self._user_present: bool = False
        self._focus: float = 0.0

        # ── Decision flash ────────────────────────────
        self._flash_alpha: float = 0.0
        self._flash_label: str = ""

        # ── Initiative events ─────────────────────────
        self._initiative_timer: float = 0.0
        self._initiative_interval: float = 30.0
        self._initiative_event: Optional[str] = None

    # ── Update ────────────────────────────────────────

    def update(self, dt: float, has_hands: bool,
               user_x: float, user_y: float,
               brain: WorldBrain) -> None:
        """Update every frame. Called from draw()."""
        # ── Breathing ─────────────────────────────────
        self._breath_time += dt * self._breath_rate

        # ── Attention (follow user) ───────────────────
        self._user_x = user_x
        self._user_y = user_y
        self._user_present = has_hands
        target_focus = 1.0 if has_hands else 0.0
        self._focus += (target_focus - self._focus) * min(1.0, 2.0 * dt)

        # Core drifts toward user
        target_x = 640.0 + (user_x - 640.0) * 0.3 * self._focus
        target_y = 360.0 + (user_y - 360.0) * 0.3 * self._focus
        self.x += (target_x - self.x) * min(1.0, 2.0 * dt)
        self.y += (target_y - self.y) * min(1.0, 2.0 * dt)

        # ── Organic wobble ────────────────────────────
        self._wobble_phase += dt * 1.3
        self._wobble_x = math.cos(self._wobble_phase) * 8.0
        self._wobble_y = math.sin(self._wobble_phase * 1.4) * 6.0

        # ── Emotion ───────────────────────────────────
        if brain.mood.lower() != self._emotion_target:
            self._emotion_target = brain.mood.lower()
            self._breath_rate = {"calm": 0.8, "hope": 1.2, "curiosity": 1.3,
                                 "dream": 0.6, "harmony": 1.0, "bloom": 1.4,
                                 "silence": 0.4, "lonely": 0.5}.get(
                                     brain.mood.lower(), 1.0)
        # Transition toward target
        if self._emotion != self._emotion_target:
            self._emotion_intensity = max(0.0, self._emotion_intensity - 0.5 * dt)
            if self._emotion_intensity < 0.05:
                self._emotion = self._emotion_target
                self._emotion_intensity = 0.0
        self._emotion_intensity = min(1.0, self._emotion_intensity + 0.3 * dt)

        # ── Thinking (from brain analysis) ────────────
        if brain.just_analyzed and brain.narrative_alpha > 0.95:
            if not self.thinking:
                self.thinking = True
                self._think_progress = 0.0
        if self.thinking:
            self._think_progress = min(1.0, self._think_progress + dt * 0.8)
        if brain.narrative_alpha < 0.1 and self._think_progress > 0.9:
            self.thinking = False
            self._think_progress = 0.0

        # ── Decision flash ────────────────────────────
        if brain.just_analyzed and brain.narrative_alpha > 0.95:
            if self._flash_alpha < 0.1 and brain.event:
                self._flash_alpha = 1.0
                self._flash_label = brain.event
        self._flash_alpha = max(0.0, self._flash_alpha - dt * 0.4)

        # ── Color from brain mood ─────────────────────
        mc = brain.mood_color()
        self.color = (mc[0], mc[1], mc[2])

        # ── Initiative events ─────────────────────────
        self._initiative_timer += dt
        if self._initiative_timer > self._initiative_interval:
            self._initiative_timer = 0.0
            events = ["Bloom", "Aurora", "Dream", "Silence"]
            self._initiative_event = random.choice(events)

    # ── Display ───────────────────────────────────────

    @property
    def breath_factor(self) -> float:
        raw = math.sin(self._breath_time * math.pi * 2.0 / 6.0)
        return (raw + 1.0) / 2.0

    def display(self, py5, brain: WorldBrain) -> None:
        """Render The Core — simplified for performance."""
        bx = self.x + self._wobble_x
        by = self.y + self._wobble_y
        cr, cg, cb = self.color
        breath = self.breath_factor
        w, h = py5.width, py5.height

        # Outer aura
        aura_r = self.glow_radius + breath * 30.0 + (self._think_progress * 60.0 if self.thinking else 0)
        py5.no_stroke()
        py5.fill(cr, cg, cb, 8 + int(breath * 6))
        py5.circle(bx, by, aura_r)

        # Core orb
        core_r = self.radius + breath * 8.0
        py5.fill(cr, cg, cb, 140 + int(breath * 50))
        py5.circle(bx, by, core_r * 1.1)

        # Hot center (point — cheapest)
        py5.stroke(255, 255, 255, 220 + int(breath * 30))
        py5.stroke_weight(max(1, core_r * 0.3))
        py5.point(bx, by)

        # AI status badge (top-right)
        py5.no_stroke()
        dot_color = (80, 255, 150)
        py5.fill(*dot_color, 200)
        py5.circle(w - 15, 15, 5)
        py5.fill(*dot_color, 160)
        py5.text_size(11)
        label = f"AI: {brain.mood}"
        tw = py5.text_width(label)
        py5.text(label, w - 20 - tw, 20)

        # Narrative text (only when active)
        if brain.just_analyzed and brain.narrative_alpha > 0.05 and brain.narrative:
            a = brain.narrative_alpha
            py5.no_stroke()
            py5.fill(0, 0, 0, int(a * 80))
            py5.rect(w * 0.1, h - 75, w * 0.8, 40)
            py5.fill(255, 255, 255, int(200 * a))
            py5.text_size(15)
            py5.text_align(py5.CENTER)
            py5.text(brain.narrative, w / 2, h - 48)
            py5.text_align(py5.LEFT)


# ============================================================
# Memory Curator — persistent world memory
# ============================================================

class MemoryCurator:
    """Long-term world memory persisted as world_memory.json."""

    FILE = "world_memory.json"

    def __init__(self) -> None:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._path = os.path.join(root, self.FILE)
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"first_visit": time.time(), "total_visits": 0,
                    "favorite_ability": "none", "ability_counts": {},
                    "total_organisms_ever": 0, "peak_energy": 0.0,
                    "longest_session_s": 0, "narrative_history": []}

    def save(self) -> None:
        try:
            with open(self._path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except OSError: pass

    def record_visit(self) -> None:
        self._data["total_visits"] += 1

    def record_ability(self, ability: str) -> None:
        if ability != "none":
            self._data["ability_counts"][ability] = (
                self._data["ability_counts"].get(ability, 0) + 1)
            if self._data["ability_counts"]:
                self._data["favorite_ability"] = max(
                    self._data["ability_counts"],
                    key=self._data["ability_counts"].get)

    def record_session(self, stats: dict, narrative: str) -> None:
        d = stats.get("session_duration", 0)
        if d > self._data["longest_session_s"]:
            self._data["longest_session_s"] = d
        if narrative:
            self._data["narrative_history"].append(
                {"time": time.time(), "narrative": narrative})
            if len(self._data["narrative_history"]) > 20:
                self._data["narrative_history"] = (
                    self._data["narrative_history"][-20:])

    def record_peak(self, organisms: int, energy: float) -> None:
        if organisms > self._data["total_organisms_ever"]:
            self._data["total_organisms_ever"] = organisms
        if energy > self._data["peak_energy"]:
            self._data["peak_energy"] = energy

    def get(self) -> dict:
        return dict(self._data)

    def visit_count(self) -> int:
        return self._data.get("total_visits", 0)

    def days_since_first(self) -> int:
        return int((time.time() - self._data.get("first_visit", time.time())) / 86400)

    def last_narrative(self) -> str:
        h = self._data.get("narrative_history", [])
        return h[-1].get("narrative", "") if h else ""
