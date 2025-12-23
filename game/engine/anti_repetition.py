"""
Anti-repetition Tracker - sleduje opakování frází a témat.

Penalizuje NPC které se opakují, aby rozhovory byly pestřejší.
"""

from typing import List, Dict, Set
from dataclasses import dataclass, field
from collections import deque
import re


@dataclass
class AntiRepetitionTracker:
    """Sleduje opakování frází a témat."""

    max_phrases: int = 10      # Kolik posledních frází sledovat
    max_topics: int = 5        # Kolik posledních témat sledovat
    max_starts: int = 8        # Kolik posledních začátků replik sledovat
    phrase_threshold: float = 0.5  # Podobnost frází pro penalizaci

    # Interní stav per NPC
    _recent_phrases: Dict[str, deque] = field(default_factory=dict)
    _recent_topics: Dict[str, deque] = field(default_factory=dict)
    _recent_starts: Dict[str, deque] = field(default_factory=dict)  # Začátky replik

    def _ensure_npc(self, npc_id: str) -> None:
        """Zajistí že NPC má inicializované fronty."""
        if npc_id not in self._recent_phrases:
            self._recent_phrases[npc_id] = deque(maxlen=self.max_phrases)
        if npc_id not in self._recent_topics:
            self._recent_topics[npc_id] = deque(maxlen=self.max_topics)
        if npc_id not in self._recent_starts:
            self._recent_starts[npc_id] = deque(maxlen=self.max_starts)

    def record_speech(self, npc_id: str, text: str, topics: List[str] = None) -> None:
        """
        Zaznamená repliku NPC.

        Args:
            npc_id: ID NPC
            text: Text repliky
            topics: Seznam témat v replice (volitelné)
        """
        self._ensure_npc(npc_id)

        # Extrahuj klíčové fráze z textu
        phrases = self._extract_phrases(text)
        for phrase in phrases:
            self._recent_phrases[npc_id].append(phrase.lower())

        # Zaznamenej začátek repliky (první 2-3 slova)
        start = self._extract_start(text)
        if start:
            self._recent_starts[npc_id].append(start)

        # Zaznamenej témata
        if topics:
            for topic in topics:
                self._recent_topics[npc_id].append(topic.lower())

    def get_penalty(self, npc_id: str, proposed_text: str) -> float:
        """
        Vypočítá penalizaci za opakování.

        Args:
            npc_id: ID NPC
            proposed_text: Navrhovaný text repliky

        Returns:
            Penalizace 0.0-1.0 (0 = žádné opakování, 1 = silné opakování)
        """
        self._ensure_npc(npc_id)

        if not proposed_text:
            return 0.0

        # 1. Penalizace za opakující se fráze/slova
        proposed_phrases = self._extract_phrases(proposed_text)
        recent = list(self._recent_phrases[npc_id])

        phrase_penalty = 0.0
        if recent and proposed_phrases:
            matches = 0
            for phrase in proposed_phrases:
                phrase_lower = phrase.lower()
                for old_phrase in recent:
                    if self._phrases_similar(phrase_lower, old_phrase):
                        matches += 1
                        break
            phrase_penalty = matches / len(proposed_phrases)

        # 2. Penalizace za opakující se začátky replik ("Ano, ...", "No, ...")
        start_penalty = 0.0
        proposed_start = self._extract_start(proposed_text)
        recent_starts = list(self._recent_starts[npc_id])

        if proposed_start and recent_starts:
            # Kolikrát se tento začátek opakuje?
            count = sum(1 for s in recent_starts if s == proposed_start)
            if count >= 3:
                start_penalty = 0.8  # 3+ opakování = vysoká penalizace
            elif count >= 2:
                start_penalty = 0.5  # 2 opakování = střední
            elif count >= 1:
                start_penalty = 0.2  # 1 opakování = mírná

        # Kombinuj penalizace (max z obou, aby se neignorovalo)
        combined = max(phrase_penalty * 1.2, start_penalty)
        return min(1.0, combined)

    def get_all_penalties(self, npc_ids: List[str]) -> Dict[str, float]:
        """
        Vrátí aktuální penalizace pro všechna NPC (bez navrhovaného textu).

        Pro použití před AI voláním - penalizace založená na minulém opakování.
        """
        penalties = {}
        for npc_id in npc_ids:
            self._ensure_npc(npc_id)
            recent = list(self._recent_phrases[npc_id])

            if len(recent) < 3:
                penalties[npc_id] = 0.0
                continue

            # Penalizace podle toho jak moc se NPC opakuje sám
            unique = len(set(recent))
            repetition_ratio = 1.0 - (unique / len(recent))
            penalties[npc_id] = repetition_ratio * 0.5

        return penalties

    def clear(self, npc_id: str = None) -> None:
        """Vymaže historii pro NPC nebo všechny."""
        if npc_id:
            self._recent_phrases.pop(npc_id, None)
            self._recent_topics.pop(npc_id, None)
            self._recent_starts.pop(npc_id, None)
        else:
            self._recent_phrases.clear()
            self._recent_topics.clear()
            self._recent_starts.clear()

    def _extract_start(self, text: str) -> str:
        """Extrahuje normalizovaný začátek repliky (první slovo)."""
        if not text:
            return ""

        # Odstraň interpunkci a rozděl na slova
        clean = re.sub(r'[^\w\s]', ' ', text.lower()).strip()
        words = clean.split()

        if not words:
            return ""

        # Vrať jen první slovo - to je klíčové pro detekci "Ano, ..." patternů
        return words[0]

    def _extract_phrases(self, text: str) -> List[str]:
        """Extrahuje klíčové fráze z textu."""
        # Odstraň interpunkci a rozděl na slova
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.lower().split()

        # Filtruj stopwords (ale ne podle délky - "ano" je důležité)
        stopwords = {'a', 'i', 'o', 'u', 'v', 'k', 's', 'z', 'na', 'do', 'to',
                     'je', 'se', 'že', 'by', 'si', 'ale', 'tak', 'jak', 'co',
                     'ten', 'ta', 'ty', 'já', 'on', 'ona', 'vy', 'my', 'oni'}
        words = [w for w in words if w not in stopwords]

        # Vrať unikátní slova jako "fráze"
        return list(set(words))

    def _phrases_similar(self, phrase1: str, phrase2: str) -> bool:
        """Zjistí jestli jsou dvě fráze podobné."""
        # Přesná shoda
        if phrase1 == phrase2:
            return True

        # Začátek shody (pro skloňování)
        min_len = min(len(phrase1), len(phrase2))
        if min_len >= 4:
            if phrase1[:4] == phrase2[:4]:
                return True

        return False

    def should_reject(
        self,
        npc_id: str,
        proposed_text: str,
        threshold: float = 0.6,
    ) -> bool:
        """
        Rozhodne jestli by měla být replika odmítnuta kvůli opakování.

        Args:
            npc_id: ID NPC
            proposed_text: Navrhovaný text
            threshold: Práh pro odmítnutí (default 0.6)

        Returns:
            True pokud by replika měla být odmítnuta
        """
        penalty = self.get_penalty(npc_id, proposed_text)
        return penalty > threshold

    def get_rejection_action(
        self,
        npc_id: str,
        proposed_text: str,
    ) -> str:
        """
        Vrátí doporučenou akci při vysoké repetici.

        Args:
            npc_id: ID NPC
            proposed_text: Navrhovaný text

        Returns:
            "accept" | "downgrade_to_thought" | "downgrade_to_action" | "reject"
        """
        penalty = self.get_penalty(npc_id, proposed_text)

        if penalty < 0.4:
            return "accept"
        elif penalty < 0.6:
            return "downgrade_to_thought"
        elif penalty < 0.8:
            return "downgrade_to_action"
        else:
            return "reject"
