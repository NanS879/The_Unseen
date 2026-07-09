"""
Structured logger with Debug/Release modes.

All project output goes through this logger. In Release mode,
only INFO/WARN/ERROR messages are shown. In Debug mode, all
messages including per-frame stats are visible.

Usage:
    from logger import log
    log("V3", "Seed created", level="INFO")
    log("Perf", f"FPS: {fps:.0f}", level="DEBUG")
"""

import time
from typing import Optional


class Logger:
    """Singleton logger with configurable verbosity.

    Levels: DEBUG < INFO < WARN < ERROR
    Debug mode: all messages shown.
    Release mode: only INFO and above.
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"

    _instance: Optional["Logger"] = None

    def __new__(cls) -> "Logger":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        self.debug_mode: bool = True
        self._start_time: float = time.time()
        self._message_count: int = 0
        self._throttle_last: dict[str, float] = {}

    def set_debug(self, enabled: bool) -> None:
        """Toggle debug mode."""
        self.debug_mode = enabled

    def log(
        self,
        source: str,
        message: str,
        level: str = "INFO",
        throttle: float = 0.0,
    ) -> None:
        """Log a message.

        Args:
            source: Module or subsystem name (e.g. "V3", "OSC", "Perf").
            message: The log message.
            level: DEBUG, INFO, WARN, or ERROR.
            throttle: Minimum seconds between identical messages from
                this source (0 = no throttle).
        """
        if not self.debug_mode and level == "DEBUG":
            return

        # Throttle check
        if throttle > 0:
            key = f"{source}:{message[:40]}"
            now = time.time()
            if key in self._throttle_last:
                if now - self._throttle_last[key] < throttle:
                    return
            self._throttle_last[key] = now

        self._message_count += 1
        elapsed = time.time() - self._start_time

        # Color markers per level (for terminal visibility)
        markers = {
            "DEBUG": "  ",
            "INFO": "  ",
            "WARN": "⚠ ",
            "ERROR": "✗ ",
        }
        marker = markers.get(level, "  ")

        print(f"[{elapsed:7.1f}s] [{source:5s}] {marker}{message}")


# Module-level convenience
_log = Logger()


def set_debug_mode(enabled: bool) -> None:
    """Enable or disable debug output globally."""
    _log.set_debug(enabled)


def log(
    source: str,
    message: str,
    level: str = "INFO",
    throttle: float = 0.0,
) -> None:
    """Log a message through the global logger."""
    _log.log(source, message, level, throttle)
