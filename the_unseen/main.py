"""
The Unseen — helper functions for py5 sketch.

All helpers reference the shared AppState singleton (S).
py5 callbacks live in __main__.py and also use S.
This decouples callbacks from helpers cleanly.
"""

import os

from .config import Config
from .state import S
from .perception.camera_tracker import CameraTracker
from .perception.hand_state import HandState
from .life.energy_manager import EnergyManager
from .life.behavior_analyzer import BehaviorAnalyzer
from .life.organism import OrganismManager
from .life.time_system import TimeSystem
from .life.persistence import save_state, load_state, delete_state
from .interaction.interaction_rules import InteractionRules
from .utils.logger import log, set_debug_mode


# ── Re-exports for __main__.py convenience ───────────
__all__ = [
    "camera_process", "smooth_hands", "init_organisms", "update_organisms",
    "update_ripples", "update_gestures", "draw_debug_overlay", "on_quit",
    "save_path", "log", "set_debug_mode", "delete_state",
]


def camera_process() -> list[HandState]:
    """Grab camera frame, run MediaPipe, update HandStates."""
    if S.camera is None or not S.camera.is_ready:
        return smooth_hands([])
    hands_data = S.camera.update()
    return smooth_hands(hands_data)


def smooth_hands(hands_data: list[dict]) -> list[HandState]:
    """Apply EMA smoothing to hand positions from camera data."""
    active: list[HandState] = []
    for h in hands_data:
        side = h["side"].lower()
        hs = S.hand_left if side == "left" else S.hand_right
        hs.raw_x = h["x"]
        hs.raw_y = h["y"]
        hs.raw_speed = h["speed"]
        hs.detected = h.get("detected", True)
        hs.has_data = True
        target_px = hs.raw_x * Config.WIDTH
        target_py = hs.raw_y * Config.HEIGHT
        hs.update_smoothing(
            Config.HAND_SMOOTHING, target_px, target_py, hs.raw_speed)
        active.append(hs)
    detected_sides = {h["side"].lower() for h in hands_data}
    for hs in (S.hand_left, S.hand_right):
        if hs.side not in detected_sides:
            hs.detected = False
            hs.raw_speed = 0.0
            hs.update_smoothing(
                Config.HAND_SMOOTHING_FADE,
                hs.default_x, hs.default_y, 0.0)
    return active


# ── V3 Organisms ────────────────────────────────────

def init_organisms() -> None:
    """Initialize or restore V3 organism subsystem."""
    path = save_path()
    if not S.fresh_start:
        try:
            data = load_state(path)
            if data:
                S.energy_manager = EnergyManager.deserialize(data["energy"])
                S.behavior_analyzer = BehaviorAnalyzer.deserialize(data["behavior"])
                S.organism_manager = OrganismManager.deserialize(data["ecosystem"])
                S.time_system = TimeSystem.deserialize(data["time_system"])
                log("V3", f"Restored: {S.organism_manager.total_organisms()} "
                    f"organisms, energy={S.energy_manager.energy:.1f}")
                return
        except Exception as e:
            log("V3", f"Load failed: {e}", "WARN")

    S.energy_manager = EnergyManager(initial_energy=30.0)
    S.behavior_analyzer = BehaviorAnalyzer()
    S.organism_manager = OrganismManager()
    S.time_system = TimeSystem()
    log("V3", "Fresh ecosystem — hold hand still to plant seeds")


