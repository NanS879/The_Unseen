"""
The Unseen — Interactive Generative Art Installation.

python -m the_unseen [--fresh] [--release] [--camera]

Keys: D=debug  F=FPS  R=release  Q=quit+report
"""

import py5

from .config import Config
from .state import S
from .perception.camera_tracker import CameraTracker
from .simulation.flow_field import FlowField
from .simulation.influence_field import InfluenceField
from .simulation.particle_manager import ParticleManager
from .simulation.space_state import SpaceState
from .interaction.ripple import RippleManager
from .interaction.fragment import FragmentManager
from .interaction.gesture_manager import GestureManager
from .interaction.ability_manager import SpaceAbilityManager
from .feedback.feedback_composer import FeedbackComposer
from .feedback.procedural_bg import ProceduralBackground
from .feedback.visual_system import DepthManager, BreathingCamera, StateLighting
from .feedback.camera_background import CameraBgManager
from .ui.render_utils import draw_hand_aura, draw_startup_hint
from .ui.debug_overlay import DebugOverlay
from .utils.logger import log, set_debug_mode
from .life.persistence import delete_state

from .main import (
    camera_process, init_organisms, update_organisms,
    update_ripples, update_gestures, draw_debug_overlay,
    on_quit, save_path,
)

from .world.world_state import W, WeatherType
from .world.organism_ai import OrganismAI
from .world.living_world import (
    EcosystemManager, WeatherSystem, WorldMemory, ExhibitionController,
)

from .ai.presence import WorldBrain, PresenceEngine, MemoryCurator


# ============================================================
# Global switches
# ============================================================
_use_camera_bg: bool = False     # --camera flag enables camera background


# ============================================================
# py5 Callbacks
# ============================================================

def setup() -> None:
    """Initialize all subsystems."""
    global _brain, _memory, _presence, _camera_bg

    py5.size(Config.WIDTH, Config.HEIGHT, py5.P2D)
    py5.color_mode(py5.RGB, 255)
    py5.frame_rate(60)
    py5.window_title("The Unseen — 不可见")
    py5.background(0)

    # Camera for hand tracking
    S.camera = CameraTracker(process_every_n=3)
    if not S.camera.start():
        log("Camera", "No camera — demo mode", "WARN")

    S.flow_field = FlowField()
    S.influence_field = InfluenceField()
    S.particle_manager = ParticleManager()
    S.space_state = SpaceState()
    S.flow_field.update(0.0)

    init_organisms()

    WorldMemory.deserialize({})
    if S.organism_manager:
        for org in S.organism_manager.organisms:
            W.register_organism(OrganismAI(org, org.seed.x, org.seed.y))

    S.debug_overlay = DebugOverlay()
    S.debug_overlay.set_font(py5.create_font("Monospaced", 10))
    S.ripple_manager = RippleManager()
    S.fragment_manager = FragmentManager()
    S.gesture_manager = GestureManager()
    S.ability_manager = SpaceAbilityManager()
    S.feedback = FeedbackComposer()
    S.ability_manager.set_composer(S.feedback)
    S.ability_manager.set_managers(
        ripple_manager=S.ripple_manager,
        energy_manager=S.energy_manager,
        organism_manager=S.organism_manager)

    S.bg_renderer = ProceduralBackground()
    S.depth_mgr = DepthManager()
    S.breath_cam = BreathingCamera()
    S.state_light = StateLighting()

    _brain = WorldBrain()
    _memory = MemoryCurator()
    _memory.record_visit()
    _presence = PresenceEngine()
    _camera_bg = CameraBgManager()

    log("Brain", f"{'Live AI' if _brain._llm.available else 'Mock AI'} "
        f"({_brain._backend_name}) — Visit #{_memory.visit_count()}")
    log("Init", "D=debug  F=FPS  R=release  Q=quit")

    S.frame_start_ms = py5.millis()


