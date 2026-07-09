"""
The Unseen V4 — Single Runtime Interactive Art

Camera → MediaPipe → Simulation → Render — all in one process.
Just run: python main.py

Keys: D=debug overlay  F=FPS badge  R=release mode  Q=quit+report
"""

import os

import py5

# ── Config ──────────────────────────────────────────────
from config import Config

# ── Camera ──────────────────────────────────────────────
from camera_tracker import CameraTracker

# ── Core Simulation ─────────────────────────────────────
from flow_field import FlowField
from influence_field import InfluenceField
from particle_manager import ParticleManager
from space_state import SpaceState

# ── Hand State ──────────────────────────────────────────
from hand_state import HandState

# ── Render ──────────────────────────────────────────────
from render_utils import draw_hand_aura, draw_startup_hint

# ── V3 Organism ─────────────────────────────────────────
from energy_manager import EnergyManager
from behavior_analyzer import BehaviorAnalyzer
from organism import OrganismManager
from time_system import TimeSystem
from persistence import save_state, load_state, delete_state

# ── V4 Interaction ──────────────────────────────────────
from ripple import RippleManager
from fragment import FragmentManager
from gesture_manager import GestureManager
from interaction_rules import InteractionRules
from ability_manager import SpaceAbilityManager

# ── Infrastructure ──────────────────────────────────────
from logger import log, set_debug_mode
from debug_overlay import DebugOverlay


# ============================================================
# Global State
# ============================================================

# Camera
camera: CameraTracker | None = None

# Hands
hand_left = HandState("left", Config.WIDTH * 0.35, Config.HEIGHT / 2)
hand_right = HandState("right", Config.WIDTH * 0.65, Config.HEIGHT / 2)

# V2
flow_field: FlowField | None = None
influence_field: InfluenceField | None = None
particle_manager: ParticleManager | None = None
space_state: SpaceState | None = None

# V3
energy_manager: EnergyManager | None = None
behavior_analyzer: BehaviorAnalyzer | None = None
organism_manager: OrganismManager | None = None
time_system: TimeSystem | None = None

# V4
debug_overlay: DebugOverlay | None = None
ripple_manager: RippleManager | None = None
fragment_manager: FragmentManager | None = None
gesture_manager: GestureManager | None = None
ability_manager: SpaceAbilityManager | None = None

# Timing
_frame_start_ms: float = 0.0
_fps_display: float = 0.0
_autosave_timer: float = 0.0
_release_mode: bool = False
_fresh_start: bool = False


# ============================================================
# py5 Callbacks
# ============================================================

def setup() -> None:
    """Initialize everything: camera, sim, render."""
    global camera, flow_field, influence_field, particle_manager, space_state
    global energy_manager, behavior_analyzer, organism_manager, time_system
    global debug_overlay, ripple_manager, fragment_manager, gesture_manager, ability_manager, _frame_start_ms

    py5.size(Config.WIDTH, Config.HEIGHT, py5.P2D)
    py5.color_mode(py5.RGB, 255)
    py5.frame_rate(60)
    py5.window_title("The Unseen V4 — 不可见")
    py5.background(0)

    # ── Camera ──────────────────────────────────────────
    camera = CameraTracker(process_every_n=2)
    if not camera.start():
        log("Camera", "No camera available — running in demo mode", "WARN")

    # ── V2 Simulation ───────────────────────────────────
    flow_field = FlowField()
    influence_field = InfluenceField()
    particle_manager = ParticleManager()
    space_state = SpaceState()
    flow_field.update(0.0)

    # ── V3 Organism ─────────────────────────────────────
    _init_v3()

    # ── UI ──────────────────────────────────────────────
    debug_overlay = DebugOverlay()
    debug_overlay.set_font(py5.create_font("Monospaced", 10))
    ripple_manager = RippleManager()
    fragment_manager = FragmentManager()
    gesture_manager = GestureManager()
    ability_manager = SpaceAbilityManager()

    _frame_start_ms = py5.millis()

    counts = particle_manager.layer_counts()
    log("Init", f"V4 Single Runtime — {particle_manager.total_count()} particles "
        f"(BG:{counts['background']} INT:{counts['interaction']} HL:{counts['highlight']})")
    log("Init", "Ready. D=debug  F=FPS  R=release  Q=quit+report")


