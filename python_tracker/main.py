"""
Hand Tracker — Main Entry Point

Captures webcam frames, runs MediaPipe hand detection, sends hand data
via OSC to the py5 visual renderer, and optionally shows a debug window.

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
    """Run the hand-tracking loop.

    Args:
        debug: If True, show the OpenCV debug window.
        osc_ip: Target IP for OSC messages.
        osc_port: Target port for OSC messages.
    """
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

    print("[Tracker] Initializing MediaPipe Hands...")
    tracker = HandTracker(
        max_num_hands=1,
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

            # Mirror for natural interaction (move left → hand goes left)
            frame = cv2.flip(frame, 1)

            # Process hand detection
            hand_data = tracker.process_frame(frame)

            # Send via OSC (always — visual side decides what to do)
            sender.send_hand_data(hand_data)

            # Print hand data to console (every ~30 frames to avoid spam)
            frame_count += 1
            if frame_count % 30 == 0:
                now = time.perf_counter()
                fps_display = 30.0 / (now - fps_time)
                fps_time = now
                status = (
                    f"hand=({hand_data['hand_x']:.3f}, {hand_data['hand_y']:.3f})"
                    if hand_data["hand_detected"] > 0.5
                    else "hand=none"
                )
                print(
                    f"[Tracker] FPS: {fps_display:.1f} | "
                    f"{status} | "
                    f"speed={hand_data['hand_speed']:.4f}"
                )

            if debug:
                # Draw debug overlay
                viz = tracker.draw_debug(frame, hand_data)

                # Show FPS and OSC status on debug window
                cv2.putText(
                    viz,
                    f"FPS: {fps_display:.1f}",
                    (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )
                cv2.putText(
                    viz,
                    f"OSC → {osc_ip}:{osc_port}",
                    (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (200, 200, 200),
                    1,
                )

                cv2.imshow("Hand Tracker (q to quit)", viz)

                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    print("[Tracker] Quit requested.")
                    break
            else:
                # Still need to pump the event loop for the window system
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
        "--no-debug",
        action="store_true",
        help="Disable the debug preview window",
    )
    parser.add_argument(
        "--osc-ip",
        default=OSC_IP,
        help=f"OSC target IP (default: {OSC_IP})",
    )
    parser.add_argument(
        "--osc-port",
        type=int,
        default=OSC_PORT,
        help=f"OSC target port (default: {OSC_PORT})",
    )
    args = parser.parse_args()
    main(debug=not args.no_debug, osc_ip=args.osc_ip, osc_port=args.osc_port)
