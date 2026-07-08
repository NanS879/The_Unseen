"""
OSC sender module for transmitting hand data to the py5 visual renderer.

Sends a single composite OSC message per frame to ensure atomicity:
    /hand  [hand_x, hand_y, hand_speed, hand_detected]

All values are floats. hand_detected is 1.0 or 0.0.
"""

from pythonosc import udp_client


class OscHandSender:
    """Lightweight OSC client that sends hand data over UDP.

    Uses SimpleUDPClient — synchronous, fire-and-forget, sufficient for
    30fps real-time transmission on localhost.
    """

    def __init__(
        self, ip: str = "127.0.0.1", port: int = 12000
    ) -> None:
        """Initialize the OSC UDP client.

        Args:
            ip: Target IP address. Use 127.0.0.1 for same-machine.
            port: Target UDP port.
        """
        self._ip = ip
        self._port = port
        self._client = udp_client.SimpleUDPClient(ip, port)
        print(f"[OSC] Sender ready → {ip}:{port}")

    def send_hand_data(self, hand_data: dict) -> None:
        """Send hand data as an OSC message.

        Args:
            hand_data: Dictionary from HandTracker.process_frame() with keys
                hand_x, hand_y, hand_speed, hand_detected.
        """
        self._client.send_message(
            "/hand",
            [
                float(hand_data["hand_x"]),
                float(hand_data["hand_y"]),
                float(hand_data["hand_speed"]),
                float(hand_data["hand_detected"]),
            ],
        )

    def close(self) -> None:
        """Release resources (UDP client is stateless, nothing to do)."""
        pass