def draw() -> None:
    """Main loop: camera → hands → sim → render."""
    global _fps_display, _frame_start_ms

    if flow_field is None or particle_manager is None:
        return
    if space_state is None or influence_field is None:
        return

    # ── Timing ──────────────────────────────────────────
    now_ms = py5.millis()
    dt = 1.0 / 60.0
    frame_time = 16.7
    if _frame_start_ms > 0:
        dt_raw = (now_ms - _frame_start_ms) / 1000.0
        if 0 < dt_raw < 0.5:
            dt = dt_raw
            frame_time = dt_raw * 1000.0
            _fps_display += (1.0 / dt - _fps_display) * 0.1
    _frame_start_ms = now_ms

    # ── Camera + Hands ──────────────────────────────────
    active_hands = _process_camera()

    has_hands = len(active_hands) > 0
    max_speed = max((hs.speed for hs in active_hands), default=0.0)

    # ── Gesture Recognition ─────────────────────────────
    if gesture_manager and camera:
        _update_gestures(active_hands, dt)

    # ── Space State ─────────────────────────────────────
    space_state.update(has_hands, max_speed)

    # ── Background fade ─────────────────────────────────
    py5.no_stroke()
    py5.fill(0, 0, 0, space_state.trail_alpha)
    py5.rect(0, 0, Config.WIDTH, Config.HEIGHT)

    # ── Flow Field ──────────────────────────────────────
    t = now_ms / 1000.0
    interval = max(1, int(Config.FLOW_UPDATE_INTERVAL / space_state.flow_multiplier))
    if py5.frame_count % interval == 0:
        flow_field.time_scale = Config.FLOW_NOISE_SPEED * space_state.flow_multiplier
        flow_field.update(t)

    # ── Influence ───────────────────────────────────────
    influence_field.update([
        (hs.px, hs.py, hs.speed, hs.dx, hs.dy) for hs in active_hands
    ])

    # ── Particles ───────────────────────────────────────
    particle_manager.update(
        flow_field, influence_field,
        flow_mult=space_state.flow_multiplier,
        influence_mult=space_state.influence_multiplier,
    )
    particle_manager.display(py5, influence_field)

    # ── V3 Organisms ────────────────────────────────────
    if Config.V3_ENABLED and organism_manager is not None:
        _update_v3(active_hands, has_hands, max_speed, dt)

    # ── V4 Ripple + Fragment ─────────────────────────────
    if ripple_manager and fragment_manager:
        _update_v4(active_hands, has_hands, max_speed, dt)

    # ── Hand Auras ──────────────────────────────────────
    for hs in active_hands:
        color = (
            Config.Palette.HAND_LEFT if hs.side == "left"
            else Config.Palette.HAND_RIGHT
        )
        draw_hand_aura(py5, hs.px, hs.py, hs.speed, space_state.state, color)

    # ── Startup Hint ────────────────────────────────────
    draw_startup_hint(
        py5, has_hands,
        has_data=hand_left.has_data or hand_right.has_data,
        organism_count=organism_manager.total_organisms() if organism_manager else 0,
        seed_count=len(organism_manager.pending_seeds) if organism_manager else 0,
        frame_count=py5.frame_count,
    )

    # ── Debug ───────────────────────────────────────────
    if debug_overlay is not None:
        debug_overlay.update(frame_time)
        if debug_overlay.visible or debug_overlay.fps_only:
            _draw_debug(active_hands)


def key_pressed() -> None:
    """Keyboard shortcuts."""
    global _release_mode

    if py5.key in ('d', 'D'):
        if debug_overlay:
            debug_overlay.toggle()
    elif py5.key in ('f', 'F'):
        if debug_overlay:
            debug_overlay.toggle_fps()
    elif py5.key in ('r', 'R'):
        _release_mode = not _release_mode
        set_debug_mode(not _release_mode)
    elif py5.key in ('q', 'Q'):
        _on_quit()


def exiting() -> None:
    """Called when window closes."""
    _on_quit()


# ============================================================
# Camera + Hands
# ============================================================

def _process_camera() -> list[HandState]:
    """Grab camera frame, run MediaPipe, update HandStates."""
    if camera is None or not camera.is_ready:
        return _smooth_hands([])

    hands_data = camera.update()
    return _smooth_hands(hands_data)