def update_organisms(
    active_hands: list[HandState],
    has_hands: bool,
    max_speed: float,
    dt: float,
) -> None:
    """Update V3 subsystems for one frame."""
    if (S.energy_manager is None or S.behavior_analyzer is None
            or S.organism_manager is None or S.time_system is None):
        return
    dt = min(dt, 0.1)
    try:
        S.time_system.update(dt)
        tmod = S.time_system.get_modulators()
        S.energy_manager.update(has_hands, max_speed, dt)
        emod = S.energy_manager.get_multipliers()
        hand_data = [
            {"side": hs.side, "px": hs.px, "py": hs.py, "speed": hs.speed}
            for hs in active_hands]
        S.behavior_analyzer.update(dt, has_hands, hand_data)
        if has_hands and active_hands:
            primary = active_hands[0]
            seed = S.organism_manager.check_seed_creation(
                primary.px, primary.py, primary.speed, dt)
            if seed:
                S.behavior_analyzer.on_seed_created()
        growth_mult = tmod["growth"] * emod["growth"]
        hand_positions = [(hs.px, hs.py) for hs in active_hands]
        S.organism_manager.update(
            S.energy_manager, growth_mult, has_hands, hand_positions)
        S.autosave_timer += dt
        if S.autosave_timer >= Config.PERSISTENCE_AUTOSAVE_INTERVAL:
            S.autosave_timer = 0.0
            if save_state(save_path(), S.energy_manager,
                          S.behavior_analyzer, S.organism_manager,
                          S.time_system):
                log("V3", f"Saved — {S.organism_manager.total_organisms()} orgs",
                    "DEBUG")
    except Exception as e:
        import traceback
        log("V3", f"Error: {e}", "ERROR")
        traceback.print_exc()


# ── V4 Ripple + Fragment ────────────────────────────

def update_ripples(
    active_hands: list[HandState],
    has_hands: bool,
    max_speed: float,
    dt: float,
) -> None:
    """Update V4 interaction systems: ripples + fragments."""
    if S.ripple_manager is None or S.fragment_manager is None:
        return
    hand_positions = [(hs.px, hs.py) for hs in active_hands]
    if has_hands and max_speed > 0.05:
        for hs in active_hands:
            if hs.speed > 0.03:
                S.ripple_manager.spawn(
                    hs.px, hs.py,
                    strength=min(2.5, hs.speed * 15.0),
                    color=(Config.Palette.HAND_LEFT if hs.side == "left"
                           else Config.Palette.HAND_RIGHT))
    S.fragment_manager.update(
        dt, hand_positions, S.energy_manager, S.ripple_manager)
    if S.particle_manager:
        S.ripple_manager.update(S.particle_manager.bg_particles)
        S.ripple_manager.update(S.particle_manager.int_particles)
        S.ripple_manager.update(S.particle_manager.hl_particles)


# ── V4 Gesture ──────────────────────────────────────

def update_gestures(active_hands: list[HandState], dt: float) -> None:
    """Run gesture recognition + drive abilities."""
    if S.gesture_manager is None or S.camera is None:
        return
    landmarks = S.camera.get_landmarks()
    if not landmarks:
        return
    hand_data = [
        {"side": hs.side.capitalize(), "speed": hs.speed}
        for hs in active_hands]
    S.gesture_manager.update(landmarks, hand_data, dt)

    if S.ability_manager:
        active_gestures: dict[str, bool] = {}
        for side_key in ("left", "right"):
            gesture, conf = S.gesture_manager.get_active(side_key)
            active_gestures[gesture] = True
            if gesture != "none" and conf > 0.5:
                hs = S.hand_left if side_key == "left" else S.hand_right
                S.ability_manager.feed(gesture, side_key, hs.px, hs.py)
        S.ability_manager.update(dt, active_gestures)
        mood_mod = S.ability_manager.get_mood_modifiers()
        if S.flow_field:
            S.flow_field.flow_strength = Config.FLOW_STRENGTH * mood_mod["flow"]

    for side, gesture, _data in S.gesture_manager.get_events():
        if side == "both":
            hx, hy = Config.WIDTH / 2, Config.HEIGHT / 2
        elif side == "left":
            hx, hy = S.hand_left.px, S.hand_left.py
        else:
            hx, hy = S.hand_right.px, S.hand_right.py
        ability_gestures = {"open_palm", "fist", "pinch", "point",
                            "two_expand", "two_compress"}
        if gesture in ability_gestures and S.ability_manager:
            S.ability_manager.trigger(gesture, side, hx, hy)
        else:
            result = InteractionRules.apply(
                gesture, hx, hy, S.ripple_manager, S.energy_manager)
            if result:
                log("Gesture", f"{side} {gesture} → {result}", "DEBUG")


