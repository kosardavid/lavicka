"""
rules - Pravidla hry
=====================

Obsahuje:
- Relationships: Správa vztahů mezi NPC
- Events: Události prostředí
- Director: Režisér scény
"""

from .relationships import RelationshipManager
from .events import EventManager
from .director import Director
