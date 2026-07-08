"""
The Unseen — py5 Visual Renderer (Dual-Hand Edition)

A generative art particle system driven by Perlin noise flow fields
and real-time dual-hand interaction via OSC.

Module-mode py5 sketch. Run with:
    python main.py [--osc-port 12000]
"""

import math
import random
import threading
import time

import py5

from pythonosc import dispatcher
from pythonosc import osc_server

from particle import Particle
from flow_field import FlowField

# ============================================================
# Configuration
# ============================================================

# Canvas
WIDTH = 1280
HEIGHT = 720

# Particles
NUM_PARTICLES = 1000
NUM_TRAIL_PARTICLES = 120        # More burst particles for two hands
PARTICLE_MAX_SPEED = 4.0
PARTICLE_DAMPING = 0.96

# Flow Field
FLOW_CELL_SIZE = 25
FLOW_NOISE_SCALE = 0.004
FLOW_TIME_SCALE = 0.006
FLOW_STRENGTH = 0.30

# Hand Interaction
GRAVITY_STRENGTH = 800.0
GRAVITY_MIN_DISTANCE = 15.0
GRAVITY_MAX_DISTANCE = 250.0
WAKE_STRENGTH = 3.0

# Smoothing
HAND_SMOOTHING = 0.4
HAND_SMOOTHING_FADE = 0.05       # When hand lost, slow fade to center

# Trail alpha
TRAIL_ALPHA_IDLE = 8
TRAIL_ALPHA_ACTIVE = 18
TRAIL_ALPHA_BURST = 35
BURST_SPEED_THRESHOLD = 0.08

# OSC
OSC_IP = "127.0.0.1"
OSC_PORT = 12000
HAND_TIMEOUT = 1.0

# ============================================================
# Per-Hand State
# ============================================================

class HandState:
    """Smoothed state for a single tracked hand."""

    def __init__(self, side: str, aura_color: tuple, initial_x: float, initial_y: float):
        self.side = side                # "left" or "right"
        self.aura_color = aura_color    # (r, g, b) for aura rings
        self.aura_burst = aura_color    # burst-mode aura color

        # Raw OSC data (updated from handler thread)
        self.raw_x: float = initial_x
        self.raw_y: float = initial_y
        self.raw_speed: float = 0.0
        self.detected: bool = False
        self.last_update: float = 0.0
        self.has_data: bool = False

        # Smoothed pixel-space values
        self.px: float = initial_x
        self.py: float = initial_y
        self.speed: float = 0.0
        self.prev_px: float = initial_x
        self.prev_py: float = initial_y
        self.dx: float = 0.0
        self.dy: float = 0.0

    def update_smoothing(self, alpha: float, target_px: float, target_py: float,
                         target_speed: float) -> None:
        """Advance EMA smoothing by one step."""
        self.prev_px = self.px
        self.prev_py = self.py
        self.px += (target_px - self.px) * alpha
        self.py += (target_py - self.py) * alpha
        self.speed += (target_speed - self.speed) * alpha
        self.dx = self.px - self.prev_px
        self.dy = self.py - self.prev_py


# Two hand states
hand_left = HandState("left", aura_color=(255, 150, 255), initial_x=WIDTH * 0.35, initial_y=HEIGHT / 2)
hand_right = HandState("right", aura_color=(255, 200, 100), initial_x=WIDTH * 0.65, initial_y=HEIGHT / 2)

# ============================================================
# Global State
# ============================================================

particles: list[Particle] = []
trail_particles: list[Particle] = []
flow_field: FlowField | None = None

_hand_lock = threading.Lock()
_osc_message_count: int = 0
_osc_server_error: str | None = None

_frame_start_time: float = 0.0
_fps_display: float = 0.0


# ============================================================
# OSC Handlers
# ============================================================

def _make_handler(side: str):
    """Create an OSC handler closure for a given hand side."""
    def handler(address: str, *args) -> None:
        global _osc_message_count
        state = hand_left if side == "left" else hand_right
        with _hand_lock:
            state.raw_x = float(args[0])
            state.raw_y = float(args[1])
            state.raw_speed = float(args[2])
            state.detected = bool(float(args[3]) > 0.5)
            state.last_update = time.monotonic()
            state.has_data = True
            _osc_message_count += 1
    return handler


