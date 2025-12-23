"""
Behavior Engine modul pro Lavička nad mořem.

Nový systém řízení NPC chování:
- WorldEvent generátor (STIMULUS/PRESSURE/SILENCE)
- NPC rozhodují sami na základě speak_drive, stay_drive, cooldown, energy
- TOP K NPC jdou do AI, ostatní čekají
- Anti-repetition tracking
"""

from .types import (
    WorldEventType,
    WorldEvent,
    NPCBehaviorState,
    ResponseType,
    NPCResponse,
    AssistedOption,
    SceneContext,
)
from .world_event import WorldEventGenerator
from .scorer import SpeakScorer
from .anti_repetition import AntiRepetitionTracker
from .drive_update import DriveUpdater
from .behavior_engine import BehaviorEngine, DEV_INTENT_LOG

__all__ = [
    "WorldEventType",
    "WorldEvent",
    "NPCBehaviorState",
    "ResponseType",
    "NPCResponse",
    "AssistedOption",
    "SceneContext",
    "WorldEventGenerator",
    "SpeakScorer",
    "AntiRepetitionTracker",
    "DriveUpdater",
    "BehaviorEngine",
    "DEV_INTENT_LOG",
]
