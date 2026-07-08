"""
The Unseen — py5 Visual Renderer

A generative art particle system driven by Perlin noise flow fields
and real-time hand interaction via OSC.

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
NUM_TRAIL_PARTICLES = 80       # Extra particles for hand wake bursts
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

# Smoothing: exponential moving average for hand position
HAND_SMOOTHING = 0.4           # Lower = smoother/more lag, higher = snappier

# Trail alpha: dynamically adjusted
TRAIL_ALPHA_IDLE = 8           # No hand — very long trails
TRAIL_ALPHA_ACTIVE = 18        # Hand present — moderate trails
TRAIL_ALPHA_BURST = 35         # Hand moving fast — short trails + burst particles
BURST_SPEED_THRESHOLD = 0.08   # Normalized speed threshold for burst mode

# OSC
OSC_IP = "127.0.0.1"
OSC_PORT = 12000
HAND_TIMEOUT = 1.0

# ============================================================
# Global State
# ============================================================

particles: list[Particle] = []
trail_particles: list[Particle] = []  # Burst particles for hand wake
flow_field: FlowField | None = None

# Thread-safe hand state
_hand_lock = threading.Lock()
hand_data = {
    "hand_x": 0.5,
    "hand_y": 0.5,
    "hand_speed": 0.0,
    "hand_detected": False,
    "last_update": 0.0,
    "has_data": False,
}
_osc_message_count: int = 0  # Track incoming OSC messages for debugging
_osc_server_error: str | None = None  # Store OSC startup error

# Smoothed hand state for visual rendering
_smooth_hand_px: float = WIDTH / 2
_smooth_hand_py: float = HEIGHT / 2
_smooth_hand_speed: float = 0.0
_prev_hand_px: float = WIDTH / 2
_prev_hand_py: float = HEIGHT / 2

# Frame timing
_frame_start_time: float = 0.0
_fps_display: float = 0.0


# ============================================================
# OSC Handler
# ============================================================

def _hand_handler(address: str, *args) -> None:
    """Receive /hand OSC messages (called from background thread)."""
    global _osc_message_count
    with _hand_lock:
        hand_data["hand_x"] = float(args[0])
        hand_data["hand_y"] = float(args[1])
        hand_data["hand_speed"] = float(args[2])
        hand_data["hand_detected"] = bool(float(args[3]) > 0.5)
        hand_data["last_update"] = time.monotonic()
        hand_data["has_data"] = True
        _osc_message_count += 1


def _start_osc_server(ip: str, port: int) -> None:
    """Start OSC receiver in daemon thread with error handling."""
    global _osc_server_error
    disp = dispatcher.Dispatcher()
    disp.map("/hand", _hand_handler)

    try:
        server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    except OSError as e:
        _osc_server_error = str(e)
        print(f"[Visual] ERROR: Cannot bind OSC to {ip}:{port} — {e}")
        print("[Visual] Hand interaction will NOT work. Is another instance running?")
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
    py5.set_window_title("The Unseen — 不可见")
    # Note: removed no_smooth() — smooth particles look better and P2D handles it fine

    # Ensure clean black start — critical for the trail-feedback technique
    py5.background(0)

    # Flow field
    flow_field = FlowField(
        width=WIDTH, height=HEIGHT,
        cell_size=FLOW_CELL_SIZE,
        noise_scale=FLOW_NOISE_SCALE,
        time_scale=FLOW_TIME_SCALE,
        flow_strength=FLOW_STRENGTH,
    )
    # Initialize immediately so particles have flow from frame 1
    flow_field.update(0.0)

    # Main particle pool
    particles = [Particle(WIDTH, HEIGHT) for _ in range(NUM_PARTICLES)]

    # Trail burst particle pool (starts dead/invisible)
    trail_particles = [Particle(WIDTH, HEIGHT) for _ in range(NUM_TRAIL_PARTICLES)]
    for tp in trail_particles:
        tp.life = 0.0  # Start dead

    # OSC receiver (with error handling)
    _start_osc_server(OSC_IP, OSC_PORT)

    print(f"[Visual] {NUM_PARTICLES} particles + {NUM_TRAIL_PARTICLES} trail particles")
    print(f"[Visual] Flow field: {flow_field.cols}x{flow_field.rows} cells")
    print(f"[Visual] Canvas: {WIDTH}x{HEIGHT}")
    print("[Visual] Waiting for hand data via OSC...")


def draw() -> None:
    """Render one frame."""
    global _smooth_hand_px, _smooth_hand_py, _smooth_hand_speed
    global _prev_hand_px, _prev_hand_py, _fps_display, _frame_start_time
    global _osc_message_count, _osc_server_error

    if flow_field is None:
        return

    # FPS tracking
    now_ms = py5.millis()
    if _frame_start_time > 0:
        dt = (now_ms - _frame_start_time) / 1000.0
        if dt > 0:
            _fps_display += (1.0 / dt - _fps_display) * 0.1
    _frame_start_time = now_ms

    # -- Read hand state (thread-safe) --
    with _hand_lock:
        hx = hand_data["hand_x"]
        hy = hand_data["hand_y"]
        hspeed = hand_data["hand_speed"]
        hdetected = hand_data["hand_detected"]
        hlast = hand_data["last_update"]
        hhas = hand_data["has_data"]

    # Timeout check
    now_mono = time.monotonic()
    if hhas and (now_mono - hlast) > HAND_TIMEOUT:
        hdetected = False

    # Map to pixels
    raw_px = hx * WIDTH
    raw_py = hy * HEIGHT

    # Smooth hand position (EMA)
    alpha = HAND_SMOOTHING
    if not hdetected:
        # Fade smoothing toward center when no hand
        alpha = 0.05
        raw_px = WIDTH / 2
        raw_py = HEIGHT / 2
        raw_speed = 0.0
    else:
        raw_speed = hspeed

    _smooth_hand_px += (raw_px - _smooth_hand_px) * alpha
    _smooth_hand_py += (raw_py - _smooth_hand_py) * alpha
    _smooth_hand_speed += (raw_speed - _smooth_hand_speed) * alpha

    hand_px = _smooth_hand_px
    hand_py = _smooth_hand_py
    hand_speed = _smooth_hand_speed

    # Hand delta for wake
    hand_dx = hand_px - _prev_hand_px
    hand_dy = hand_py - _prev_hand_py
    _prev_hand_px = hand_px
    _prev_hand_py = hand_py

    # -- Dynamic trail alpha --
    if not hdetected or not hhas:
        trail_alpha = TRAIL_ALPHA_IDLE
        burst_mode = False
    elif hand_speed > BURST_SPEED_THRESHOLD:
        trail_alpha = TRAIL_ALPHA_BURST
        burst_mode = True
    else:
        trail_alpha = TRAIL_ALPHA_ACTIVE
        burst_mode = False

    # -- Trail overlay --
    py5.no_stroke()
    py5.fill(0, 0, 0, trail_alpha)
    py5.rect(0, 0, WIDTH, HEIGHT)

    # -- Subtle vignette for depth --
    _draw_vignette()

    # -- Flow field update (throttled, less frequent when idle) --
    t = now_ms / 1000.0
    update_interval = 6 if not hdetected else 3
    if py5.frame_count % update_interval == 0:
        flow_field.update(t)

    # -- Burst trail particles on fast movement --
    if burst_mode and hdetected:
        _spawn_burst(hand_px, hand_py, hand_dx, hand_dy, hand_speed)

    # -- Update and render trail particles --
    for tp in trail_particles:
        if tp.life > 0:
            fvx, fvy = flow_field.lookup(tp.position[0], tp.position[1])
            tp.apply_force(fvx, fvy)
            tp.update(max_speed=PARTICLE_MAX_SPEED * 1.5, damping=0.92)
            if tp.is_dead():
                tp.life = 0.0
            else:
                # Trail particles always glow warm/bright
                tp.display(py5, near_hand=1.0)

    # -- Update and render main particles --
    for p in particles:
        # Flow field
        fvx, fvy = flow_field.lookup(p.position[0], p.position[1])
        p.apply_force(fvx, fvy)

        # Hand interaction
        near_hand = 0.0
        if hdetected:
            dx = hand_px - p.position[0]
            dy = hand_py - p.position[1]
            dist = math.sqrt(dx * dx + dy * dy)

            if dist < GRAVITY_MAX_DISTANCE and dist > 0.01:
                # Gravity: F = G / d^2
                d_clamped = max(dist, GRAVITY_MIN_DISTANCE)
                magnitude = GRAVITY_STRENGTH / (d_clamped * d_clamped)
                ndx = dx / dist
                ndy = dy / dist
                p.apply_force(ndx * magnitude, ndy * magnitude)

                # Wake push
                wake_factor = hand_speed * WAKE_STRENGTH * (1.0 - dist / GRAVITY_MAX_DISTANCE)
                p.apply_force(hand_dx * wake_factor, hand_dy * wake_factor)

                # Burst mode: extra repulsion creates "air parting" effect
                if burst_mode:
                    repel = -wake_factor * 0.5
                    p.apply_force(hand_dx * repel, hand_dy * repel)

                # Color shift
                near_hand = 1.0 - (dist / GRAVITY_MAX_DISTANCE)
                near_hand = near_hand * near_hand

        # Physics
        p.update(max_speed=PARTICLE_MAX_SPEED, damping=PARTICLE_DAMPING)

        # Respawn
        if p.is_dead():
            p.respawn()

        # Render — boost effective near_hand during burst mode
        display_factor = near_hand
        if burst_mode and near_hand > 0.3:
            display_factor = min(1.0, near_hand * 1.5)
        p.display(py5, near_hand=display_factor)

    # -- Hand indicator --
    if hdetected and hhas:
        _draw_hand_aura(hand_px, hand_py, hand_speed, burst_mode)

    # -- OSC status overlay (top-left corner) --
    _draw_status_overlay(hhas, hdetected)


# ============================================================
# Burst Particles
# ============================================================

def _spawn_burst(
    px: float, py: float, dx: float, dy: float, speed: float
) -> None:
    """Activate trail particles at hand position for wake bursts.

    Args:
        px, py: Hand position in pixels.
        dx, dy: Hand movement delta this frame.
        speed: Smoothed hand speed.
    """
    spawn_count = min(20, int(speed * 30))
    spawned = 0
    for tp in trail_particles:
        if tp.life <= 0:
            # Place at hand position with velocity in movement direction
            tp.position[0] = px + random.uniform(-15, 15)
            tp.position[1] = py + random.uniform(-15, 15)
            tp.prev_x = tp.position[0]
            tp.prev_y = tp.position[1]

            # Velocity follows hand movement + random spread
            spread = 1.5
            tp.velocity[0] = dx * 0.8 + random.uniform(-spread, spread)
            tp.velocity[1] = dy * 0.8 + random.uniform(-spread, spread)
            tp.acceleration = [0.0, 0.0]

            # Short life — bright flash then fade
            tp.max_life = random.uniform(30, 80)
            tp.life = tp.max_life
            tp.size = random.uniform(2.0, 5.0)

            spawned += 1
            if spawned >= spawn_count:
                break


# ============================================================
# Visual Polish
# ============================================================

def _draw_hand_aura(
    px: float, py: float, speed: float, burst: bool
) -> None:
    """Draw a soft aura around the hand position.

    Args:
        px, py: Hand position in pixels.
        speed: Smoothed hand speed.
        burst: Whether in burst (fast movement) mode.
    """
    intensity = min(1.0, speed * 10.0)
    rings = 5 if burst else 3

    for i in range(rings):
        radius = 20.0 + i * 25.0 + speed * 80.0 * (i + 1) / rings
        alpha = (rings - i) / rings * 30.0 * (1.0 + intensity)

        if burst:
            py5.stroke(255, 180, 100, alpha)
        else:
            py5.stroke(180, 210, 255, alpha)

        py5.stroke_weight(0.8)
        py5.no_fill()
        py5.circle(px, py, radius)

    # Core glow
    glow_size = 8.0 + speed * 40.0
    for i in range(3):
        r = glow_size * (1.0 - i * 0.3)
        a = 60.0 * (1.0 - i * 0.3) * (1.0 + intensity)
        py5.no_stroke()
        py5.fill(255, 255, 255, a)
        py5.circle(px, py, r)


def _draw_vignette() -> None:
    """Draw a very subtle radial vignette for depth."""
    # Only draw every 10 frames — it's a static effect
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


def _draw_status_overlay(has_data: bool, detected: bool) -> None:
    """Draw OSC connection status and frame info in the top-left corner.

    Args:
        has_data: Whether any OSC message has ever been received.
        detected: Whether a hand is currently detected.
    """
    py5.push()

    # Semi-transparent background for readability
    py5.no_stroke()
    py5.fill(0, 0, 0, 120)
    py5.rect(5, 5, 260, 70)

    # OSC status line
    if _osc_server_error:
        py5.fill(255, 80, 80, 230)
        py5.text(f"X OSC ERROR: {_osc_server_error[:40]}", 14, 24)
    elif has_data and detected:
        py5.fill(80, 255, 80, 230)
        py5.text(f"● OSC live | hand tracked", 14, 24)
    elif has_data:
        py5.fill(255, 200, 60, 230)
        py5.text(f"○ OSC live | hand lost ({_osc_message_count} msgs)", 14, 24)
    else:
        py5.fill(255, 160, 60, 230)
        py5.text(f"◎ Waiting for hand tracker...", 14, 24)
        py5.fill(180, 180, 180, 200)
        py5.text(f"   Run: cd python_tracker && python main.py", 14, 42)

    # FPS
    py5.fill(200, 200, 200, 200)
    py5.text(f"FPS: {_fps_display:.0f}  |  particles: {len(particles)}", 14, 62)

    py5.pop()


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="The Unseen — Visual Renderer")
    parser.add_argument(
        "--osc-port",
        type=int,
        default=OSC_PORT,
        help=f"OSC listen port (default: {OSC_PORT})",
    )
    args = parser.parse_args()
    OSC_PORT = args.osc_port

    print("[Visual] Starting The Unseen...")
    py5.run_sketch()