def _start_osc_server(ip: str, port: int) -> None:
    """Start OSC receiver in daemon thread with error handling."""
    global _osc_server_error
    disp = dispatcher.Dispatcher()
    disp.map("/hand/left", _make_handler("left"))
    disp.map("/hand/right", _make_handler("right"))

    try:
        server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    except OSError as e:
        _osc_server_error = str(e)
        print(f"[Visual] ERROR: Cannot bind OSC to {ip}:{port} — {e}")
        print("[Visual] Hand interaction will NOT work.")
        return

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Visual] OSC listening on {ip}:{port}")


# ============================================================
# py5 Callbacks
# ============================================================

def setup() -> None:
    """Initialize py5 sketch."""
    global particles, trail_particles, flow_field

    py5.size(WIDTH, HEIGHT, py5.P2D)
    py5.color_mode(py5.RGB, 255)
    py5.frame_rate(60)
    py5.window_title("The Unseen — 不可见 (Dual Hand)")
    py5.background(0)

    flow_field = FlowField(
        width=WIDTH, height=HEIGHT,
        cell_size=FLOW_CELL_SIZE,
        noise_scale=FLOW_NOISE_SCALE,
        time_scale=FLOW_TIME_SCALE,
        flow_strength=FLOW_STRENGTH,
    )
    flow_field.update(0.0)

    particles = [Particle(WIDTH, HEIGHT) for _ in range(NUM_PARTICLES)]
    trail_particles = [Particle(WIDTH, HEIGHT) for _ in range(NUM_TRAIL_PARTICLES)]
    for tp in trail_particles:
        tp.life = 0.0

    _start_osc_server(OSC_IP, OSC_PORT)

    print(f"[Visual] {NUM_PARTICLES} particles + {NUM_TRAIL_PARTICLES} trail particles")
    print(f"[Visual] Flow field: {flow_field.cols}x{flow_field.rows} cells")
    print(f"[Visual] Canvas: {WIDTH}x{HEIGHT}")
    print("[Visual] Dual-hand mode — waiting for OSC data...")
    print("[Visual]   Right hand: warm gold aura")
    print("[Visual]   Left hand:  magenta aura")