def draw() -> None:
    """Main loop — heavily optimized."""
    if S.flow_field is None or S.particle_manager is None:
        return
    if S.space_state is None or S.influence_field is None:
        return

    # Timing
    now_ms = py5.millis()
    dt = 1.0 / 60.0
    frame_time = 16.7
    if S.frame_start_ms > 0:
        dt_raw = (now_ms - S.frame_start_ms) / 1000.0
        if 0 < dt_raw < 0.5:
            dt = dt_raw
            frame_time = dt_raw * 1000.0
            S.fps_display += (1.0 / dt - S.fps_display) * 0.1
    S.frame_start_ms = now_ms

    # V5 Time effects
    if S.feedback:
        dt = S.feedback.apply_dt(dt)
        S.feedback.update(dt)

    # ── Background (camera or procedural) ──────────────
    if _use_camera_bg and S.camera:
        _camera_bg.set_filter_from_mood(_brain.mood)
        _camera_bg.draw_background(py5, S.camera)
    else:
        py5.background(5, 10, 25)

    # Camera + Hands
    active_hands = camera_process()
    has_hands = len(active_hands) > 0
    max_speed = max((hs.speed for hs in active_hands), default=0.0)

    # Gestures + AI feed
    if S.gesture_manager and S.camera:
        update_gestures(active_hands, dt)

    _brain.feed(_get_gesture(active_hands), max_speed, has_hands)
    S.space_state.update(has_hands, max_speed)

    # Motion blur + procedural atmosphere (combined into one pass)
    py5.no_stroke()
    alpha = 4 if not has_hands else (8 if max_speed < 0.06 else 12)
    py5.fill(0, 0, 0, alpha)
    py5.rect(0, 0, Config.WIDTH, Config.HEIGHT)

    # Flow Field
    t = now_ms / 1000.0
    interval = max(1, int(Config.FLOW_UPDATE_INTERVAL / S.space_state.flow_multiplier))
    if py5.frame_count % interval == 0:
        S.flow_field.time_scale = Config.FLOW_NOISE_SPEED * S.space_state.flow_multiplier
        S.flow_field.update(t)

    # Influence
    S.influence_field.update([
        (hs.px, hs.py, hs.speed, hs.dx, hs.dy) for hs in active_hands])

    # Particles
    S.particle_manager.update(
        S.flow_field, S.influence_field,
        flow_mult=S.space_state.flow_multiplier,
        influence_mult=S.space_state.influence_multiplier)
    S.particle_manager.display(py5, S.influence_field)

    # V3 Organisms
    if Config.V3_ENABLED and S.organism_manager is not None:
        update_organisms(active_hands, has_hands, max_speed, dt)
        S.organism_manager.display(py5)

    # Ripple + Fragment
    if S.ripple_manager and S.fragment_manager:
        update_ripples(active_hands, has_hands, max_speed, dt)
        S.ripple_manager.display(py5)
        S.fragment_manager.display(py5)

    if S.ability_manager:
        S.ability_manager.display(py5)

    # Living World + AI Brain
    _update_world(active_hands, has_hands, dt, py5)

    # AI Presence (Core + mood)
    ux = active_hands[0].px if active_hands else Config.WIDTH / 2
    uy = active_hands[0].py if active_hands else Config.HEIGHT / 2
    _presence.update(dt, has_hands, ux, uy, _brain)
    _presence.display(py5, _brain)

    # Hand Auras
    for hs in active_hands:
        color = (Config.Palette.HAND_LEFT if hs.side == "left"
                 else Config.Palette.HAND_RIGHT)
        draw_hand_aura(py5, hs.px, hs.py, hs.speed, S.space_state.state, color)

    # Startup Hint
    if py5.frame_count < 300 or not has_hands:
        draw_startup_hint(
            py5, has_hands,
            has_data=S.hand_left.has_data or S.hand_right.has_data,
            organism_count=(S.organism_manager.total_organisms()
                            if S.organism_manager else 0),
            seed_count=(len(S.organism_manager.pending_seeds)
                        if S.organism_manager else 0),
            frame_count=py5.frame_count)

    # Debug
    if S.debug_overlay is not None:
        S.debug_overlay.update(frame_time)
        if S.debug_overlay.visible or S.debug_overlay.fps_only:
            draw_debug_overlay(py5, active_hands)


