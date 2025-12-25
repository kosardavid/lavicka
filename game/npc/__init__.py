"""
npc - Modul pro správu NPC postav
==================================

Obsahuje:
- NPC: Základní třída pro postavy
- ARCHETYPY: Předdefinované typy postav
- npc_depth: Výpočet allowed_depth pro realistické omezení rozhovorů
- registry: Dynamická správa aktivních NPC na lavičce
"""

from .base import NPC
from .archetypes import ARCHETYPY, get_archetype_by_id, get_available_archetypes
from .npc_depth import build_depth_context, calculate_allowed_depth
from .registry import NpcRegistry, get_registry, reset_registry, set_log_callback