def _smooth_hands(hands_data: list[dict]) -> list[HandState]:
    """Apply EMA smoothing to hand positions from camera data."""
    active: list[HandState] = []

    for h in hands_data:
        side = h["side"].lower()
        hs = hand_left if side == "left" else hand_right
        hs.raw_x = h["x"]
        hs.raw_y = h["y"]
        hs.raw_speed = h["speed"]
        hs.detected = h.get("detected", True)
        hs.has_data = True

        target_px = hs.raw_x * Config.WIDTH
        target_py = hs.raw_y * Config.HEIGHT
        hs.update_smoothing(
            Config.HAND_SMOOTHING, target_px, target_py, hs.raw_speed,
        )
        active.append(hs)

    # Fade undetected hands toward default
    detected_sides = {h["side"].lower() for h in hands_data}
    for hs in (hand_left, hand_right):
        if hs.side not in detected_sides:
            hs.detected = False
            hs.raw_speed = 0.0
            hs.update_smoothing(
                Config.HAND_SMOOTHING_FADE,
                hs.default_x, hs.default_y, 0.0,
            )

    return active


# ============================================================
# V3
# ============================================================

def _init_v3() -> None:
    """Initialize or restore V3 organism subsystem."""
    global energy_manager, behavior_analyzer, organism_manager, time_system

    save_path = _save_path()

    if not _fresh_start:
        try:
            data = load_state(save_path)
            if data:
                energy_manager = EnergyManager.deserialize(data["energy"])
                behavior_analyzer = BehaviorAnalyzer.deserialize(data["behavior"])
                organism_manager = OrganismManager.deserialize(data["ecosystem"])
                time_system = TimeSystem.deserialize(data["time_system"])
                log("V3", f"Restored: {organism_manager.total_organisms()} organisms, "
                    f"energy={energy_manager.energy:.1f}")
                return
        except Exception as e:
            log("V3", f"Load failed: {e}", "WARN")

    energy_manager = EnergyManager(initial_energy=30.0)
    behavior_analyzer = BehaviorAnalyzer()
    organism_manager = OrganismManager()
    time_system = TimeSystem()
    log("V3", "Fresh ecosystem — hold hand still to plant seeds")


def _update_v3(
    active_hands: list[HandState],
    has_hands: bool,
    max_speed: float,
    dt: float,
) -> None:
    """Update V3 subsystems for one frame."""
    global _autosave_timer

    if energy_manager is None or behavior_analyzer is None:
        return
    if organism_manager is None or time_system is None:
        return

    dt = min(dt, 0.1)

    try:
        time_system.update(dt)
        tmod = time_system.get_modulators()
        energy_manager.update(has_hands, max_speed, dt)
        emod = energy_manager.get_multipliers()

        hand_data = [
            {"side": hs.side, "px": hs.px, "py": hs.py, "speed": hs.speed}
            for hs in active_hands
        ]
        behavior_analyzer.update(dt, has_hands, hand_data)

        if has_hands and active_hands:
            primary = active_hands[0]
            seed = organism_manager.check_seed_creation(
                primary.px, primary.py, primary.speed, dt,
            )
            if seed:
                behavior_analyzer.on_seed_created()

        growth_mult = tmod["growth"] * emod["growth"]
        hand_positions = [(hs.px, hs.py) for hs in active_hands]
        organism_manager.update(
            energy_manager, growth_mult, has_hands, hand_positions,
        )

        organism_manager.display(py5)

        # Autosave
        _autosave_timer += dt
        if _autosave_timer >= Config.PERSISTENCE_AUTOSAVE_INTERVAL:
            _autosave_timer = 0.0
            if save_state(_save_path(), energy_manager, behavior_analyzer,
                          organism_manager, time_system):
                log("V3", f"Saved — {organism_manager.total_organisms()} orgs", "DEBUG")
    except Exception as e:
        import traceback
        log("V3", f"Error: {e}", "ERROR")
        traceback.print_exc()


# ============================================================
# V4 Interaction
# ============================================================