def key_pressed() -> None:
    if py5.key in ('d', 'D') and S.debug_overlay:
        S.debug_overlay.toggle()
    elif py5.key in ('f', 'F') and S.debug_overlay:
        S.debug_overlay.toggle_fps()
    elif py5.key in ('r', 'R'):
        S.release_mode = not S.release_mode
        set_debug_mode(not S.release_mode)
    elif py5.key in ('c', 'C'):
        global _use_camera_bg
        _use_camera_bg = not _use_camera_bg
        log("Camera", f"Camera background: {'ON' if _use_camera_bg else 'OFF'}")
    elif py5.key in ('q', 'Q'):
        _quit_with_brain()


def exiting() -> None:
    _quit_with_brain()


# ============================================================
# Helpers
# ============================================================

def _get_gesture(active_hands: list) -> str:
    if S.gesture_manager:
        g, _ = S.gesture_manager.get_active("right")
        if g == "none":
            g, _ = S.gesture_manager.get_active("left")
        return g
    return "none"


def _quit_with_brain() -> None:
    def after_save(stats):
        orgs = W.organism_count()
        energy = S.energy_manager.energy if S.energy_manager else 30.0
        result = _brain.finalize(stats, orgs, energy, _memory.get())
        _memory.record_session(stats, result.get("narrative", ""))
        _memory.record_peak(orgs, energy)
        _memory.save()
        if result.get("narrative"):
            print(f'\n  "{result["narrative"]}"\n')
    on_quit(py5, after_save=after_save)


def _update_world(active_hands, has_hands, dt, py5) -> None:
    """Update ecosystem + AI brain. Most expensive ops throttled."""
    W.update_perception(
        hands=[(hs.px, hs.py) for hs in active_hands],
        speeds=[hs.speed for hs in active_hands],
        gesture=_get_gesture(active_hands),
        energy=S.energy_manager.energy if S.energy_manager else 30.0,
        space_state=S.space_state.state if S.space_state else "IDLE",
        time_phase=S.time_system.get_phase_name() if S.time_system else "dawn",
    )

    if not W.weather_locked:
        WeatherSystem.update(dt)
    ExhibitionController.update(dt, has_hands)

    # AI analysis
    if S.behavior_analyzer:
        _brain.update(dt, S.behavior_analyzer.get_stats(),
                      W.organism_count(),
                      S.energy_manager.energy if S.energy_manager else 30.0,
                      _memory.get())
    EcosystemManager.update(dt)

    # Organisms
    W.world_age += dt
    for ai in W.autonomous_organisms[:]:
        ai.update(dt, W)
        if ai.state == "fade" and ai.energy < 1.0:
            W.unregister_organism(ai)

    # Apply AI directives
    wmod = WeatherSystem.get_modifiers()
    ambient = ExhibitionController.get_ambient_modifier()
    light_mult = _brain.lighting_mult()
    strat = _brain.strategy_mult()

    if S.flow_field:
        S.flow_field.flow_strength = 0.30 * wmod["flow"] * ambient * light_mult

    for ai in W.autonomous_organisms:
        ai.curiosity = min(1.0, ai.curiosity * strat["curiosity"])
        ai.fear = min(1.0, ai.fear * strat["fear"])
        ai.affinity = min(1.0, ai.affinity * strat["affinity"])

    # Display organisms (every frame — no throttling)
    for ai in W.autonomous_organisms:
        ai.display(py5)

    # Spawn AI wrappers for new V3 organisms
    if S.organism_manager and py5.frame_count % 30 == 0:
        for org in S.organism_manager.organisms:
            if not any(ai.organism is org for ai in W.autonomous_organisms):
                W.register_organism(OrganismAI(org, org.seed.x, org.seed.y))


# ============================================================
# V8 AI Globals
# ============================================================

_brain: WorldBrain = WorldBrain()
_memory: MemoryCurator = MemoryCurator()
_presence: PresenceEngine = PresenceEngine()
_camera_bg: CameraBgManager = CameraBgManager()


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="The Unseen")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--camera", action="store_true",
                        help="Enable webcam background")
    args = parser.parse_args()

    if args.release:
        S.release_mode = True
        set_debug_mode(False)
    if args.fresh:
        S.fresh_start = True
        delete_state(save_path())
    if args.camera:
        _use_camera_bg = True

    log("Init", "The Unseen — python -m the_unseen")
    py5.run_sketch()
