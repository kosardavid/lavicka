"""
events.py - Správa událostí prostředí
======================================

Události prostředí jsou věci které se dějí kolem lavičky
a na které mohou NPC reagovat (déšť, racek, míč, atd.).
"""

import time
import random
import re
import unicodedata
from typing import Optional, List
from dataclasses import dataclass, field


@dataclass
class EnvironmentEvent:
    """Jedna událost prostředí."""
    text: str
    timestamp: float = field(default_factory=time.time)
    ttl: float = 35.0  # Jak dlouho je událost "aktivní"
    target_seat: Optional[int] = None  # 0 nebo 1, nebo None
    affects_both: bool = False

    def is_expired(self, now: float = None) -> bool:
        """Vrací True pokud událost vypršela."""
        now = now or time.time()
        return (now - self.timestamp) > self.ttl


# Fyzické reakce na události (bez AI)
PHYSICAL_REACTIONS = {
    "target": {
        "hit": ["Au!", "Sakra!", "Jejda!", "Au, to zabolelo!"],
        "bird": ["Au!", "Hej, mazej!", "Au, potvora!", "Sakra, to štíplo!"],
        "default": ["Jejda.", "Hm.", "No teda.", "Co to bylo?"],
    },
    "observer": {
        "hit": ["Jejda, jste v pořádku?", "Pozor!", "To bylo těsné…", "Au, to snad ne."],
        "bird": ["Jejda, racek! Nechte ho.", "Pozor, ať vás nezobne.", "To je drzoun…"],
        "rain": ["No tak… začíná pršet.", "Jejda, déšť.", "Hm, to se nám mění počasí."],
        "wind": ["Uf… ten vítr.", "Do očí mi jde písek.", "Fouká to jak blázen."],
        "default": ["Tohle mě vytrhlo.", "Zvláštní moment.", "Chvilka ticha…"],
    },
}

# Klíčová slova pro detekci typu události
EVENT_KEYWORDS = {
    "hit": ["míč", "kop", "bouch", "tref", "do hlavy", "do ruky", "do ramene"],
    "bird": ["racek", "klovn", "klovne", "zob", "zobne", "kříd"],
    "rain": ["prší", "pršet", "déšť", "lij"],
    "wind": ["vítr", "fouk", "písek", "prach"],
    "global": ["prsi", "dest", "lij", "vitr", "fouka", "prach", "pisek", "zima", "boure", "mlha"],
}


class EventManager:
    """
    Správce událostí prostředí.

    Sleduje aktivní události a generuje reakce NPC.
    """

    def __init__(self):
        self.active_events: List[EnvironmentEvent] = []
        self.pending_reaction: Optional[EnvironmentEvent] = None
        self.reaction_window: float = 12.0  # sekund pro reakci

    def add_event(self, text: str, seats: list) -> Optional[EnvironmentEvent]:
        """
        Přidá novou událost prostředí.

        Args:
            text: Popis události
            seats: Seznam NPC na sedadlech [npc0, npc1]

        Returns:
            Vytvořená událost
        """
        text = text.strip()
        if not text:
            return None

        # Zjisti koho se to týká
        target_seat = self._find_target_seat(text, seats)
        affects_both = self._affects_both(text)

        # Pokud není jasný cíl, náhodně vyber
        if target_seat is None:
            occupied = [i for i, s in enumerate(seats) if s]
            target_seat = random.choice(occupied) if occupied else 0

        event = EnvironmentEvent(
            text=text,
            target_seat=target_seat,
            affects_both=affects_both,
        )

        self.active_events.append(event)
        self.pending_reaction = event

        # Limit počtu událostí
        self.active_events = self.active_events[-10:]

        return event

    def _strip_accents(self, s: str) -> str:
        """Odebere diakritiku."""
        return "".join(
            ch for ch in unicodedata.normalize("NFD", s)
            if unicodedata.category(ch) != "Mn"
        )

    def _find_target_seat(self, text: str, seats: list) -> Optional[int]:
        """
        Najde sedadlo které je cílem události.

        Hledá jména postav v textu.
        """
        low = self._strip_accents(text.lower())

        for idx, npc in enumerate(seats):
            if not npc:
                continue
            role = npc.get("role", "") if isinstance(npc, dict) else npc.role
            name = role.split()[-1] if role else ""
            if name and self._strip_accents(name.lower()) in low:
                return idx

        return None

    def _affects_both(self, text: str) -> bool:
        """Rozhodne jestli událost ovlivňuje obě postavy."""
        low = self._strip_accents(text.lower())

        # Plošné události
        if any(k in low for k in EVENT_KEYWORDS["global"]):
            return True

        # Explicitní zmínka obou
        if any(k in low for k in ["na ne", "na oba", "oba", "na vsechny"]):
            return True

        return False

    def get_physical_reaction(self, event_text: str, is_target: bool) -> tuple:
        """
        Vrátí okamžitou fyzickou reakci (bez AI).

        Args:
            event_text: Text události
            is_target: True pokud je NPC přímý cíl

        Returns:
            Tuple (type, text) - např. ("speech", "Au!")
        """
        low = event_text.lower()

        # Určení typu události
        event_type = "default"
        for etype, keywords in EVENT_KEYWORDS.items():
            if etype == "global":
                continue
            if any(k in low for k in keywords):
                event_type = etype
                break

        # Výběr reakce
        role = "target" if is_target else "observer"
        reactions = PHYSICAL_REACTIONS.get(role, {})

        # Hledej specifickou reakci, pak fallback
        if event_type in reactions:
            text = random.choice(reactions[event_type])
            return ("speech", text)

        # Default reakce
        default = reactions.get("default", ["Hm."])
        text = random.choice(default)

        # Pozorovatel má častěji myšlenku
        if not is_target and event_type == "default":
            return ("thought", text)

        return ("speech", text)

    def get_recent_events_text(self, max_count: int = 3) -> str:
        """
        Vrátí text posledních aktivních událostí pro AI prompt.

        Args:
            max_count: Maximální počet událostí

        Returns:
            Text pro prompt nebo prázdný string
        """
        now = time.time()
        self.active_events = [e for e in self.active_events if not e.is_expired(now)]

        if not self.active_events:
            return ""

        items = self.active_events[-max_count:]
        return "\n".join([f"- {e.text}" for e in items])

    def get_pending_event(self) -> Optional[str]:
        """
        Vrátí text čekající události (pokud je v časovém okně).

        Returns:
            Text události nebo None
        """
        if not self.pending_reaction:
            return None

        age = time.time() - self.pending_reaction.timestamp
        if age <= self.reaction_window:
            return self.pending_reaction.text

        self.pending_reaction = None
        return None

    def clear_pending(self):
        """Vymaže čekající událost (po reakci)."""
        self.pending_reaction = None

    def has_pending(self) -> bool:
        """Vrací True pokud je čekající událost."""
        return self.pending_reaction is not None
