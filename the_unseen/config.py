"""
Centralized configuration for The Unseen V2.

All tunable parameters live here. No magic numbers in any other module.
Import as: from .config import Config
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

    # ---- Layer 1: Background (slow drift, subtle, no trail, minimal glow) ----
    PARTICLE_BG_COUNT: int = 800
    PARTICLE_BG_SIZE_MIN: float = 3.0
    PARTICLE_BG_SIZE_MAX: float = 7.0
    PARTICLE_BG_SPEED_MAX: float = 1.2
    PARTICLE_BG_DAMPING: float = 0.97
    PARTICLE_BG_LIFE_MIN: float = 300
    PARTICLE_BG_LIFE_MAX: float = 600
    PARTICLE_BG_GLOW_LAYERS: int = 1

    # ---- Layer 2: Interaction (main flow followers, no trail) ----
    PARTICLE_INT_COUNT: int = 400
    PARTICLE_INT_SIZE_MIN: float = 2.5
    PARTICLE_INT_SIZE_MAX: float = 6.0
    PARTICLE_INT_SPEED_MAX: float = 3.0
    PARTICLE_INT_DAMPING: float = 0.95
    PARTICLE_INT_LIFE_MIN: float = 200
    PARTICLE_INT_LIFE_MAX: float = 400
    PARTICLE_INT_GLOW_LAYERS: int = 2

    # ---- Layer 3: Highlight (bright, fast, trails only here) ----
    PARTICLE_HL_COUNT: int = 80
    PARTICLE_HL_SIZE_MIN: float = 1.5
    PARTICLE_HL_SIZE_MAX: float = 4.5
    PARTICLE_HL_SPEED_MAX: float = 4.5
    PARTICLE_HL_DAMPING: float = 0.92
    PARTICLE_HL_LIFE_MIN: float = 50
    PARTICLE_HL_LIFE_MAX: float = 120
    PARTICLE_HL_GLOW_LAYERS: int = 2

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
        """State-based color themes for visual identity.

        Each state has: primary (dominant), secondary (accent), ambient (background).
        Particle layers interpolate between their base colors and state theme.
        """

        # ── State Color Themes ─────────────────────────────
        class Theme:
            """Per-state color identity."""
            _themes = {
                "IDLE": {
                    "primary":    (60, 100, 180),
                    "secondary":  (100, 150, 220),
                    "ambient":    (10, 20, 50),
                    "particle":   (80, 130, 210),
                    "glow":       (50, 90, 170),
                    "warmth":     0.2,
                },
                "ACTIVE": {
                    "primary":    (140, 110, 220),
                    "secondary":  (180, 150, 240),
                    "ambient":    (15, 10, 40),
                    "particle":   (130, 110, 220),
                    "glow":       (110, 80, 200),
                    "warmth":     0.5,
                },
                "EXCITED": {
                    "primary":    (240, 180, 60),
                    "secondary":  (255, 210, 120),
                    "ambient":    (25, 15, 5),
                    "particle":   (230, 190, 80),
                    "glow":       (220, 160, 50),
                    "warmth":     0.9,
                },
                "CALM": {
                    "primary":    (80, 180, 200),
                    "secondary":  (130, 210, 230),
                    "ambient":    (5, 20, 35),
                    "particle":   (70, 170, 200),
                    "glow":       (50, 150, 180),
                    "warmth":     0.3,
                },
            }

            @staticmethod
            def get(state: str) -> dict:
                return Config.Palette.Theme._themes.get(
                    state, Config.Palette.Theme._themes["IDLE"])


        # ── Layer Identity Colors ──────────────────────────
        BG_BASE: tuple[int, int, int]  = (100, 140, 220)
        BG_GLOW: tuple[int, int, int]  = (60, 100, 180)
        INT_BASE: tuple[int, int, int] = (140, 120, 230)
        INT_GLOW: tuple[int, int, int] = (100, 80, 210)
        HL_BASE: tuple[int, int, int]  = (255, 200, 100)
        HL_GLOW: tuple[int, int, int]  = (255, 180, 60)

        # ── Hands ──────────────────────────────────────────
        HAND_LEFT: tuple[int, int, int]  = (255, 150, 255)
        HAND_RIGHT: tuple[int, int, int] = (255, 200, 100)

        # ── Digital Organism ───────────────────────────────
        LIFE_BLUE: tuple[int, int, int]     = (80, 140, 255)
        LIFE_DEEP: tuple[int, int, int]     = (30, 60, 160)
        MEMORY_PURPLE: tuple[int, int, int] = (160, 120, 240)
        MEMORY_DIM: tuple[int, int, int]    = (80, 50, 160)
        ENERGY_GOLD: tuple[int, int, int]   = (255, 210, 80)
        ENERGY_WARM: tuple[int, int, int]   = (255, 160, 40)
        GROWTH_WHITE: tuple[int, int, int]  = (240, 240, 255)
        GROWTH_PALE: tuple[int, int, int]   = (200, 210, 255)

    # ============================================================
    # Background Fade (per state alpha for motion blur effect)
    # ============================================================
    FADE_ALPHA_IDLE: int = 4
    FADE_ALPHA_ACTIVE: int = 8
    FADE_ALPHA_EXCITED: int = 14

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

    # ============================================================
    # Hand Smoothing
    # ============================================================
    HAND_SMOOTHING: float = 0.4          # EMA alpha when hand detected
    HAND_SMOOTHING_FADE: float = 0.05    # EMA alpha when hand lost

    # ============================================================
    # Debug
    # ============================================================
    DEBUG_ENABLED: bool = True           # Logger debug mode default

    # ============================================================
    # V3 — Digital Organism
    # ============================================================
    V3_ENABLED: bool = True

    # ---- Memory Seed ----
    SEED_DWELL_RADIUS: float = 80.0         # px — hand must stay within this
    SEED_DWELL_TIME: float = 1.5            # seconds of dwelling to create seed
    SEED_DWELL_SPEED_MAX: float = 0.10      # max speed to count as "dwelling"
    SEED_MAX_ENERGY: float = 100.0
    SEED_ENERGY_RATE: float = 20.0          # energy gained per second of dwell
    SEED_ENERGY_DECAY: float = 2.0          # energy lost per second when absent
    SEED_GROWTH_THRESHOLD: float = 40.0     # energy needed to begin growth

    # ---- DLA Growth ----
    DLA_WALKERS_PER_FRAME: int = 40         # Walkers per frame (faster growth)
    DLA_MAX_STEPS: int = 150                # Max steps before walker dies
    DLA_STICK_RADIUS: float = 4.0           # px — contact distance
    DLA_MAX_RADIUS: float = 150.0           # px — max cluster radius
    DLA_SPAWN_MARGIN: float = 20.0          # px beyond current radius

    # ---- Energy System ----
    ENERGY_MAX: float = 100.0
    ENERGY_MOVE_GAIN: float = 8.0           # per unit speed per second
    ENERGY_IDLE_DECAY: float = 1.5          # per second when no hands
    ENERGY_GROWTH_COST: float = 25.0        # one-time cost to spawn organism

    # ---- Organism Ecosystem ----
    ORGANISM_MAX_COUNT: int = 8
    ORGANISM_MIN_DISTANCE: float = 80.0     # px minimum between organisms
    ORGANISM_CONNECT_DISTANCE: float = 200.0  # px to draw connection line

    # ---- Time System ----
    TIME_CYCLE_SECONDS: float = 300.0       # 5 min = one full day/night

    # ---- Persistence ----
    PERSISTENCE_AUTOSAVE_INTERVAL: float = 30.0  # seconds
    PERSISTENCE_FILE: str = "the_unseen_state.json"

