"""
Hand Tracker — Main Entry Point

Captures webcam frames, runs MediaPipe hand detection (up to 2 hands),
sends dual-hand data via OSC to the py5 visual renderer.

Usage:
    python main.py [--no-debug] [--osc-ip 127.0.0.1] [--osc-port 12000]

Press 'q' to quit.
"""

import argparse
import sys
import time

import cv2

from hand_tracking import HandTracker
from osc_sender import OscHandSender

# --- Configuration ---
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
OSC_IP = "127.0.0.1"
OSC_PORT = 12000
# ---------------------


def main(debug: bool = True, osc_ip: str = OSC_IP, osc_port: int = OSC_PORT) -> None:
    """Run the dual-hand tracking loop."""
    print("[Tracker] Initializing camera...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        print("[Tracker] ERROR: Cannot open camera index", CAMERA_INDEX)
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"[Tracker] Camera opened: {int(actual_w)}x{int(actual_h)}")

    print("[Tracker] Initializing MediaPipe Hands (dual-hand mode)...")
    tracker = HandTracker(
        max_num_hands=2,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    )

    print("[Tracker] Initializing OSC sender...")
    sender = OscHandSender(ip=osc_ip, port=osc_port)

    print("[Tracker] Ready. Press 'q' to quit.")

    frame_count = 0
    fps_time = time.perf_counter()
    fps_display = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[Tracker] WARNING: Dropped frame")
                continue

            # Mirror for natural interaction
            frame = cv2.flip(frame, 1)

            # Process hand detection (returns list of hand dicts)
            hands_data = tracker.process_frame(frame)

            # Send via OSC
            sender.send_hand_data(hands_data)

            # Status print (every ~30 frames)
            frame_count += 1
            if frame_count % 30 == 0:
                now = time.perf_counter()
                fps_display = 30.0 / (now - fps_time)
                fps_time = now

                if hands_data:
                    parts = []
                    for h in hands_data:
                        parts.append(
                            f"{h['hand_side']}: ({h['hand_x']:.3f}, {h['hand_y']:.3f})"
                            f" speed={h['hand_speed']:.4f}"
                        )
                    status = " | ".join(parts)
                else:
                    status = "hands=none"

                print(f"[Tracker] FPS: {fps_display:.1f} | {status}")

            if debug:
                viz = tracker.draw_debug(frame, hands_data)
                cv2.putText(
                    viz,
                    f"FPS: {fps_display:.1f}",
                    (30, viz.shape[0] - 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    viz,
                    f"OSC -> {osc_ip}:{osc_port}",
                    (30, viz.shape[0] - 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                )
                cv2.putText(
                    viz,
                    f"Hands: {len(hands_data)}",
                    (30, viz.shape[0] - 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 255, 255),
                    1,
                )
                cv2.imshow("Hand Tracker — Dual Hand (q to quit)", viz)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("[Tracker] Quit requested.")
                    break
            else:
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("[Tracker] Quit requested.")
                    break

    except KeyboardInterrupt:
        print("\n[Tracker] Interrupted.")

    finally:
        sender.close()
        tracker.close()
        cap.release()
        cv2.destroyAllWindows()
        print("[Tracker] Shut down.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hand Tracker for The Unseen")
    parser.add_argument(
        "--no-debug", action="store_true", help="Disable the debug preview window"
    )
    parser.add_argument("--osc-ip", default=OSC_IP, help=f"OSC target IP (default: {OSC_IP})")
    parser.add_argument("--osc-port", type=int, default=OSC_PORT, help=f"OSC target port (default: {OSC_PORT})")
    args = parser.parse_args()
    main(debug=not args.no_debug, osc_ip=args.osc_ip, osc_port=args.osc_port)