def draw() -> None:
    """Render one frame with dual-hand interaction."""
    global _fps_display, _frame_start_time, _osc_message_count, _osc_server_error

    if flow_field is None:
        return

    # FPS tracking
    now_ms = py5.millis()
    if _frame_start_time > 0:
        dt = (now_ms - _frame_start_time) / 1000.0
        if dt > 0:
            _fps_display += (1.0 / dt - _fps_display) * 0.1
    _frame_start_time = now_ms

    # ---- Read hand states (thread-safe) ----
    with _hand_lock:
        for hs in (hand_left, hand_right):
            # Timeout check
            now_mono = time.monotonic()
            if hs.has_data and (now_mono - hs.last_update) > HAND_TIMEOUT:
                hs.detected = False
                hs.raw_speed = 0.0

    # ---- Smooth & update both hands ----
    active_hands: list[HandState] = []

    for hs in (hand_left, hand_right):
        if hs.detected and hs.has_data:
            target_px = hs.raw_x * WIDTH
            target_py = hs.raw_y * HEIGHT
            target_speed = hs.raw_speed
            hs.update_smoothing(HAND_SMOOTHING, target_px, target_py, target_speed)
            active_hands.append(hs)
        else:
            # Fade toward default position
            default_px = WIDTH * 0.35 if hs.side == "left" else WIDTH * 0.65
            default_py = HEIGHT / 2
            hs.update_smoothing(HAND_SMOOTHING_FADE, default_px, default_py, 0.0)

    any_hand = len(active_hands) > 0

    # ---- Dynamic trail alpha (use fastest hand) ----
    if not any_hand:
        trail_alpha = TRAIL_ALPHA_IDLE
        burst_mode = False
    else:
        max_speed = max(hs.speed for hs in active_hands)
        if max_speed > BURST_SPEED_THRESHOLD:
            trail_alpha = TRAIL_ALPHA_BURST
            burst_mode = True
        else:
            trail_alpha = TRAIL_ALPHA_ACTIVE
            burst_mode = False

    # ---- Trail overlay ----
    py5.no_stroke()
    py5.fill(0, 0, 0, trail_alpha)
    py5.rect(0, 0, WIDTH, HEIGHT)

    # ---- Vignette ----
    _draw_vignette()

    # ---- Flow field update ----
    t = now_ms / 1000.0
    update_interval = 6 if not any_hand else 3
    if py5.frame_count % update_interval == 0:
        flow_field.update(t)

    # ---- Burst trail particles (per hand) ----
    if burst_mode:
        for hs in active_hands:
            if hs.speed > BURST_SPEED_THRESHOLD:
                _spawn_burst(hs.px, hs.py, hs.dx, hs.dy, hs.speed, hs.aura_color)

    # ---- Update & render trail particles ----
    for tp in trail_particles:
        if tp.life > 0:
            fvx, fvy = flow_field.lookup(tp.position[0], tp.position[1])
            tp.apply_force(fvx, fvy)
            tp.update(max_speed=PARTICLE_MAX_SPEED * 1.5, damping=0.92)
            if tp.is_dead():
                tp.life = 0.0
            else:
                tp.display(py5, near_hand=1.0)

    # ---- Update & render main particles ----
    for p in particles:
        # Flow field force
        fvx, fvy = flow_field.lookup(p.position[0], p.position[1])
        p.apply_force(fvx, fvy)

        # Dual-hand interaction — superposition of both hands
        near_hand = 0.0
        near_left = 0.0
        near_right = 0.0

        for hs in active_hands:
            dx = hs.px - p.position[0]
            dy = hs.py - p.position[1]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < GRAVITY_MAX_DISTANCE and dist > 0.01:
                # Gravity: F = G / d^2
                d_clamped = max(dist, GRAVITY_MIN_DISTANCE)
                magnitude = GRAVITY_STRENGTH / (d_clamped * d_clamped)
                ndx = dx / dist
                ndy = dy / dist
                p.apply_force(ndx * magnitude, ndy * magnitude)

                # Wake push along hand movement direction
                wake_factor = hs.speed * WAKE_STRENGTH * (1.0 - dist / GRAVITY_MAX_DISTANCE)
                p.apply_force(hs.dx * wake_factor, hs.dy * wake_factor)

                # Burst repulsion for "air parting" effect
                if burst_mode:
                    repel = -wake_factor * 0.5
                    p.apply_force(hs.dx * repel, hs.dy * repel)

                # Proximity factor per hand (for color blending)
                factor = 1.0 - (dist / GRAVITY_MAX_DISTANCE)
                factor = factor * factor  # Quadratic falloff feels more natural
                near_hand = max(near_hand, factor)
                if hs.side == "left":
                    near_left = max(near_left, factor)
                else:
                    near_right = max(near_right, factor)

        # Physics
        p.update(max_speed=PARTICLE_MAX_SPEED, damping=PARTICLE_DAMPING)

        if p.is_dead():
            p.respawn()

        # Render with per-hand color blending
        display_factor = near_hand
        if burst_mode and near_hand > 0.3:
            display_factor = min(1.0, near_hand * 1.5)
        p.display_dual(py5, near_hand=display_factor,
                       near_left=near_left, near_right=near_right)

    # ---- Hand auras ----
    for hs in active_hands:
        _draw_hand_aura(hs.px, hs.py, hs.speed, burst_mode, hs.aura_color)

    # ---- Status overlay ----
    _draw_status_overlay(any_hand, active_hands)


# ============================================================
# Burst Particles
# ============================================================

