"""Quick test: verify all modules import correctly.

Run from project root:
    python tests/test_imports.py
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from the_unseen.config import Config
from the_unseen.perception.camera_tracker import CameraTracker
from the_unseen.perception.hand_state import HandState
from the_unseen.simulation.flow_field import FlowField
from the_unseen.simulation.influence_field import InfluenceField
from the_unseen.simulation.particle import Particle
from the_unseen.simulation.particle_manager import ParticleManager
from the_unseen.simulation.space_state import SpaceState
from the_unseen.life.energy_manager import EnergyManager
from the_unseen.life.behavior_analyzer import BehaviorAnalyzer
from the_unseen.life.organism import OrganismManager
from the_unseen.life.time_system import TimeSystem
from the_unseen.life.persistence import save_state, load_state
from the_unseen.life.memory_seed import MemorySeed
from the_unseen.life.growth_algorithm import DLAEngine
from the_unseen.interaction.ripple import RippleManager
from the_unseen.interaction.fragment import FragmentManager
from the_unseen.interaction.gesture_manager import GestureManager
from the_unseen.interaction.interaction_rules import InteractionRules
from the_unseen.interaction.ability_manager import SpaceAbilityManager
from the_unseen.feedback.feedback_composer import FeedbackComposer
from the_unseen.feedback.procedural_bg import ProceduralBackground
from the_unseen.feedback.visual_system import (
    DepthManager, ParticleVariety, BreathingCamera, StateLighting,
)
from the_unseen.feedback.audio_hook import audio
from the_unseen.ui.render_utils import draw_hand_aura, draw_startup_hint
from the_unseen.ui.debug_overlay import DebugOverlay
from the_unseen.utils.logger import log, set_debug_mode
from the_unseen.utils.easing import smoothstep, ease_out_cubic

set_debug_mode(False)
print("All 30 modules import OK")
