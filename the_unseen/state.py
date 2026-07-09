"""
Shared application state — single source of truth for all globals.

Import as: from .state import S
Access: S.flow_field, S.particle_manager, etc.

This decouples __main__.py callbacks from main.py helpers.
Both modules import `S` — same object, same namespace.
"""

from .config import Config
from .perception.camera_tracker import CameraTracker
from .perception.hand_state import HandState
from .simulation.flow_field import FlowField
from .simulation.influence_field import InfluenceField
from .simulation.particle_manager import ParticleManager
from .simulation.space_state import SpaceState
from .life.energy_manager import EnergyManager
from .life.behavior_analyzer import BehaviorAnalyzer
from .life.organism import OrganismManager
from .life.time_system import TimeSystem
from .interaction.ripple import RippleManager
from .interaction.fragment import FragmentManager
from .interaction.gesture_manager import GestureManager
from .interaction.ability_manager import SpaceAbilityManager
from .feedback.feedback_composer import FeedbackComposer
from .feedback.procedural_bg import ProceduralBackground
from .feedback.visual_system import DepthManager, BreathingCamera, StateLighting
from .ui.debug_overlay import DebugOverlay


class AppState:
    """Singleton application state. All globals go here.

    Created once at module import time. __main__.py callbacks
    and main.py helpers both import `S` — same object.
    """

    def __init__(self) -> None:
        # Hands
        self.hand_left = HandState("left", Config.WIDTH * 0.35, Config.HEIGHT / 2)
        self.hand_right = HandState("right", Config.WIDTH * 0.65, Config.HEIGHT / 2)

        # V2 Simulation
        self.camera: CameraTracker | None = None
        self.flow_field: FlowField | None = None
        self.influence_field: InfluenceField | None = None
        self.particle_manager: ParticleManager | None = None
        self.space_state: SpaceState | None = None

        # V3 Life
        self.energy_manager: EnergyManager | None = None
        self.behavior_analyzer: BehaviorAnalyzer | None = None
        self.organism_manager: OrganismManager | None = None
        self.time_system: TimeSystem | None = None

        # V4 Interaction
        self.debug_overlay: DebugOverlay | None = None
        self.ripple_manager: RippleManager | None = None
        self.fragment_manager: FragmentManager | None = None
        self.gesture_manager: GestureManager | None = None
        self.ability_manager: SpaceAbilityManager | None = None
        self.feedback: FeedbackComposer | None = None

        # V6 Visual
        self.bg_renderer: ProceduralBackground | None = None
        self.depth_mgr: DepthManager | None = None
        self.breath_cam: BreathingCamera | None = None
        self.state_light: StateLighting | None = None

        # Timing
        self.frame_start_ms: float = 0.0
        self.fps_display: float = 0.0
        self.autosave_timer: float = 0.0
        self.release_mode: bool = False
        self.fresh_start: bool = False


# ── Module-level singleton ────────────────────────────
S = AppState()
