"""
OSC sender module for transmitting dual-hand data to the py5 visual renderer.

Sends per-hand OSC messages:
    /hand/left   [hand_x, hand_y, hand_speed, hand_detected]
    /hand/right  [hand_x, hand_y, hand_speed, hand_detected]

When no hands are detected, sends a single /hand/none message
so the visual side knows the tracker is alive.
"""

from pythonosc import udp_client


class OscHandSender:
    """Lightweight OSC client that sends dual-hand data over UDP."""

    def __init__(
        self, ip: str = "127.0.0.1", port: int = 12000
    ) -> None:
        self._ip = ip
        self._port = port
        self._client = udp_client.SimpleUDPClient(ip, port)
        print(f"[OSC] Sender ready -> {ip}:{port}")

    def send_hand_data(self, hands_data: list[dict]) -> None:
        """Send hand data for all detected hands as per-hand OSC messages.

        Args:
            hands_data: List of hand dicts from HandTracker.process_frame(),
                each with keys hand_x, hand_y, hand_speed, hand_side,
                hand_detected.
        """
        sent_sides: set[str] = set()

        for hand in hands_data:
            side = hand["hand_side"].lower()  # "left" or "right"
            addr = f"/hand/{side}"
            self._client.send_message(
                addr,
                [
                    float(hand["hand_x"]),
                    float(hand["hand_y"]),
                    float(hand["hand_speed"]),
                    float(hand["hand_detected"]),
                ],
            )
            sent_sides.add(side)

        # For sides not detected, send a "not detected" message
        for side in ("left", "right"):
            if side not in sent_sides:
                self._client.send_message(
                    f"/hand/{side}",
                    [0.0, 0.0, 0.0, 0.0],  # hand_detected=0.0 signals absence
                )

    def close(self) -> None:
        """Release resources (UDP client is stateless)."""
        pass
