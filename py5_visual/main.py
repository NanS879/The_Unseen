"""
The Unseen V2 — py5 Visual Renderer

A generative art ecosystem where particles live, breathe, and respond
to human presence. The entire space becomes a living digital environment.

Architecture:
    Config → FlowField + InfluenceField → ParticleManager (3 layers)
           → SpaceState (behavior modulation) → render_utils (visual polish)
           → hand_state (OSC dual-hand input)

Run with:
    python main.py [--osc-port 12000]
"""

import time

import py5

from config import Config
from flow_field import FlowField
from influence_field import InfluenceField
from particle_manager import ParticleManager
from space_state import SpaceState
from hand_state import (
    HandState,
    get_lock,
    get_message_count,
    get_server_error,
    start_osc_server,
)
from render_utils import draw_hand_aura, draw_vignette, draw_status_overlay


# ============================================================
# Global State
# ============================================================

hand_left = HandState("left", Config.WIDTH * 0.35, Config.HEIGHT / 2)
hand_right = HandState("right", Config.WIDTH * 0.65, Config.HEIGHT / 2)

flow_field: FlowField | None = None
influence_field: InfluenceField | None = None
particle_manager: ParticleManager | None = None
space_state: SpaceState | None = None

_frame_start_time: float = 0.0
_fps_display: float = 0.0


# ============================================================
# py5 Callbacks
# ============================================================

def setup() -> None:
    """Initialize py5 sketch and all V2 subsystems."""
    global flow_field, influence_field, particle_manager, space_state

    py5.size(Config.WIDTH, Config.HEIGHT, py5.P2D)
    py5.color_mode(py5.RGB, 255)
    py5.frame_rate(60)
    py5.window_title("The Unseen V2 — 不可见")
    py5.background(0)

    flow_field = FlowField()
    influence_field = InfluenceField()
    particle_manager = ParticleManager()
    space_state = SpaceState()

    flow_field.update(0.0)
    start_osc_server(Config.OSC_IP, Config.OSC_PORT, hand_left, hand_right)

    counts = particle_manager.layer_counts()
    print(f"[Visual] V2 — {particle_manager.total_count()} particles")
    print(f"  BG:{counts['background']} INT:{counts['interaction']} HL:{counts['highlight']}")
    print(f"[Visual] Flow: {flow_field.cols}x{flow_field.rows} | "
          f"Canvas: {Config.WIDTH}x{Config.HEIGHT}")


def draw() -> None:
    """Render one frame — orchestrate all V2 subsystems."""
    global _fps_display, _frame_start_time

    if flow_field is None or particle_manager is None:
        return
    if space_state is None or influence_field is None:
        return

    # ---- FPS ----
    now_ms = py5.millis()
    if _frame_start_time > 0:
        dt = (now_ms - _frame_start_time) / 1000.0
        if dt > 0:
            _fps_display += (1.0 / dt - _fps_display) * 0.1
    _frame_start_time = now_ms

    # ---- Read & smooth hands ----
    active_hands = _process_hands()

    has_hands = len(active_hands) > 0
    max_speed = max((hs.speed for hs in active_hands), default=0.0)

    # ---- Space State ----
    space_state.update(has_hands, max_speed)

    # ---- Trail overlay ----
    py5.no_stroke()
    py5.fill(0, 0, 0, space_state.trail_alpha)
    py5.rect(0, 0, Config.WIDTH, Config.HEIGHT)

    # ---- Vignette ----
    draw_vignette(py5)

    # ---- Flow Field ----
    t = now_ms / 1000.0
    interval = max(1, int(Config.FLOW_UPDATE_INTERVAL / space_state.flow_multiplier))
    if py5.frame_count % interval == 0:
        flow_field.time_scale = Config.FLOW_NOISE_SPEED * space_state.flow_multiplier
        flow_field.update(t)

    # ---- Influence Field ----
    influence_field.update([
        (hs.px, hs.py, hs.speed, hs.dx, hs.dy) for hs in active_hands
    ])

    # ---- Particles ----
    particle_manager.update(
        flow_field, influence_field,
        flow_mult=space_state.flow_multiplier,
        influence_mult=space_state.influence_multiplier,
        trail_mult=space_state.trail_multiplier,
    )
    particle_manager.display(py5, influence_field, space_state.trail_multiplier)

    # ---- Hand Auras ----
    for hs in active_hands:
        color = (
            Config.Palette.HAND_LEFT if hs.side == "left"
            else Config.Palette.HAND_RIGHT
        )
        draw_hand_aura(py5, hs.px, hs.py, hs.speed, space_state.state, color)

    # ---- Status ----
    if Config.DEBUG_SHOW_STATUS:
        draw_status_overlay(
            py5, space_state, particle_manager,
            active_hands, has_hands, hand_left, hand_right,
            get_server_error(), get_message_count(), _fps_display,
        )


# ============================================================
# Hand Processing
# ============================================================

def _process_hands() -> list[HandState]:
    """Read, timeout-check, and smooth both hands. Returns active hands."""
    lock = get_lock()
    with lock:
        now = time.monotonic()
        for hs in (hand_left, hand_right):
            if hs.has_data and (now - hs.last_update) > Config.STATE_HAND_TIMEOUT:
                hs.detected = False
                hs.raw_speed = 0.0

    active: list[HandState] = []
    for hs in (hand_left, hand_right):
        if hs.detected and hs.has_data:
            target_px = hs.raw_x * Config.WIDTH
            target_py = hs.raw_y * Config.HEIGHT
            hs.update_smoothing(
                Config.HAND_SMOOTHING, target_px, target_py, hs.raw_speed,
            )
            active.append(hs)
        else:
            hs.update_smoothing(
                Config.HAND_SMOOTHING_FADE,
                hs.default_x, hs.default_y, 0.0,
            )
    return active


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="The Unseen V2 — Visual Renderer")
    parser.add_argument(
        "--osc-port", type=int, default=Config.OSC_PORT,
        help=f"OSC listen port (default: {Config.OSC_PORT})",
    )
    args = parser.parse_args()
    Config.OSC_PORT = args.osc_port

    print("[Visual] Starting The Unseen V2...")
    py5.run_sketch()
