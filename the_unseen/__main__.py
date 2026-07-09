"""
The Unseen — Interactive Generative Art Installation.

python -m the_unseen [--fresh] [--release]

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
from .ui.render_utils import draw_hand_aura, draw_startup_hint
from .ui.debug_overlay import DebugOverlay
from .utils.logger import log, set_debug_mode
from .life.persistence import delete_state

from .main import (
    camera_process, init_organisms, update_organisms,
    update_ripples, update_gestures, draw_debug_overlay,
    on_quit, save_path,
)


# ============================================================
# py5 Callbacks
# ============================================================

def setup() -> None:
    """Initialize all subsystems."""
    py5.size(Config.WIDTH, Config.HEIGHT, py5.P2D)
    py5.color_mode(py5.RGB, 255)
    py5.frame_rate(60)
    py5.window_title("The Unseen — 不可见")
    py5.background(0)

    S.camera = CameraTracker(process_every_n=2)
    if not S.camera.start():
        log("Camera", "No camera — demo mode", "WARN")

    S.flow_field = FlowField()
    S.influence_field = InfluenceField()
    S.particle_manager = ParticleManager()
    S.space_state = SpaceState()
    S.flow_field.update(0.0)

    init_organisms()

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

    S.frame_start_ms = py5.millis()

    counts = S.particle_manager.layer_counts()
    log("Init", f"{S.particle_manager.total_count()} particles "
        f"(BG:{counts['background']} INT:{counts['interaction']} "
        f"HL:{counts['highlight']})")
    log("Init", "D=debug  F=FPS  R=release  Q=quit")


def draw() -> None:
    """Main loop."""
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

    # Camera + Hands
    active_hands = camera_process()
    has_hands = len(active_hands) > 0
    max_speed = max((hs.speed for hs in active_hands), default=0.0)

    # Gestures
    if S.gesture_manager and S.camera:
        update_gestures(active_hands, dt)

    # Space State
    S.space_state.update(has_hands, max_speed)

    # V6 Breathing Camera
    if S.breath_cam:
        S.breath_cam.update(dt)
        S.breath_cam.apply(py5)

    # V6 BG + Lighting
    if S.state_light and S.bg_renderer:
        S.state_light.set_state(S.space_state.state)
        S.state_light.update(dt)
        S.bg_renderer.update(dt)
        S.bg_renderer.draw(py5, S.space_state.state)

    # V5 Camera matrix
    py5.push_matrix()
    if S.feedback:
        S.feedback.apply_camera(py5)

    # Motion blur
    py5.no_stroke()
    py5.fill(0, 0, 0, S.space_state.trail_alpha)
    py5.rect(0, 0, Config.WIDTH, Config.HEIGHT)

    # Flow Field
    t = now_ms / 1000.0
    interval = max(1, int(Config.FLOW_UPDATE_INTERVAL
                          / S.space_state.flow_multiplier))
    ripple_flow = 1.0
    if S.ripple_manager and S.ripple_manager.active_count > 0:
        ripple_flow = 1.0 + S.ripple_manager.get_flow_modulation(
            Config.WIDTH / 2, Config.HEIGHT / 2) * 2.0
        shake = S.ripple_manager.get_camera_shake()
        if shake > 0.1 and S.feedback:
            S.feedback.camera.trigger("shake", shake * 0.4, 0.15, "smoothstep")
    if py5.frame_count % interval == 0:
        S.flow_field.time_scale = (
            Config.FLOW_NOISE_SPEED
            * S.space_state.flow_multiplier
            * ripple_flow)
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

    # V4 Ripple + Fragment
    if S.ripple_manager and S.fragment_manager:
        update_ripples(active_hands, has_hands, max_speed, dt)
        S.ripple_manager.display(py5)
        S.fragment_manager.display(py5)

    # V4 Ability feedback
    if S.ability_manager:
        S.ability_manager.display(py5)

    # Hand Auras
    for hs in active_hands:
        color = (Config.Palette.HAND_LEFT if hs.side == "left"
                 else Config.Palette.HAND_RIGHT)
        draw_hand_aura(py5, hs.px, hs.py, hs.speed,
                       S.space_state.state, color)

    # Startup Hint
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

    # End camera matrix
    py5.pop_matrix()

    # Post effects
    if S.feedback:
        S.feedback.apply_post(py5)


def key_pressed() -> None:
    if py5.key in ('d', 'D') and S.debug_overlay:
        S.debug_overlay.toggle()
    elif py5.key in ('f', 'F') and S.debug_overlay:
        S.debug_overlay.toggle_fps()
    elif py5.key in ('r', 'R'):
        S.release_mode = not S.release_mode
        set_debug_mode(not S.release_mode)
    elif py5.key in ('q', 'Q'):
        on_quit(py5)


def exiting() -> None:
    on_quit(py5)


# ============================================================
# Entry
# ============================================================

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="The Unseen")
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument("--release", action="store_true")
    args = parser.parse_args()

    if args.release:
        S.release_mode = True
        set_debug_mode(False)
    if args.fresh:
        delete_state(save_path())
        S.fresh_start = True
        log("Init", "Fresh start")

    log("Init", "The Unseen — python -m the_unseen")
    py5.run_sketch()
