"""
Minimal OSC receiver for testing dual-hand data transmission.

Run this first, then run the tracker. You should see per-hand data printed.

Usage:
    python test_osc_receiver.py [--port 12000]
"""

import argparse
import time

from pythonosc import dispatcher
from pythonosc import osc_server


def make_handler(side: str):
    """Create a handler for a specific hand side."""
    def handler(address: str, *args) -> None:
        hand_x, hand_y, hand_speed, hand_detected = args
        status = "DETECTED" if hand_detected > 0.5 else "none"
        print(
            f"[OSC RX] {side:5s} | "
            f"x={hand_x:.3f} y={hand_y:.3f} | "
            f"speed={hand_speed:.4f} | "
            f"{status}"
        )
    return handler


def main(ip: str = "127.0.0.1", port: int = 12000) -> None:
    disp = dispatcher.Dispatcher()
    disp.map("/hand/left", make_handler("left"))
    disp.map("/hand/right", make_handler("right"))
    disp.set_default_handler(
        lambda addr, *args: print(f"[OSC RX] Unknown: {addr} {args}")
    )

    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"[Test Receiver] Listening on {ip}:{port} — Ctrl+C to stop")
    print("[Test Receiver] Waiting for /hand/left and /hand/right...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[Test Receiver] Stopped.")
    finally:
        server.shutdown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OSC Test Receiver")
    parser.add_argument("--port", type=int, default=12000)
    args = parser.parse_args()
    main(port=args.port)
