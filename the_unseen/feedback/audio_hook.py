"""
Audio Hook — interface for future audio integration.

Currently a stub. All methods accept the same parameters
so audio can be wired in later without changing any caller.

Future backends: pygame.mixer, sounddevice, pydub, FMOD, Wwise.

Usage:
    from .audio_hook import audio
    audio.play("connect", volume=0.8, pitch=1.0)
"""


class AudioHook:
    """Audio interface stub. All methods are no-ops until a backend is set."""

    def __init__(self) -> None:
        self._backend = None
        self._muted: bool = False
        self._master_volume: float = 1.0

    def set_backend(self, backend) -> None:
        """Wire in a real audio backend (pygame.mixer, etc.)."""
        self._backend = backend

    def mute(self) -> None:
        self._muted = True

    def unmute(self) -> None:
        self._muted = False

    def set_master_volume(self, vol: float) -> None:
        self._master_volume = max(0.0, min(1.0, vol))

    def play(
        self,
        name: str,
        volume: float = 1.0,
        pitch: float = 1.0,
        pan: float = 0.0,
        fade_in: float = 0.0,
    ) -> None:
        """Play a sound event.

        Args:
            name: Sound identifier ("connect", "gather", "create",
                  "guide", "expand", "merge", "ripple", "collect").
            volume: 0.0–1.0.
            pitch: Playback speed multiplier (1.0 = normal).
            pan: -1.0 (left) to 1.0 (right). For future spatial audio.
            fade_in: Volume ramp duration in seconds.
        """
        if self._muted or self._backend is None:
            return
        vol = volume * self._master_volume
        try:
            self._backend.play(name, volume=vol, pitch=pitch,
                              pan=pan, fade_in=fade_in)
        except Exception:
            pass  # Audio is non-critical

    def stop(self, name: str, fade_out: float = 0.0) -> None:
        """Stop a specific sound."""
        if self._backend:
            try:
                self._backend.stop(name, fade_out=fade_out)
            except Exception:
                pass

    def stop_all(self, fade_out: float = 0.2) -> None:
        """Stop all sounds."""
        if self._backend:
            try:
                self._backend.stop_all(fade_out=fade_out)
            except Exception:
                pass

    def on_ability(self, ability: str, stage: str) -> None:
        """Convenience: play the right sound for an ability stage.

        Args:
            ability: "connect", "gather", "create", etc.
            stage: "charge", "activate", or "complete".
        """
        if stage == "charge":
            self.play(f"{ability}_charge", volume=0.5, fade_in=0.1)
        elif stage == "activate":
            self.play(ability, volume=0.9)
        elif stage == "complete":
            self.play(f"{ability}_complete", volume=0.6, fade_in=0.2)


# Singleton instance
audio = AudioHook()
