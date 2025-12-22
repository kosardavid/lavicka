"""
base.py - Základní třída NPC
=============================

Definuje strukturu a chování NPC postavy.
"""

import random
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NPC:
    """
    Reprezentuje jednu NPC postavu na lavičce.

    Attributes:
        id: Unikátní identifikátor (např. "babicka_vlasta")
        role: Zobrazované jméno (např. "Babička Vlasta")
        vek: Věk postavy
        color: RGB barva pro vykreslení
        vibe: Popis osobnosti pro AI prompt
        popis: Krátký popis vzhledu
        rod: "muž" nebo "žena" - pro správné skloňování

        intent: Aktuální záměr postavy
        emotion: Současná emoce
        emotion_intensity: Intenzita emoce (0-100)
        baseline_mood: Základní nálada (-30 až +30)
        chce_odejit: True pokud chce postava odejít
    """

    # Základní identifikace
    id: str
    role: str
    vek: int
    color: tuple
    vibe: str
    popis: str
    rod: str

    # Stav
    intent: str = "Chce si v klidu posedět."
    emotion: str = "calm"
    emotion_intensity: int = 30
    baseline_mood: int = 0
    chce_odejit: bool = False

    def __post_init__(self):
        """Inicializuje náhodné hodnoty emocí."""
        if self.baseline_mood == 0:
            self.baseline_mood = random.randint(-10, 10)
        if self.emotion == "calm":
            self.emotion = random.choice(["calm", "bored", "content", "curious"])
        if self.emotion_intensity == 30:
            self.emotion_intensity = random.randint(15, 45)

    @classmethod
    def from_archetype(cls, archetype: dict) -> "NPC":
        """
        Vytvoří NPC z archetypu (slovníku).

        Args:
            archetype: Slovník s definicí postavy

        Returns:
            Nová instance NPC
        """
        return cls(
            id=archetype["id"],
            role=archetype["role"],
            vek=archetype["vek"],
            color=archetype["color"],
            vibe=archetype["vibe"],
            popis=archetype["popis"],
            rod=archetype["rod"],
        )

    def to_dict(self) -> dict:
        """Převede NPC na slovník (pro zpětnou kompatibilitu)."""
        return {
            "id": self.id,
            "role": self.role,
            "vek": self.vek,
            "color": self.color,
            "vibe": self.vibe,
            "popis": self.popis,
            "rod": self.rod,
            "intent": self.intent,
            "emotion": self.emotion,
            "emotion_intensity": self.emotion_intensity,
            "baseline_mood": self.baseline_mood,
            "chce_odejit": self.chce_odejit,
        }

    def get_emotion_hint(self) -> str:
        """Vrátí textový popis emočního stavu pro AI prompt."""
        return (
            f"Emoce: {self.emotion} "
            f"(intenzita {self.emotion_intensity}%), "
            f"dlouhodobá nálada {self.baseline_mood:+d}."
        )

    def drift_emotions(self, spoke_type: str):
        """
        Posune emoce po tahu.

        Args:
            spoke_type: "speech" nebo "thought"
        """
        if spoke_type == "thought":
            self.emotion_intensity = max(
                0, min(100, self.emotion_intensity + random.randint(-6, 4))
            )
            if self.emotion in ("engaged", "amused") and random.random() < 0.25:
                self.emotion = "content"
        else:
            self.emotion_intensity = max(
                0, min(100, self.emotion_intensity + random.randint(-4, 6))
            )
            if self.emotion == "bored" and random.random() < 0.25:
                self.emotion = "curious"
            if self.emotion == "curious" and random.random() < 0.15:
                self.emotion = "engaged"

        # Občas změna základní nálady
        if random.random() < 0.05:
            self.baseline_mood = max(
                -30, min(30, self.baseline_mood + random.choice([-1, 1]))
            )

    def apply_event_effect(self):
        """Aplikuje efekt události prostředí na emoce."""
        self.emotion_intensity = max(
            0, min(100, self.emotion_intensity + random.randint(6, 14))
        )
        if random.random() < 0.35:
            self.emotion = random.choice(["curious", "tense", "irritated", "restless"])
