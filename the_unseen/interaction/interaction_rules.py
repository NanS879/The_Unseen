"""
Interaction Rules — one-shot effects for non-ability gestures.

Ability gestures (open_palm, fist, pinch, point, expand, compress)
are driven continuously by GestureManager → SpaceAbilityManager.

This module handles one-shot events for gestures without abilities:
    victory → mode cycle
    swipe → ripple burst
    cross → color invert ripple
    sync → spiral flow
"""

from ..config import Config
from .gesture_manager import (
    GESTURE_VICTORY, GESTURE_SWIPE,
    TWO_HAND_CROSS, TWO_HAND_SYNC,
)


class InteractionRules:
    """One-shot effects for non-ability gestures."""

    MODES = ["normal", "dream", "void", "bloom"]
    _mode_index: int = 0

    @staticmethod
    def apply(
        gesture: str,
        hand_x: float,
        hand_y: float,
        ripple_manager,
        energy_manager,
    ) -> str | None:
        """Apply one-shot effect for a non-ability gesture.

        Returns action name, or None if gesture not handled here.
        """
        if gesture == GESTURE_VICTORY:
            InteractionRules._mode_index = (
                (InteractionRules._mode_index + 1) % len(InteractionRules.MODES)
            )
            if ripple_manager:
                ripple_manager.spawn(hand_x, hand_y, strength=3.0,
                                     color=(255, 255, 255))
            return f"mode_cycle → {InteractionRules.MODES[InteractionRules._mode_index]}"

        elif gesture == GESTURE_SWIPE:
            if ripple_manager:
                for _ in range(3):
                    ripple_manager.spawn(hand_x, hand_y, strength=1.2,
                                         color=Config.Palette.ENERGY_WARM)
            return "ripple_burst"

        elif gesture == TWO_HAND_CROSS:
            if ripple_manager:
                ripple_manager.spawn(hand_x, hand_y, strength=2.0,
                                     color=Config.Palette.MEMORY_PURPLE)
            return "cross"

        elif gesture == TWO_HAND_SYNC:
            return "sync_flow"

        return None

    @staticmethod
    def get_current_mode() -> str:
        return InteractionRules.MODES[InteractionRules._mode_index]