def _update_v4(
    active_hands: list[HandState],
    has_hands: bool,
    max_speed: float,
    dt: float,
) -> None:
    """Update V4 interaction systems: ripples + fragments."""
    if ripple_manager is None or fragment_manager is None:
        return

    hand_positions = [(hs.px, hs.py) for hs in active_hands]

    # Spawn ripple on fast movement
    if has_hands and max_speed > 0.05 and py5.frame_count % 15 == 0:
        for hs in active_hands:
            if hs.speed > 0.03:
                ripple_manager.spawn(
                    hs.px, hs.py,
                    strength=min(2.5, hs.speed * 15.0),
                    color=(
                        Config.Palette.HAND_LEFT if hs.side == "left"
                        else Config.Palette.HAND_RIGHT
                    ),
                )

    # Update fragments (attract to hands, check collection)
    fragment_manager.update(
        dt, hand_positions, energy_manager, ripple_manager,
    )

    # Update ripples (push particles)
    if particle_manager:
        ripple_manager.update(particle_manager.int_particles)

    # Display
    ripple_manager.display(py5)
    fragment_manager.display(py5)


# ============================================================
# Gesture
# ============================================================

def _update_gestures(active_hands: list[HandState], dt: float) -> None:
    """Run gesture recognition + drive abilities directly each frame.

    Key insight: abilities need gestures HELD to charge, so we drive
    them directly from get_active() every frame, NOT from state machine
    events (which fire on release).
    """
    if gesture_manager is None or camera is None:
        return

    landmarks = camera.get_landmarks()
    if not landmarks:
        return

    hand_data = [
        {"side": hs.side.capitalize(), "speed": hs.speed}
        for hs in active_hands
    ]
    gesture_manager.update(landmarks, hand_data, dt)

    # ── Drive Ability Manager from active gestures ───────
    if ability_manager:
        active_gestures: dict[str, bool] = {}

        for side_key in ("left", "right"):
            gesture, conf = gesture_manager.get_active(side_key)
            active_gestures[gesture] = True  # track what's held

            # If a gesture is detected with good confidence, feed it to
            # the ability manager for charging (every frame while held)
            if gesture != "none" and conf > 0.5:
                hs = hand_left if side_key == "left" else hand_right
                # Trigger starts ability if idle, or continues charging
                ability_manager.feed(gesture, side_key, hs.px, hs.py)

        # Update abilities — charge held ones, cancel released ones
        ability_manager.update(dt, active_gestures)

        # Apply mood modulation to flow
        mood_mod = ability_manager.get_mood_modifiers()
        if flow_field:
            flow_field.flow_strength = Config.FLOW_STRENGTH * mood_mod["flow"]

        # Render ability feedback
        ability_manager.display(py5)

    # ── Process one-shot gesture events (non-ability gestures) ──
    for side, gesture, _data in gesture_manager.get_events():
        if side == "both":
            hx, hy = Config.WIDTH / 2, Config.HEIGHT / 2
        elif side == "left":
            hx, hy = hand_left.px, hand_left.py
        else:
            hx, hy = hand_right.px, hand_right.py

        # Route to ability manager for ability gestures
        ability_gestures = {"open_palm", "fist", "pinch", "point",
                            "two_expand", "two_compress"}
        if gesture in ability_gestures and ability_manager:
            ability_manager.trigger(gesture, side, hx, hy)
        else:
            # Non-ability one-shot gestures
            result = InteractionRules.apply(
                gesture, hx, hy, ripple_manager, energy_manager,
            )
            if result:
                log("Gesture", f"{side} {gesture} → {result}", "DEBUG")


# ============================================================
# Debug
# ============================================================

