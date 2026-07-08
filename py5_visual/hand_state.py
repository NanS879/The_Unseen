"""
Hand state tracking and OSC communication.

HandState: Smoothed hand position/speed with EMA filtering.
OSC setup: Dual-hand OSC receiver in a daemon thread.
"""

import threading
import time

from pythonosc import dispatcher
from pythonosc import osc_server

from config import Config


class HandState:
    """Smoothed state for a single tracked hand.

    Raw OSC data is smoothed with exponential moving average (EMA)
    to eliminate jitter while maintaining responsiveness.
    """

    def __init__(self, side: str, default_x: float, default_y: float) -> None:
        self.side = side
        self.default_x = default_x
        self.default_y = default_y

        # Raw OSC data (updated from handler thread)
        self.raw_x: float = default_x / Config.WIDTH
        self.raw_y: float = default_y / Config.HEIGHT
        self.raw_speed: float = 0.0
        self.detected: bool = False
        self.last_update: float = 0.0
        self.has_data: bool = False

        # Smoothed pixel-space values
        self.px: float = default_x
        self.py: float = default_y
        self.speed: float = 0.0
        self.dx: float = 0.0
        self.dy: float = 0.0

    def update_smoothing(
        self, alpha: float, target_px: float, target_py: float, target_speed: float
    ) -> None:
        """Advance EMA smoothing by one step."""
        prev_px, prev_py = self.px, self.py
        self.px += (target_px - self.px) * alpha
        self.py += (target_py - self.py) * alpha
        self.speed += (target_speed - self.speed) * alpha
        self.dx = self.px - prev_px
        self.dy = self.py - prev_py


# Shared globals for OSC thread communication
_hand_lock = threading.Lock()
_osc_message_count: int = 0
_osc_server_error: str | None = None


def get_lock() -> threading.Lock:
    """Return the shared hand-state lock."""
    return _hand_lock


def get_message_count() -> int:
    """Return total OSC messages received."""
    return _osc_message_count


def get_server_error() -> str | None:
    """Return OSC server error message, if any."""
    return _osc_server_error


def make_osc_handler(side: str, hand_left, hand_right):
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


def start_osc_server(
    ip: str, port: int, hand_left: HandState, hand_right: HandState
) -> None:
    """Start OSC receiver in daemon thread.

    Args:
        ip: OSC listen IP.
        port: OSC listen port.
        hand_left: Left HandState instance.
        hand_right: Right HandState instance.
    """
    global _osc_server_error
    disp = dispatcher.Dispatcher()
    disp.map("/hand/left", make_osc_handler("left", hand_left, hand_right))
    disp.map("/hand/right", make_osc_handler("right", hand_left, hand_right))

    try:
        server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    except OSError as e:
        _osc_server_error = str(e)
        print(f"[Visual] ERROR: Cannot bind OSC to {ip}:{port} — {e}")
        return

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[Visual] OSC listening on {ip}:{port}")
