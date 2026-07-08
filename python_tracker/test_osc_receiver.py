"""
Minimal OSC receiver for testing hand-data transmission.

Run this first, then run the tracker. You should see hand data printed.

Usage:
    python test_osc_receiver.py [--port 12000]
"""

import argparse
import time

from pythonosc import dispatcher
from pythonosc import osc_server


def hand_handler(address: str, *args) -> None:
    """Handle incoming /hand OSC messages."""
    hand_x, hand_y, hand_speed, hand_detected = args
    status = "DETECTED" if hand_detected > 0.5 else "none"
    print(
        f"[OSC RX] {address} | "
        f"x={hand_x:.3f} y={hand_y:.3f} | "
        f"speed={hand_speed:.4f} | "
        f"{status}"
    )


def main(ip: str = "127.0.0.1", port: int = 12000) -> None:
    disp = dispatcher.Dispatcher()
    disp.map("/hand", hand_handler)
    # Also map a wildcard to catch anything
    disp.set_default_handler(
        lambda addr, *args: print(f"[OSC RX] Unknown: {addr} {args}")
    )

    server = osc_server.ThreadingOSCUDPServer((ip, port), disp)
    print(f"[Test Receiver] Listening on {ip}:{port} — Ctrl+C to stop")
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