def _draw_debug(active_hands: list[HandState]) -> None:
    """Render debug overlay."""
    if debug_overlay is None or particle_manager is None:
        return

    debug_overlay.draw(
        py5,
        particles=particle_manager.layer_counts(),
        organisms=organism_manager.total_organisms() if organism_manager else 0,
        growth_pts=organism_manager.total_growth_points() if organism_manager else 0,
        seeds=len(organism_manager.pending_seeds) if organism_manager else 0,
        energy=energy_manager.energy if energy_manager else 0.0,
        state=space_state.state if space_state else "?",
        phase=time_system.get_phase_name() if time_system else "?",
        hands=[(hs.px, hs.py) for hs in active_hands],
        speeds=[hs.speed for hs in active_hands],
    )
    # Add fragment + gesture info to overlay
    y_extra = py5.height - 40
    if fragment_manager and fragment_manager.active_count > 0:
        py5.fill(200, 200, 150, 200)
        py5.text(f"Fragments: {fragment_manager.active_count}  "
                 f"Collected: {fragment_manager.collected_count}",
                 22, y_extra)
        y_extra -= 18
    if gesture_manager:
        left_g, left_c = gesture_manager.get_active("left")
        right_g, right_c = gesture_manager.get_active("right")
        if left_g != "none" or right_g != "none":
            py5.fill(150, 220, 150, 200)
            py5.text(f"L: {left_g} ({left_c:.0%})  R: {right_g} ({right_c:.0%})",
                     22, y_extra)
            y_extra -= 18
    if ability_manager:
        active = ability_manager.get_active_ability()
        mood = ability_manager.current_mood.value
        if active:
            py5.fill(200, 180, 255, 200)
            py5.text(f"Ability: {active.name} ({active.state.value})  Mood: {mood}",
                     22, y_extra)


# ============================================================
# Quit
# ============================================================

def _on_quit() -> None:
    """Clean shutdown: save state, release camera, print report."""
    # Save V3 state
    try:
        if energy_manager and organism_manager:
            save_state(_save_path(), energy_manager, behavior_analyzer,
                       organism_manager, time_system)
            log("Save", "State saved", "INFO")
    except Exception as e:
        log("Save", f"Failed: {e}", "ERROR")

    # Release camera
    if camera:
        camera.stop()

    # Presence summary
    if behavior_analyzer:
        stats = behavior_analyzer.get_stats()
        orgs = organism_manager.total_organisms() if organism_manager else 0
        print("\n" + "=" * 50)
        print("  The Unseen — Today's Presence")
        print("=" * 50)
        print(f"  Duration:       {stats['session_duration']:.0f}s")
        print(f"  Distance:       {stats['total_distance']:.0f}px")
        print(f"  Still time:     {stats['total_dwell_time']:.1f}s")
        print(f"  Active time:    {stats['total_active_time']:.1f}s")
        print(f"  Seeds planted:  {stats['seed_count']}")
        print(f"  Organisms:      {orgs}")
        print(f"  Interactions:   {stats['interaction_count']}")
        print(f"  Avg speed:      {stats['avg_speed']:.4f}")
        if fragment_manager:
            print(f"  Fragments:      {fragment_manager.collected_count}")
        print("=" * 50)
        print(f"  \"{_presence_message(stats, orgs)}\"")
        print("=" * 50 + "\n")

    log("Exit", "Goodbye.")
    py5.exit_sketch()


def _presence_message(stats: dict, orgs: int) -> str:
    """Generate a presence宣言 based on session stats."""
    dwell = stats.get("total_dwell_time", 0)
    dist = stats.get("total_distance", 0)
    seeds = stats.get("seed_count", 0)
    fragments = fragment_manager.collected_count if fragment_manager else 0

    if orgs > 3:
        return "You grew a forest in the unseen."
    if seeds > 2:
        return "The space remembers where you paused."
    if fragments > 5:
        return "You gathered the scattered memories."
    if dwell > dist * 0.3:
        return "Your stillness shaped the world."
    if dist > 5000:
        return "You stirred the invisible ocean."
    return "You were here. The space has changed."


# ============================================================
# Utils
# ============================================================

def _save_path() -> str:
    try:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            Config.PERSISTENCE_FILE,
        )
    except Exception:
        return Config.PERSISTENCE_FILE


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="The Unseen V4")
    parser.add_argument("--fresh", action="store_true",
                        help="Start with fresh ecosystem")
    parser.add_argument("--release", action="store_true",
                        help="Disable debug output")
    parser.add_argument("--no-camera", action="store_true",
                        help="Run without camera (demo mode)")
    args = parser.parse_args()

    if args.release:
        _release_mode = True
        set_debug_mode(False)

    if args.fresh:
        delete_state(_save_path())
        _fresh_start = True
        log("Init", "Fresh start")

    log("Init", "The Unseen V4 — Single Runtime")
    log("Init", "python main.py  (that's it!)")
    py5.run_sketch()
