"""
Centralized configuration for The Unseen V2.

All tunable parameters live here. No magic numbers in any other module.
Import as: from config import Config
Access as: Config.WIDTH, Config.PARTICLE_BG_COUNT, etc.
"""


class Config:
    """Master configuration with nested parameter groups.

    All values are class-level constants for fast import and iteration.
    Grouped by subsystem for readability.
    """

    # ============================================================
    # Canvas
    # ============================================================
    WIDTH: int = 1280
    HEIGHT: int = 720
    BG_COLOR: tuple[int, int, int] = (0, 0, 0)  # Pure black background

    # ============================================================
    # Flow Field
    # ============================================================
    FLOW_ENABLED: bool = True
    FLOW_CELL_SIZE: int = 25          # Grid cell size in pixels
    FLOW_NOISE_SCALE: float = 0.004   # Spatial frequency (smaller = larger swirls)
    FLOW_NOISE_SPEED: float = 0.006   # Temporal evolution rate
    FLOW_STRENGTH: float = 0.30       # Base force magnitude
    FLOW_UPDATE_INTERVAL: int = 3     # Frames between flow field updates

    # ============================================================
    # Influence Field
    # ============================================================
    INFLUENCE_ENABLED: bool = True
    INFLUENCE_RADIUS: float = 250.0       # Max influence radius in pixels
    INFLUENCE_STRENGTH: float = 800.0      # Base attraction strength
    INFLUENCE_MIN_DISTANCE: float = 15.0   # Min distance to avoid singularity
    INFLUENCE_FALLOFF: str = "inverse_square"  # "inverse_square" or "gaussian"
    INFLUENCE_GAUSSIAN_SIGMA: float = 80.0    # Sigma for gaussian falloff
    INFLUENCE_WAKE_STRENGTH: float = 3.0       # Push along hand movement direction

    # Per-layer influence multipliers
    INFLUENCE_WEIGHT_BG: float = 0.05     # Background — barely affected
    INFLUENCE_WEIGHT_INT: float = 1.0     # Interaction — full response
    INFLUENCE_WEIGHT_HL: float = 2.0      # Highlight — amplified

    # ============================================================
    # Particle Layers
    # ============================================================

    # ---- Layer 1: Background (slow drift, large, soft, no trail) ----
    PARTICLE_BG_COUNT: int = 1200
    PARTICLE_BG_SIZE_MIN: float = 2.0
    PARTICLE_BG_SIZE_MAX: float = 5.0
    PARTICLE_BG_SPEED_MAX: float = 1.5
    PARTICLE_BG_DAMPING: float = 0.97
    PARTICLE_BG_LIFE_MIN: float = 300
    PARTICLE_BG_LIFE_MAX: float = 600
    PARTICLE_BG_TRAIL_LENGTH: int = 0       # No trail — performance
    PARTICLE_BG_GLOW_LAYERS: int = 2        # Minimal glow

    # ---- Layer 2: Interaction (main flow followers) ----
    PARTICLE_INT_COUNT: int = 600
    PARTICLE_INT_SIZE_MIN: float = 1.5
    PARTICLE_INT_SIZE_MAX: float = 4.0
    PARTICLE_INT_SPEED_MAX: float = 3.5
    PARTICLE_INT_DAMPING: float = 0.95
    PARTICLE_INT_LIFE_MIN: float = 200
    PARTICLE_INT_LIFE_MAX: float = 400
    PARTICLE_INT_TRAIL_LENGTH: int = 10
    PARTICLE_INT_GLOW_LAYERS: int = 3       # Standard glow

    # ---- Layer 3: Highlight (bright, fast, long trails) ----
    PARTICLE_HL_COUNT: int = 120
    PARTICLE_HL_SIZE_MIN: float = 1.0
    PARTICLE_HL_SIZE_MAX: float = 3.5
    PARTICLE_HL_SPEED_MAX: float = 5.0
    PARTICLE_HL_DAMPING: float = 0.92
    PARTICLE_HL_LIFE_MIN: float = 60
    PARTICLE_HL_LIFE_MAX: float = 150
    PARTICLE_HL_TRAIL_LENGTH: int = 18
    PARTICLE_HL_GLOW_LAYERS: int = 3       # Standard glow

    # ============================================================
    # Particle Lifecycle
    # ============================================================
    LIFECYCLE_BIRTH_RATIO: float = 0.1    # First 10% of life: fade-in
    LIFECYCLE_GROWTH_RATIO: float = 0.3   # 10%-30%: grow to peak
    LIFECYCLE_PEAK_RATIO: float = 0.7     # 30%-70%: full size/opacity
                                           # 70%-100%: decay to death

    # ============================================================
    # Unified Color Palette
    # ============================================================
    class Palette:
        """Color definitions for the unified palette.

        Colors vary dynamically based on lifecycle, speed, and distance,
        but the BASE values define the core identity of each layer.
        """
        # Layer 1 — Background: deep blue
        BG_BASE: tuple[int, int, int] = (100, 140, 220)
        BG_GLOW: tuple[int, int, int] = (60, 100, 180)

        # Layer 2 — Interaction: blue-purple
        INT_BASE: tuple[int, int, int] = (140, 120, 230)
        INT_GLOW: tuple[int, int, int] = (100, 80, 210)

        # Layer 3 — Highlight: warm gold
        HL_BASE: tuple[int, int, int] = (255, 200, 100)
        HL_GLOW: tuple[int, int, int] = (255, 180, 60)

        # Hand aura colors
        HAND_LEFT: tuple[int, int, int] = (255, 150, 255)    # Magenta
        HAND_RIGHT: tuple[int, int, int] = (255, 200, 100)   # Gold

        # Core white (shared across layers for hot center)
        CORE_WHITE: tuple[int, int, int] = (255, 255, 255)

    # ============================================================
    # Motion Trail
    # ============================================================
    TRAIL_ALPHA_IDLE: int = 8       # Background fade alpha when no hand
    TRAIL_ALPHA_ACTIVE: int = 14    # Background fade alpha with hand
    TRAIL_ALPHA_EXCITED: int = 22   # Background fade alpha in excited state
    TRAIL_BASE_LENGTH: int = 15     # Default trail history
    TRAIL_SPEED_SCALE: float = 0.5  # Trail length multiplier per speed unit

    # ============================================================
    # Space State Machine
    # ============================================================
    STATE_EXCITED_SPEED: float = 0.06    # Speed threshold for EXCITED
    STATE_CALM_SPEED: float = 0.02       # Speed threshold for CALM
    STATE_EXCITED_FRAMES: int = 15       # Frames before ACTIVE→EXCITED
    STATE_CALM_FRAMES: int = 90          # Frames before EXCITED→CALM
    STATE_HAND_TIMEOUT: float = 2.0      # Seconds before hand considered lost

    # State-dependent multipliers
    STATE_FLOW_SPEED: dict[str, float] = {
        "IDLE": 0.5,
        "ACTIVE": 1.0,
        "EXCITED": 2.0,
        "CALM": 0.7,
    }
    STATE_INFLUENCE_MULT: dict[str, float] = {
        "IDLE": 0.0,
        "ACTIVE": 1.0,
        "EXCITED": 1.8,
        "CALM": 0.5,
    }
    STATE_TRAIL_MULT: dict[str, float] = {
        "IDLE": 0.5,
        "ACTIVE": 1.0,
        "EXCITED": 2.0,
        "CALM": 0.8,
    }

    # ============================================================
    # Hand Smoothing
    # ============================================================
    HAND_SMOOTHING: float = 0.4          # EMA alpha when hand detected
    HAND_SMOOTHING_FADE: float = 0.05    # EMA alpha when hand lost

    # ============================================================
    # Visual Polish
    # ============================================================
    VIGNETTE_ENABLED: bool = True
    AURA_RINGS: int = 3                  # Rings around hand (5 in excited)
    AURA_RINGS_EXCITED: int = 5

    # ============================================================
    # OSC
    # ============================================================
    OSC_IP: str = "127.0.0.1"
    OSC_PORT: int = 12000

    # ============================================================
    # Debug
    # ============================================================
    DEBUG_SHOW_STATUS: bool = True
    DEBUG_SHOW_FPS: bool = True