# ── Debug Overlay ───────────────────────────────────

def draw_debug_overlay(py5, active_hands: list[HandState]) -> None:
    """Render debug overlay."""
    if S.debug_overlay is None or S.particle_manager is None:
        return
    S.debug_overlay.draw(
        py5,
        particles=S.particle_manager.layer_counts(),
        organisms=(S.organism_manager.total_organisms()
                   if S.organism_manager else 0),
        growth_pts=(S.organism_manager.total_growth_points()
                    if S.organism_manager else 0),
        seeds=(len(S.organism_manager.pending_seeds)
               if S.organism_manager else 0),
        energy=S.energy_manager.energy if S.energy_manager else 0.0,
        state=S.space_state.state if S.space_state else "?",
        phase=S.time_system.get_phase_name() if S.time_system else "?",
        hands=[(hs.px, hs.py) for hs in active_hands],
        speeds=[hs.speed for hs in active_hands])
    y_extra = py5.height - 40
    if S.fragment_manager and S.fragment_manager.active_count > 0:
        py5.fill(200, 200, 150, 200)
        py5.text(f"Fragments: {S.fragment_manager.active_count}  "
                 f"Collected: {S.fragment_manager.collected_count}",
                 22, y_extra)
        y_extra -= 18
    if S.gesture_manager:
        left_g, left_c = S.gesture_manager.get_active("left")
        right_g, right_c = S.gesture_manager.get_active("right")
        if left_g != "none" or right_g != "none":
            py5.fill(150, 220, 150, 200)
            py5.text(f"L: {left_g} ({left_c:.0%})  R: {right_g} ({right_c:.0%})",
                     22, y_extra)
            y_extra -= 18
    if S.ability_manager:
        active = S.ability_manager.get_active_ability()
        mood = S.ability_manager.current_mood.value
        if active:
            py5.fill(200, 180, 255, 200)
            py5.text(f"Ability: {active.name} ({active.state.value})  "
                     f"Mood: {mood}", 22, y_extra)
            y_extra -= 18
    if S.feedback and S.feedback.time.time_scale < 0.95:
        py5.fill(255, 180, 100, 200)
        py5.text(f"Time: {S.feedback.time.time_scale:.2f}x", 22, y_extra)


# ── Quit ────────────────────────────────────────────

def on_quit(py5, after_save=None) -> None:
    """Clean shutdown: save, release camera, print report.

    Args:
        py5: py5 sketch instance.
        after_save: Optional callback called after state is saved.
    """
    try:
        if S.energy_manager and S.organism_manager:
            save_state(save_path(), S.energy_manager, S.behavior_analyzer,
                       S.organism_manager, S.time_system)
            log("Save", "State saved", "INFO")
    except Exception as e:
        log("Save", f"Failed: {e}", "ERROR")
    if S.camera:
        S.camera.stop()
    if S.behavior_analyzer:
        stats = S.behavior_analyzer.get_stats()
        orgs = S.organism_manager.total_organisms() if S.organism_manager else 0
        frags = S.fragment_manager.collected_count if S.fragment_manager else 0
        print("\n" + "=" * 50)
        print("  The Unseen — Today's Presence")
        print("=" * 50)
        print(f"  Duration:       {stats['session_duration']:.0f}s")
        print(f"  Distance:       {stats['total_distance']:.0f}px")
        print(f"  Still time:     {stats['total_dwell_time']:.1f}s")
        print(f"  Seeds planted:  {stats['seed_count']}")
        print(f"  Organisms:      {orgs}")
        print(f"  Fragments:      {frags}")
        print("=" * 50)
        # V8 World Brain hook
        if after_save:
            after_save(stats)
    log("Exit", "Goodbye.")
    py5.exit_sketch()


# ── Utils ───────────────────────────────────────────

def save_path() -> str:
    try:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            Config.PERSISTENCE_FILE)
    except Exception:
        return Config.PERSISTENCE_FILE
