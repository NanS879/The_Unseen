"""
WorldBrain — the central intelligence of The Unseen.

The WorldBrain is the ONLY module allowed to modify world-level state:
    - Mood
    - Weather
    - Lighting
    - Organism strategy
    - Narrative
    - Evolution

All other modules (gesture, ability, particle, organism) read from
WorldState. The WorldBrain observes everything and adjusts the world
based on AI analysis or rule-based fallback.

Design:
    - WorldBrain holds an LLMInterface backend (DeepSeek or RuleEngine)
    - Runs analysis periodically (every 30s) — never on hot path
    - All decisions flow through WorldBrain.apply_analysis()
"""

import time
from typing import Optional

from ..world.world_state import W, WeatherType
from .llm_interface import LLMInterface, RuleEngine
from .behavior_reporter import BehaviorReporter


class WorldBrain:
    """Central world coordinator — the "consciousness" of the space.

    Only one instance. Created at startup, runs alongside py5 draw loop.
    """

    def __init__(self, llm: Optional[LLMInterface] = None) -> None:
        """Initialize the WorldBrain.

        Args:
            llm: AI backend. If None, uses RuleEngine (offline fallback).
        """
        self._llm: LLMInterface = llm or RuleEngine()
        self._reporter = BehaviorReporter()

        # Current world directives (set by AI analysis)
        self.current_mood: str = "Calm"
        self.current_weather: str = "Calm"
        self.current_lighting: str = "Neutral"
        self.current_organism_strategy: str = "Balanced"
        self.current_narrative: str = ""
        self.current_event: str = "Calm"

        # Background analysis — faster cycle for visible AI presence
        self._analysis_timer: float = 0.0
        self._analysis_interval: float = 10.0  # every 10s (faster feedback)
        self._session_analyzed: bool = False
        self._last_report: Optional[dict] = None

        # Pulse feedback — true for 2s after each analysis
        self.just_analyzed: bool = False
        self._pulse_timer: float = 0.0
        self._pulse_duration: float = 5.0    # narrative text visible for 5s (was 3s)

        # Narrative display state (for ambient text rendering)
        self.narrative_alpha: float = 0.0    # 0→1→0, driven by _pulse_timer

        # Weather lock — when brain sets weather, prevent WeatherSystem cycling
        self.weather_locked: bool = False
        self._weather_lock_timer: float = 0.0
        self._weather_lock_duration: float = 20.0  # brain weather holds for 20s

        # Evolution tracking
        self._evolution_proposals: list[dict] = []

    # ── Per-frame update (call from draw) ─────────────

    def update_frame(self, active_gesture: str, max_speed: float,
                     has_hands: bool) -> None:
        """Record one frame of behavior. Very cheap — no AI here.

        Args:
            active_gesture: Current gesture name (from GestureManager).
            max_speed: Maximum hand speed this frame.
            has_hands: Whether any hand is detected.
        """
        self._reporter.update_frame(active_gesture, max_speed, has_hands)

    def update(self, dt: float, v3_stats: dict, organism_count: int,
               energy: float, world_memory: dict) -> None:
        """Run periodic AI analysis with visible pulse feedback.

        Args:
            dt: Time delta.
            v3_stats: From V3 BehaviorAnalyzer.get_stats().
            organism_count: Current autonomous organism count.
            energy: Current energy level.
            world_memory: WorldMemory dict.
        """
        self._analysis_timer += dt

        # ── Pulse decay (narrative alpha drives text visibility) ──
        if self.just_analyzed:
            self._pulse_timer += dt
            # Fade in (0→0.5s), hold (0.5→4.5s), fade out (4.5→5.0s)
            t = self._pulse_timer
            if t < 0.5:
                self.narrative_alpha = t / 0.5
            elif t < 4.5:
                self.narrative_alpha = 1.0
            elif t < 5.0:
                self.narrative_alpha = 1.0 - (t - 4.5) / 0.5
            else:
                self.narrative_alpha = 0.0
                self.just_analyzed = False

        # ── Weather lock decay ──────────────────────────
        if self.weather_locked:
            self._weather_lock_timer += dt
            if self._weather_lock_timer >= self._weather_lock_duration:
                self.weather_locked = False

        # ── Run analysis ────────────────────────────────
        if (self._analysis_timer >= self._analysis_interval
                and not self._session_analyzed):
            self._analysis_timer = 0.0
            print(f"[AI] Running analysis (timer={self._analysis_interval:.0f}s) ...")
            self._run_analysis(v3_stats, organism_count, energy, world_memory)
            print(f"[AI] Result: mood={self.current_mood} weather={self.current_weather} "
                  f"lighting={self.current_lighting}")
            print(f"[AI] Narrative: \"{self.current_narrative}\"")

    # ── Session-end analysis ─────────────────────────

    def finalize_session(self, v3_stats: dict, organism_count: int,
                         energy: float, world_memory: dict) -> dict:
        """Run analysis at session end. Returns full result dict.

        Called once on exit — always runs, regardless of timer.
        """
        self._session_analyzed = True
        return self._run_analysis(v3_stats, organism_count, energy,
                                  world_memory)

    # ── Internal ─────────────────────────────────────

    def _run_analysis(self, v3_stats: dict, organism_count: int,
                      energy: float, world_memory: dict) -> dict:
        """Execute AI analysis pipeline."""
        # Build behavior report
        report = self._reporter.get_report(
            v3_stats, organism_count, energy, world_memory)
        self._last_report = report

        # Call AI
        result = self._llm.analyze_session(report)

        # Apply results
        if result:
            self._apply_analysis(result)
            self.just_analyzed = True       # trigger visible feedback
            self._pulse_timer = 0.0

        return result or {}

    def _apply_analysis(self, analysis: dict) -> None:
        """Apply AI analysis results to world state.

        This is the ONLY place that modifies world-level directives.
        """
        # ── Mood ───────────────────────────────────────
        self.current_mood = analysis.get("world_mood", "Calm")

        # ── Weather ────────────────────────────────────
        weather_map = {
            "Calm": WeatherType.CALM,
            "Wind": WeatherType.WIND,
            "Storm": WeatherType.STORM,
            "Aurora": WeatherType.AURORA,
            "Nebula": WeatherType.AURORA,   # map to Aurora
            "Bloom": WeatherType.AURORA,     # map to Aurora
        }
        weather_str = analysis.get("weather", "Calm")
        W.weather = weather_map.get(weather_str, WeatherType.CALM)
        W.weather_locked = True             # prevent WeatherSystem cycling
        self.current_weather = weather_str

        # ── Lighting ───────────────────────────────────
        self.current_lighting = analysis.get("lighting", "Neutral")

        # ── Organism strategy ──────────────────────────
        self.current_organism_strategy = analysis.get(
            "organism_strategy", "Balanced")

        # ── Narrative ──────────────────────────────────
        self.current_narrative = analysis.get("narrative", "")

        # ── Event ──────────────────────────────────────
        self.current_event = analysis.get("recommended_event", "Calm")

    # ── Queries ──────────────────────────────────────

    def get_last_report(self) -> Optional[dict]:
        return self._last_report

    def get_lighting_mult(self) -> float:
        """Return lighting intensity multiplier from current directive."""
        return {
            "Warm": 1.2, "Cool": 0.8, "Neutral": 1.0,
            "Soft": 0.9, "Dramatic": 1.4,
        }.get(self.current_lighting, 1.0)

    def get_lighting_warmth(self) -> float:
        """Return color warmth (0=cool, 1=warm)."""
        return {
            "Warm": 0.8, "Cool": 0.2, "Neutral": 0.5,
            "Soft": 0.6, "Dramatic": 0.9,
        }.get(self.current_lighting, 0.5)

    def get_organism_strategy_mult(self) -> dict[str, float]:
        """Return organism emotion multipliers for current strategy."""
        strategies = {
            "Curious":   {"curiosity": 1.5, "fear": 0.5, "affinity": 1.0},
            "Fearful":   {"curiosity": 0.5, "fear": 2.0, "affinity": 0.3},
            "Approach":  {"curiosity": 1.0, "fear": 0.3, "affinity": 1.5},
            "Observe":   {"curiosity": 1.3, "fear": 0.7, "affinity": 0.8},
            "Balanced":  {"curiosity": 1.0, "fear": 1.0, "affinity": 1.0},
        }
        return strategies.get(self.current_organism_strategy,
                              strategies["Balanced"])

    def propose_evolution(self) -> Optional[dict]:
        """Ask AI to propose world evolution. Called periodically."""
        if not self._last_report:
            return None

        context = {
            "world_age": W.world_age,
            "total_visits": W.total_visits,
            "total_organisms": W.total_organisms_created,
            "dominant_archetype": self._last_report.get(
                "user_behavior", {}).get("dominant_gesture", "none"),
        }
        return self._llm.propose_evolution(context)
