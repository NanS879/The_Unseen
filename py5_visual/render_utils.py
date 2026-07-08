"""
Visual polish rendering utilities.

Hand aura rings, vignette overlay, and debug status display.
These are pure rendering helpers — no state management.
"""

import math

from config import Config
from space_state import SpaceState


def draw_hand_aura(
    py5, px: float, py: float, speed: float, state: str, color: tuple
) -> None:
    """Draw soft multi-ring aura around a hand position.

    More rings appear in EXCITED state. Ring size scales with hand speed.

    Args:
        py5: The py5 module/sketch.
        px, py: Hand pixel position.
        speed: Hand movement speed.
        state: Current SpaceState name.
        color: (r, g, b) aura color.
    """
    intensity = min(1.0, speed * 10.0)
    rings = (
        Config.AURA_RINGS_EXCITED
        if state == SpaceState.EXCITED
        else Config.AURA_RINGS
    )
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


def draw_vignette(py5) -> None:
    """Draw a subtle radial vignette (throttled to every 10 frames)."""
    if not Config.VIGNETTE_ENABLED:
        return
    if py5.frame_count % 10 != 0:
        return

    py5.no_stroke()
    cx, cy = Config.WIDTH / 2, Config.HEIGHT / 2
    max_r = math.sqrt(cx * cx + cy * cy)
    for i in range(5):
        r = max_r * (0.5 + i * 0.1)
        alpha = 3.0 * (1.0 - i / 5.0)
        py5.fill(0, 0, 0, alpha)
        py5.circle(cx, cy, r * 2)


def draw_status_overlay(
    py5,
    space_state: SpaceState | None,
    particle_manager,
    active_hands: list,
    has_hands: bool,
    hand_left,
    hand_right,
    server_error: str | None,
    message_count: int,
    fps_display: float,
) -> None:
    """Draw debug status overlay with state, OSC, FPS, and layer info.

    Args:
        py5: The py5 module/sketch.
        space_state: Current SpaceState instance.
        particle_manager: Current ParticleManager instance.
        active_hands: List of HandState instances with active hands.
        has_hands: Whether hands are currently detected.
        hand_left, hand_right: HandState instances.
        server_error: OSC server error string, if any.
        message_count: Total OSC messages received.
        fps_display: Smoothed FPS value.
    """
    py5.push()
    py5.no_stroke()
    py5.fill(0, 0, 0, 140)
    py5.rect(5, 5, 310, 105)

    y = 22

    # State indicator
    if space_state is not None:
        state_colors = {
            SpaceState.IDLE: (100, 100, 255),
            SpaceState.ACTIVE: (80, 255, 80),
            SpaceState.EXCITED: (255, 180, 60),
            SpaceState.CALM: (120, 200, 255),
        }
        sc = state_colors.get(space_state.state, (200, 200, 200))
        py5.fill(*sc, 230)
        py5.text(
            f"State: {space_state.state} ({space_state.time_in_state:.1f}s)",
            14, y,
        )

    y += 20

    # OSC status
    if server_error:
        py5.fill(255, 80, 80, 230)
        py5.text(f"OSC ERROR: {server_error[:40]}", 14, y)
    elif has_hands:
        parts = []
        for hs in active_hands:
            label = "R" if hs.side == "right" else "L"
            parts.append(
                f"{label}:({hs.raw_x:.2f},{hs.raw_y:.2f}) spd={hs.speed:.3f}"
            )
        py5.fill(80, 255, 80, 230)
        py5.text(f"OSC live | {'  '.join(parts)}", 14, y)
    elif hand_left.has_data or hand_right.has_data:
        py5.fill(255, 200, 60, 230)
        py5.text(f"OSC | hands lost ({message_count} msgs)", 14, y)
    else:
        py5.fill(255, 160, 60, 230)
        py5.text("Waiting for tracker...", 14, y)
        py5.fill(180, 180, 180, 200)
        py5.text("   cd python_tracker && python main.py", 14, y + 18)

    y += 20

    # FPS + layer counts
    if particle_manager is not None:
        counts = particle_manager.layer_counts()
        py5.fill(200, 200, 200, 200)
        py5.text(
            f"FPS:{fps_display:.0f} | BG:{counts['background']} "
            f"INT:{counts['interaction']} HL:{counts['highlight']}",
            14, y + 2,
        )

    py5.pop()
