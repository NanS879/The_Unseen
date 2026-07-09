"""
The Unseen V3 — py5 Visual Renderer

A living digital ecosystem. Particles respond to human presence.
The space remembers, grows, and evolves across sessions.

Architecture:
    V2: Config → FlowField + InfluenceField → ParticleManager (3 layers)
               → SpaceState → render_utils → hand_state (OSC)
    V3: MemorySeed → Organism (DLA growth) → OrganismManager (ecosystem)
         EnergyManager → BehaviorAnalyzer → TimeSystem → Persistence

Run with:
    python main.py [--osc-port 12000] [--fresh]
"""

import os
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

# V3 imports
from energy_manager import EnergyManager
from behavior_analyzer import BehaviorAnalyzer
from organism import OrganismManager
from time_system import TimeSystem
from persistence import save_state, load_state, delete_state


# ============================================================
# Global State
# ============================================================

hand_left = HandState("left", Config.WIDTH * 0.35, Config.HEIGHT / 2)
hand_right = HandState("right", Config.WIDTH * 0.65, Config.HEIGHT / 2)

flow_field: FlowField | None = None
influence_field: InfluenceField | None = None
particle_manager: ParticleManager | None = None
space_state: SpaceState | None = None

# V3 globals
energy_manager: EnergyManager | None = None
behavior_analyzer: BehaviorAnalyzer | None = None
organism_manager: OrganismManager | None = None
time_system: TimeSystem | None = None
_autosave_timer: float = 0.0
_v3_fresh_start: bool = False

_frame_start_time: float = 0.0
_fps_display: float = 0.0


# ============================================================
# py5 Callbacks
# ============================================================

def setup() -> None:
    """Initialize py5 sketch and all V2 + V3 subsystems."""
    global flow_field, influence_field, particle_manager, space_state
    global energy_manager, behavior_analyzer, organism_manager, time_system
    global _v3_fresh_start

    py5.size(Config.WIDTH, Config.HEIGHT, py5.P2D)
    py5.color_mode(py5.RGB, 255)
    py5.frame_rate(60)
    py5.window_title("The Unseen V3 — 不可见 · Digital Organism")
    py5.background(0)

    flow_field = FlowField()
    influence_field = InfluenceField()
    particle_manager = ParticleManager()
    space_state = SpaceState()

    flow_field.update(0.0)
    start_osc_server(Config.OSC_IP, Config.OSC_PORT, hand_left, hand_right)

    # ---- V3 Setup ----
    if Config.V3_ENABLED and not _v3_fresh_start:
        _init_v3(from_saved=True)
    elif Config.V3_ENABLED:
        _init_v3(from_saved=False)
        _v3_fresh_start = False

    counts = particle_manager.layer_counts()
    print(f"[Visual] V3 — {particle_manager.total_count()} particles")
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
    dt = 1.0 / 60.0
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

    # ---- V3: Digital Organism ----
    if Config.V3_ENABLED and organism_manager is not None:
        _update_v3(active_hands, has_hands, max_speed, dt)

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
# V3 Helpers
# ============================================================

def _init_v3(from_saved: bool = True) -> None:
    """Initialize (or load) the V3 digital organism subsystem."""
    global energy_manager, behavior_analyzer, organism_manager, time_system

    try:
        # Use absolute path for save file
        module_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
        save_path = os.path.join(module_dir, Config.PERSISTENCE_FILE)
    except Exception:
        save_path = Config.PERSISTENCE_FILE

    if from_saved:
        try:
            data = load_state(save_path)
            if data:
                energy_manager = EnergyManager.deserialize(data["energy"])
                behavior_analyzer = BehaviorAnalyzer.deserialize(data["behavior"])
                organism_manager = OrganismManager.deserialize(data["ecosystem"])
                time_system = TimeSystem.deserialize(data["time_system"])
                print(f"[V3] Restored session: {organism_manager.total_organisms()} organisms, "
                      f"energy={energy_manager.energy:.1f}")
                return
        except Exception as e:
            print(f"[V3] Could not load saved state: {e}")

    # Fresh start
    energy_manager = EnergyManager(initial_energy=30.0)
    behavior_analyzer = BehaviorAnalyzer()
    organism_manager = OrganismManager()
    time_system = TimeSystem()
    print("[V3] Fresh ecosystem ready — hold hand still to plant seeds.")


def _update_v3(
    active_hands: list[HandState],
    has_hands: bool,
    max_speed: float,
    dt: float,
) -> None:
    """Update all V3 subsystems for one frame."""
    global _autosave_timer

    if energy_manager is None or behavior_analyzer is None:
        return
    if organism_manager is None or time_system is None:
        return

    # Clamp dt to prevent huge jumps
    dt = min(dt, 0.1)

    try:
        # Time system
        time_system.update(dt)
        tmod = time_system.get_modulators()

        # Energy
        energy_manager.update(has_hands, max_speed, dt)
        emod = energy_manager.get_multipliers()

        # Behavior
        hand_data = [
            {"side": hs.side, "px": hs.px, "py": hs.py, "speed": hs.speed}
            for hs in active_hands
        ]
        behavior_analyzer.update(dt, has_hands, hand_data)

        # Seed creation — use primary hand
        if has_hands and active_hands:
            primary = active_hands[0]
            seed = organism_manager.check_seed_creation(
                primary.px, primary.py, primary.speed, dt,
            )
            if seed:
                behavior_analyzer.on_seed_created()

        # Organism ecosystem
        growth_mult = tmod["growth"] * emod["growth"]
        hand_positions = [(hs.px, hs.py) for hs in active_hands]
        organism_manager.update(
            energy_manager, growth_mult, has_hands, hand_positions,
        )

        # Apply V3 modulations to V2 systems (mild)
        Config.FLOW_STRENGTH = 0.30 * (0.5 + 0.5 * tmod["flow"]) * emod["flow"]

        # Render organisms on top of particles
        organism_manager.display(py5)

        # Autosave
        _autosave_timer += dt
        if _autosave_timer >= Config.PERSISTENCE_AUTOSAVE_INTERVAL:
            _autosave_timer = 0.0
            try:
                module_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd()
                save_path = os.path.join(module_dir, Config.PERSISTENCE_FILE)
            except Exception:
                save_path = Config.PERSISTENCE_FILE
            if save_state(save_path, energy_manager, behavior_analyzer,
                          organism_manager, time_system):
                print(f"[V3] Saved — {organism_manager.total_organisms()} organisms, "
                      f"{organism_manager.total_growth_points()} pts")
    except Exception as e:
        import traceback
        print(f"[V3] Error in update: {e}")
        traceback.print_exc()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="The Unseen V3 — Visual Renderer")
    parser.add_argument(
        "--osc-port", type=int, default=Config.OSC_PORT,
        help=f"OSC listen port (default: {Config.OSC_PORT})",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Start with a fresh ecosystem (delete saved state)",
    )
    args = parser.parse_args()
    Config.OSC_PORT = args.osc_port

    if args.fresh:
        save_path = os.path.join(os.path.dirname(__file__) or ".",
                                 Config.PERSISTENCE_FILE)
        delete_state(save_path)
        _v3_fresh_start = True
        print("[Visual] Fresh start — previous ecosystem cleared.")

    print("[Visual] Starting The Unseen V3 — Digital Organism...")
    py5.run_sketch()
