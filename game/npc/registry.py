"""
registry.py - Jednoduchý NPC Registry pro dynamické přidávání/odebírání NPC
============================================================================

Cíl:
- NPC nejsou natvrdo ve scéně
- Registry drží dostupné a aktivní NPC
- Lavička si z registry vybere max 2 aktivní NPC
- Když NPC odejde, registry ho deaktivuje
- Pokud je na lavičce <2 NPC, registry doplní nového

OMEZENÍ (v této verzi):
- Bez DB, bez persistence mezi restartami
- Jen pro lavičku (max 2 NPC)
- Bez AI budgeteru
"""

import random
from typing import List, Optional, Set
from .archetypes import ARCHETYPY, get_archetype_by_id


# Debug log callback - nastaví se z app.py
_log_callback = None


def _log(action: str, details: str = "") -> None:
    """Loguje NPC lifecycle akce."""
    msg = f"[REGISTRY] {action}"
    if details:
        msg += f": {details}"
    if _log_callback:
        _log_callback(msg)
    else:
        print(msg)


def set_log_callback(callback) -> None:
    """Nastaví callback pro logování."""
    global _log_callback
    _log_callback = callback


class NpcRegistry:
    """
    Jednoduchý registry pro správu NPC.

    Drží:
    - available_npc_ids: seznam všech NPC co mohou přijít na lavičku
    - active_npc_ids: seznam NPC co jsou aktuálně na lavičce (max 2)
    - cooldown_npc_ids: NPC co nedávno odešli (krátký cooldown)
    """

    def __init__(self):
        # Všechny dostupné NPC ID (z archetypes)
        self.available_npc_ids: Set[str] = set()
        for arch in ARCHETYPY:
            self.available_npc_ids.add(arch["id"])

        # Aktivní NPC (na lavičce)
        self.active_npc_ids: List[str] = []

        # Cooldown - NPC co nedávno odešli (nemůžou hned znovu přijít)
        self.cooldown_npc_ids: Set[str] = set()

        _log("NPC_REGISTRY_INIT", f"available={len(self.available_npc_ids)}")

    def get_active_npc_ids(self) -> List[str]:
        """Vrátí seznam aktivních NPC ID."""
        return list(self.active_npc_ids)

    def get_active_count(self) -> int:
        """Vrátí počet aktivních NPC."""
        return len(self.active_npc_ids)

    def is_active(self, npc_id: str) -> bool:
        """Zjistí jestli je NPC aktivní."""
        return npc_id in self.active_npc_ids

    def activate(self, npc_id: str) -> bool:
        """
        Aktivuje NPC (přidá na lavičku).

        Returns:
            True pokud se podařilo aktivovat
        """
        if npc_id in self.active_npc_ids:
            return False  # Už je aktivní

        if len(self.active_npc_ids) >= 2:
            return False  # Lavička je plná

        if npc_id not in self.available_npc_ids:
            return False  # Neznámé NPC

        self.active_npc_ids.append(npc_id)

        # Odeber z cooldownu
        self.cooldown_npc_ids.discard(npc_id)

        _log("NPC_ACTIVATED", npc_id)
        return True

    def deactivate(self, npc_id: str, reason: str = "unknown") -> bool:
        """
        Deaktivuje NPC (odebere z lavičky).

        Args:
            npc_id: ID NPC
            reason: Důvod odchodu (goodbye, leaving, kicked, ...)

        Returns:
            True pokud se podařilo deaktivovat
        """
        if npc_id not in self.active_npc_ids:
            return False

        self.active_npc_ids.remove(npc_id)

        # Přidej do cooldownu (aby hned znovu nepřišel)
        self.cooldown_npc_ids.add(npc_id)

        _log("NPC_DEACTIVATED", f"{npc_id} (reason={reason})")
        return True

    def fill(self, target: int = 2) -> Optional[str]:
        """
        Doplní lavičku na cílový počet NPC.

        Args:
            target: Cílový počet NPC na lavičce (default 2)

        Returns:
            ID nově aktivovaného NPC nebo None
        """
        if len(self.active_npc_ids) >= target:
            return None  # Lavička je plná

        # Najdi dostupné NPC (ne aktivní, ne v cooldownu)
        candidates = [
            npc_id for npc_id in self.available_npc_ids
            if npc_id not in self.active_npc_ids
            and npc_id not in self.cooldown_npc_ids
        ]

        if not candidates:
            # Pokud nejsou kandidáti mimo cooldown, vezmi i ty v cooldownu
            candidates = [
                npc_id for npc_id in self.available_npc_ids
                if npc_id not in self.active_npc_ids
            ]

        if not candidates:
            return None  # Žádný NPC není k dispozici

        # Vyber náhodně
        npc_id = random.choice(candidates)

        if self.activate(npc_id):
            _log("NPC_FILL", f"added {npc_id}, active={len(self.active_npc_ids)}/{target}")
            return npc_id

        return None

    def clear_cooldowns(self) -> None:
        """Vyčistí cooldowny (např. po delší pauze)."""
        count = len(self.cooldown_npc_ids)
        self.cooldown_npc_ids.clear()
        if count > 0:
            _log("COOLDOWNS_CLEARED", f"removed {count} cooldowns")

    def reset(self) -> None:
        """Resetuje registry (odebere všechny aktivní NPC)."""
        for npc_id in list(self.active_npc_ids):
            self.deactivate(npc_id, reason="reset")
        self.cooldown_npc_ids.clear()
        _log("REGISTRY_RESET", "all NPCs deactivated")

    def get_npc_data(self, npc_id: str) -> Optional[dict]:
        """
        Vrátí data NPC podle ID.

        Args:
            npc_id: ID NPC

        Returns:
            Dict s daty NPC nebo None
        """
        return get_archetype_by_id(npc_id)

    def get_debug_info(self) -> str:
        """Vrátí debug info o stavu registry."""
        return (
            f"active={self.active_npc_ids}, "
            f"cooldown={list(self.cooldown_npc_ids)}, "
            f"available={len(self.available_npc_ids)}"
        )


# === SINGLETON ===

_registry_instance: Optional[NpcRegistry] = None


def get_registry() -> NpcRegistry:
    """Vrátí singleton instanci registry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = NpcRegistry()
    return _registry_instance


def reset_registry() -> None:
    """Resetuje singleton instanci."""
    global _registry_instance
    if _registry_instance:
        _registry_instance.reset()
    _registry_instance = None
