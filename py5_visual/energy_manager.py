"""
EnergyManager — unified energy system for the digital ecosystem.

Energy flows through the entire space:
    Movement → energy gain
    Dwelling → energy converts to organism growth
    Idle → energy slowly decays

All visual systems read energy multipliers to modulate their behavior:
    flow strength, glow intensity, growth speed, particle density.

Design:
    Single source of truth for global energy state.
    Serializable for persistence.
"""

from config import Config


class EnergyManager:
    """Manages global energy pool and provides system multipliers.

    Energy range: 0.0 – ENERGY_MAX (default 100.0)

    Energy mechanics:
        - Movement: +ENERGY_MOVE_GAIN × speed × dt
        - Dwell: energy is consumed by organism growth
        - Idle: -ENERGY_IDLE_DECAY × dt

    Public interface:
        update(state, speed, dt)
        consume(amount) → bool
        get_multipliers() → dict
        serialize()/deserialize()
    """

    def __init__(self, initial_energy: float = 30.0) -> None:
        """Initialize the energy manager.

        Args:
            initial_energy: Starting energy level.
        """
        self.energy = max(0.0, min(Config.ENERGY_MAX, initial_energy))

    def update(
        self,
        has_hands: bool,
        max_speed: float,
        dt: float,
    ) -> None:
        """Update energy for one frame.

        Args:
            has_hands: Whether any hand is detected.
            max_speed: Maximum hand speed this frame.
            dt: Time delta in seconds.
        """
        if has_hands:
            # Movement → energy
            gain = Config.ENERGY_MOVE_GAIN * max_speed * dt
            self.energy = min(Config.ENERGY_MAX, self.energy + gain)
        else:
            # Idle → decay
            self.energy = max(
                0.0,
                self.energy - Config.ENERGY_IDLE_DECAY * dt,
            )

    def consume(self, amount: float) -> bool:
        """Attempt to consume energy. Returns True if sufficient.

        Args:
            amount: Energy to consume.

        Returns:
            True if energy was available and consumed.
        """
        if self.energy >= amount:
            self.energy -= amount
            return True
        return False

    def energy_ratio(self) -> float:
        """Return energy as 0.0–1.0 ratio."""
        return self.energy / Config.ENERGY_MAX

    def get_multipliers(self) -> dict[str, float]:
        """Return system multipliers based on current energy.

        All multipliers are in 0.0–2.0 range.
        At energy=0, systems operate at minimum.
        At energy=50, systems operate at normal.
        At energy=100, systems operate at maximum.
        """
        e = self.energy_ratio()
        return {
            "flow": 0.5 + e * 0.5,       # 0.5 – 1.0
            "glow": 0.4 + e * 0.6,       # 0.4 – 1.0
            "growth": 0.2 + e * 0.8,     # 0.2 – 1.0
            "density": 0.5 + e * 0.5,    # 0.5 – 1.0
            "influence": 0.3 + e * 0.7,  # 0.3 – 1.0
        }

    def serialize(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {"energy": self.energy}

    @classmethod
    def deserialize(cls, data: dict) -> "EnergyManager":
        """Create from serialized dict."""
        return cls(initial_energy=data.get("energy", 30.0))
