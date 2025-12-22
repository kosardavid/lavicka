"""
relationships.py - Správa vztahů mezi NPC
==========================================

Sleduje:
- Familiarity: jak dobře se znají (0-25)
- Sympathy: sympatie (-1 až +1)
- Tykání: jestli si tykají
- Výměna jmen: jestli si řekli jména

Nyní s persistencí - načítá data z vztahy.json při startu.
"""

import random
from typing import Optional
from ..utils.helpers import pair_key
from ..memory import get_pamet


class Relationship:
    """Reprezentuje vztah mezi dvěma NPC."""

    def __init__(self):
        self.familiarity: float = 0.0
        self.sympathy: float = random.uniform(-0.05, 0.25)
        self.tykani: bool = False
        self.name_exchange: bool = False
        self.pending_tykani: Optional[dict] = None

    def to_dict(self) -> dict:
        """Převede na slovník."""
        return {
            "familiarity": self.familiarity,
            "sympathy": self.sympathy,
            "tykani": self.tykani,
            "name_exchange": self.name_exchange,
            "pending_tykani": self.pending_tykani,
        }


class RelationshipManager:
    """
    Správce vztahů mezi NPC.

    Ukládá a aktualizuje vztahy během hry.
    Nyní s persistencí - načítá data z vztahy.json při startu.
    """

    def __init__(self):
        self._relationships: dict[str, Relationship] = {}
        self._pamet = get_pamet()
        self._load_from_persistence()

    def _load_from_persistence(self):
        """Načte vztahy z persistentního úložiště (vztahy.json)."""
        for key, data in self._pamet.vztahy.items():
            rel = Relationship()
            # Sympatie z persistence
            rel.sympathy = data.get("sympatie", 0.0)
            # Tykání z persistence
            rel.tykani = data.get("tykani", False)
            # Familiarity odhadneme z počtu setkání a fáze
            pocet = data.get("pocet_setkani", 0)
            faze = data.get("faze", "cizinci")
            if faze == "pratele":
                rel.familiarity = max(15.0, min(25.0, pocet * 0.8))
            elif faze == "znami":
                rel.familiarity = max(10.0, min(20.0, pocet * 0.6))
            elif faze == "tvare":
                rel.familiarity = max(5.0, min(12.0, pocet * 0.5))
            else:
                rel.familiarity = min(5.0, pocet * 0.4)
            # Name exchange - pokud si tykají, pravděpodobně si řekli jména
            rel.name_exchange = rel.tykani
            self._relationships[key] = rel

    def _get_id(self, npc) -> str:
        """Získá ID z NPC (dict nebo objekt)."""
        if isinstance(npc, dict):
            return npc.get("id", npc.get("role", "unknown"))
        return getattr(npc, "id", getattr(npc, "role", "unknown"))

    def get(self, npc_a, npc_b) -> Relationship:
        """
        Získá vztah mezi dvěma NPC.

        Args:
            npc_a: První NPC (dict nebo objekt s 'id')
            npc_b: Druhé NPC (dict nebo objekt s 'id')

        Returns:
            Relationship objekt
        """
        id_a = self._get_id(npc_a)
        id_b = self._get_id(npc_b)
        key = pair_key(id_a, id_b)

        if key not in self._relationships:
            self._relationships[key] = Relationship()

        return self._relationships[key]

    def get_dict(self, npc_a, npc_b) -> dict:
        """Získá vztah jako slovník (pro zpětnou kompatibilitu)."""
        return self.get(npc_a, npc_b).to_dict()

    def update_after_speech(self, speaker, other, text: str):
        """
        Aktualizuje vztah po promluvě.

        Args:
            speaker: NPC které mluvilo
            other: Druhé NPC
            text: Text promluvy
        """
        vztah = self.get(speaker, other)

        # Zvyš familiarity
        vztah.familiarity = min(25.0, vztah.familiarity + 1.0)

        # Analyzuj sentiment
        t = text.lower()

        # Pozitivní slova
        positive = ["děku", "příjemn", "hezk", "rád", "těší", "super", "skvě", "mil"]
        if any(x in t for x in positive):
            vztah.sympathy = min(1.0, vztah.sympathy + 0.08)

        # Negativní slova
        negative = ["otrava", "blb", "hloup", "naštv", "hrozn"]
        if any(x in t for x in negative):
            vztah.sympathy = max(-1.0, vztah.sympathy - 0.08)

        # Detekce výměny jmen
        if not vztah.name_exchange:
            if ("jmenuji se" in t) or ("jmenuju se" in t):
                if vztah.familiarity >= 4 and vztah.sympathy >= 0.10:
                    vztah.name_exchange = True

        # Detekce tykání
        self._check_tykani(vztah, speaker, text)

    def _check_tykani(self, vztah: Relationship, speaker, text: str):
        """Kontroluje návrh/přijetí tykání."""
        t = text.lower()
        speaker_id = self._get_id(speaker)

        if vztah.tykani:
            return

        # Návrh tykání
        navrh_phrases = [
            "nechcete si tykat",
            "můžeme si tykat",
            "mohli bychom si tykat",
            "budeme si tykat",
            "tykání?",
        ]
        if any(x in t for x in navrh_phrases):
            vztah.pending_tykani = {"from": speaker_id}

        # Přijetí tykání
        prijeti_phrases = [
            "klidně si tykejme",
            "ano, můžeme si tykat",
            "tak si tykejme",
            "dobře, tykejme",
            "klidně tykejte",
        ]
        if vztah.pending_tykani and any(x in t for x in prijeti_phrases):
            if vztah.pending_tykani.get("from") != speaker_id:
                vztah.tykani = True
                vztah.pending_tykani = None

        # Odmítnutí tykání
        if vztah.pending_tykani and "raději zatím" in t and "vykání" in t:
            vztah.pending_tykani = None

    def should_propose_name_exchange(self, npc_a, npc_b) -> bool:
        """
        Rozhodne jestli je vhodné navrhnout výměnu jmen.

        Returns:
            True pokud je vhodné se představit
        """
        vztah = self.get(npc_a, npc_b)
        if vztah.name_exchange:
            return False
        if vztah.familiarity < 5:
            return False
        if vztah.sympathy < 0.25:
            return False
        return random.random() < 0.22

    def should_propose_tykani(self, npc_a, npc_b) -> bool:
        """
        Rozhodne jestli je vhodné navrhnout tykání.

        Returns:
            True pokud je vhodné navrhnout tykání
        """
        vztah = self.get(npc_a, npc_b)
        if vztah.tykani:
            return False
        if vztah.pending_tykani:
            return False
        if vztah.familiarity < 9:
            return False
        if vztah.sympathy < 0.45:
            return False
        return random.random() < 0.14

    def get_pacing_rule(self, npc_a, npc_b) -> str:
        """
        Vrátí pravidlo tempa konverzace podle familiarity.

        Returns:
            Text pro AI prompt
        """
        vztah = self.get(npc_a, npc_b)

        if vztah.familiarity < 5:
            return """Tempo:
- Jste cizinci. Držte se malého rozhovoru: počasí, moře, jaký byl den.
- Žádné návrhy na kafe, schůzky, kontakty ani plány na později.
- Žádná osobní/intimní témata."""

        elif vztah.familiarity < 10:
            return """Tempo:
- Už se trochu znáte, ale stále opatrně.
- Můžete se zeptat na práci/koníčky, ale stále bez domlouvání schůzek."""

        else:
            return """Tempo:
- Už proběhlo více výměn. Můžete být o trochu osobnější, ale stále realisticky."""

    def get_addressing_rule(self, npc_a, npc_b) -> str:
        """
        Vrátí pravidlo oslovování (tykání/vykání).

        Returns:
            Text pro AI prompt
        """
        vztah = self.get(npc_a, npc_b)

        if vztah.tykani:
            return "Můžete TYKAT (ty/tobě/tebe). Oslovuj křestním jménem."
        else:
            return "MUSÍTE VYKAT (vy/vás/vám). NIKDY NETYKEJ! Nepoužívej křestní jména - řekni 'pane/paní' nebo vůbec neoslovuj."

    def get_silence_chance(self, npc_a, npc_b) -> float:
        """
        Vrátí pravděpodobnost ticha (nikdo nic neřekne).

        Čím víc se znají, tím méně ticha.
        """
        vztah = self.get(npc_a, npc_b)

        if vztah.familiarity < 6:
            return 0.55
        elif vztah.familiarity < 12:
            return 0.35
        else:
            return 0.22
