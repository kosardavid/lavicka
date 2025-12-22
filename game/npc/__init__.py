"""
npc - Modul pro správu NPC postav
==================================

Obsahuje:
- NPC: Základní třída pro postavy
- ARCHETYPY: Předdefinované typy postav
"""

from .base import NPC
from .archetypes import ARCHETYPY, get_archetype_by_id, get_available_archetypes