def _spawn_burst(
    px: float, py: float, dx: float, dy: float, speed: float, color: tuple
) -> None:
    """Activate trail particles at hand position for wake bursts."""
    spawn_count = min(15, int(speed * 30))
    spawned = 0
    for tp in trail_particles:
        if tp.life <= 0:
            tp.position[0] = px + random.uniform(-15, 15)
            tp.position[1] = py + random.uniform(-15, 15)
            tp.prev_x = tp.position[0]
            tp.prev_y = tp.position[1]
            spread = 1.5
            tp.velocity[0] = dx * 0.8 + random.uniform(-spread, spread)
            tp.velocity[1] = dy * 0.8 + random.uniform(-spread, spread)
            tp.acceleration = [0.0, 0.0]
            tp.max_life = random.uniform(30, 80)
            tp.life = tp.max_life
            tp.size = random.uniform(2.0, 5.0)
            # Store burst color for this particle
            tp.burst_r, tp.burst_g, tp.burst_b = color
            spawned += 1
            if spawned >= spawn_count:
                break


# ============================================================
# Visual Polish
# ============================================================

def _draw_hand_aura(
    px: float, py: float, speed: float, burst: bool, color: tuple
) -> None:
    """Draw a soft aura around a hand position."""
    intensity = min(1.0, speed * 10.0)
    rings = 5 if burst else 3
    r, g, b = color

    for i in range(rings):
        radius = 20.0 + i * 25.0 + speed * 80.0 * (i + 1) / rings
        alpha = (rings - i) / rings * 30.0 * (1.0 + intensity)
        py5.stroke(r, g, b, alpha)
        py5.stroke_weight(0.8)
        py5.no_fill()
        py5.circle(px, py, radius)

    # Core glow
    glow_size = 8.0 + speed * 40.0
    for i in range(3):
        rr = glow_size * (1.0 - i * 0.3)
        a = 60.0 * (1.0 - i * 0.3) * (1.0 + intensity)
        py5.no_stroke()
        py5.fill(255, 255, 255, a)
        py5.circle(px, py, rr)


def _draw_vignette() -> None:
    """Draw a subtle radial vignette."""
    if py5.frame_count % 10 != 0:
        return
    py5.no_stroke()
    cx, cy = WIDTH / 2, HEIGHT / 2
    max_r = math.sqrt(cx * cx + cy * cy)
    for i in range(5):
        r = max_r * (0.5 + i * 0.1)
        alpha = 3.0 * (1.0 - i / 5.0)
        py5.fill(0, 0, 0, alpha)
        py5.circle(cx, cy, r * 2)


def _draw_status_overlay(any_hand: bool, active_hands: list[HandState]) -> None:
    """Draw OSC connection status with per-hand info."""
    py5.push()
    # Background
    py5.no_stroke()
    py5.fill(0, 0, 0, 120)
    py5.rect(5, 5, 280, 85)

    y = 22

    # OSC status
    if _osc_server_error:
        py5.fill(255, 80, 80, 230)
        py5.text(f"X OSC ERROR: {_osc_server_error[:40]}", 14, y)
    elif any_hand:
        parts = []
        for hs in active_hands:
            label = "R" if hs.side == "right" else "L"
            parts.append(f"{label}:({hs.raw_x:.2f},{hs.raw_y:.2f})")
        py5.fill(80, 255, 80, 230)
        py5.text(f"● OSC live | {'  '.join(parts)}", 14, y)
    elif hand_left.has_data or hand_right.has_data:
        py5.fill(255, 200, 60, 230)
        py5.text(f"○ OSC live | hands lost ({_osc_message_count} msgs)", 14, y)
    else:
        py5.fill(255, 160, 60, 230)
        py5.text(f"◎ Waiting for dual-hand tracker...", 14, y)
        py5.fill(180, 180, 180, 200)
        py5.text(f"   Run: cd python_tracker && python main.py", 14, y + 18)

    # FPS + particle count
    y_bottom = 62
    if not any_hand and not hand_left.has_data:
        y_bottom = 78
    py5.fill(200, 200, 200, 200)
    py5.text(f"FPS: {_fps_display:.0f}  |  particles: {len(particles)}", 14, y_bottom)

    py5.pop()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="The Unseen — Visual Renderer")
    parser.add_argument(
        "--osc-port", type=int, default=OSC_PORT,
        help=f"OSC listen port (default: {OSC_PORT})",
    )
    args = parser.parse_args()
    OSC_PORT = args.osc_port

    print("[Visual] Starting The Unseen (Dual-Hand)...")
    py5.run_sketch()
