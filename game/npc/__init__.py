"""
npc - Modul pro správu NPC postav
==================================

Obsahuje:
- NPC: Základní třída pro postavy
- ARCHETYPY: Předdefinované typy postav
- npc_depth: Výpočet allowed_depth pro realistické omezení rozhovorů
"""

from .base import NPC
from .archetypes import ARCHETYPY, get_archetype_by_id, get_available_archetypes
from .npc_depth import build_depth_context, calculate_allowed_depth
