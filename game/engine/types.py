"""
Datové typy pro Behavior Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List


class WorldEventType(Enum):
    """Typ světové události."""
    STIMULUS = "stimulus"    # Něco se stalo (racek, vítr, zvuk)
    PRESSURE = "pressure"    # Tlak na reakci (otázka, oslovení)
    SILENCE = "silence"      # Ticho - prostor pro iniciativu


@dataclass
class WorldEvent:
    """Světová událost generovaná enginem."""
    event_type: WorldEventType
    description: str = ""
    pressure_target: Optional[str] = None  # ID NPC pokud PRESSURE
    intensity: float = 0.5  # 0.0-1.0, jak silná je událost


@dataclass
class NPCBehaviorState:
    """Stav chování jednoho NPC."""
    npc_id: str
    speak_drive: float = 0.3      # Jak moc chce mluvit (0-1)
    stay_drive: float = 0.7       # Jak moc chce zůstat (0-1)
    cooldown_turns: int = 0       # Kolik tahů musí čekat před další replikou
    energy: float = 1.0           # Energie (0-1), klesá po mluvení

    # Statistiky pro skórování
    speeches_count: int = 0       # Počet replik v této scéně
    last_spoke_turn: int = -1     # Poslední tah kdy mluvil
    last_acted_turn: int = -1     # Poslední tah kdy udělal COKOLI (speech/action/thought)
    last_selected_turn: int = -1  # Poslední tah kdy byl vybrán pro AI (i když vrátil nothing)

    def can_speak(self) -> bool:
        """Může NPC mluvit?"""
        return self.cooldown_turns <= 0 and self.energy > 0.1

    def on_spoke(self, current_turn: int, energy_cost: float = 0.15) -> None:
        """Zavoláno když NPC promluvil."""
        self.speeches_count += 1
        self.last_spoke_turn = current_turn
        self.last_acted_turn = current_turn
        self.energy = max(0.0, self.energy - energy_cost)

    def on_acted(self, current_turn: int) -> None:
        """Zavoláno když NPC udělal action/thought (ne speech)."""
        self.last_acted_turn = current_turn

    def on_selected(self, current_turn: int) -> None:
        """Zavoláno když byl NPC vybrán pro AI volání (i když vrátí nothing)."""
        self.last_selected_turn = current_turn

    def on_turn_start(self, energy_regen: float = 0.05) -> None:
        """Zavoláno na začátku každého tahu."""
        if self.cooldown_turns > 0:
            self.cooldown_turns -= 1
        self.energy = min(1.0, self.energy + energy_regen)


class ResponseType(Enum):
    """Typ odpovědi NPC."""
    SPEECH = "speech"       # Mluvená replika
    THOUGHT = "thought"     # Vnitřní myšlenka (v závorce)
    ACTION = "action"       # Fyzická akce (kouká se, vstane...)
    NOTHING = "nothing"     # Ticho, nic nedělá
    GOODBYE = "goodbye"     # Loučí se a odchází


@dataclass
class NPCResponse:
    """Odpověď NPC z AI."""
    npc_id: str
    response_type: ResponseType
    text: str = ""

    def is_speech(self) -> bool:
        return self.response_type == ResponseType.SPEECH

    def is_leaving(self) -> bool:
        return self.response_type == ResponseType.GOODBYE


@dataclass
class AssistedOption:
    """Možnost pro ASSISTED mód když scéna umírá."""
    label: str           # Krátký popis pro uživatele
    instruction: str     # Instrukce pro AI


@dataclass
class SceneContext:
    """Kontext aktuální scény pro engine."""
    turn_number: int = 0
    last_speech_turn: int = 0
    last_activity_turn: int = 0  # Poslední tah s jakoukoli aktivitou
    total_speeches: int = 0
    total_actions: int = 0
    total_thoughts: int = 0
    scene_energy: float = 0.5
    consecutive_silence: int = 0  # Počet tahů bez řeči
    consecutive_inactivity: int = 0  # Počet tahů bez jakékoli aktivity

    def on_speech(self) -> None:
        """Zavoláno když někdo promluvil."""
        self.last_speech_turn = self.turn_number
        self.last_activity_turn = self.turn_number
        self.total_speeches += 1
        self.consecutive_silence = 0
        self.consecutive_inactivity = 0
        self.scene_energy = min(1.0, self.scene_energy + 0.1)

    def on_action(self) -> None:
        """Zavoláno při fyzické akci (střední aktivita)."""
        self.last_activity_turn = self.turn_number
        self.total_actions += 1
        self.consecutive_inactivity = 0
        # Action nepřeruší consecutive_silence (pro účely ticha v rozhovoru)
        # ale je to aktivita - scene_energy mírně roste
        self.scene_energy = min(1.0, self.scene_energy + 0.03)

    def on_thought(self) -> None:
        """Zavoláno při vnitřní myšlence (malá aktivita)."""
        self.last_activity_turn = self.turn_number
        self.total_thoughts += 1
        self.consecutive_inactivity = 0
        # Thought je minimální aktivita
        self.scene_energy = min(1.0, self.scene_energy + 0.01)

    def on_silence(self) -> None:
        """Zavoláno když nikdo nepromluvil."""
        self.consecutive_silence += 1
        self.scene_energy = max(0.0, self.scene_energy - 0.05)

    def on_nothing(self) -> None:
        """Zavoláno při úplné nečinnosti (nothing)."""
        self.consecutive_silence += 1
        self.consecutive_inactivity += 1
        self.scene_energy = max(0.0, self.scene_energy - 0.07)

    def on_turn_end(self) -> None:
        """Zavoláno na konci tahu."""
        self.turn_number += 1

    def is_dying(self) -> bool:
        """Je scéna 'umírající'? (pro ASSISTED mód)"""
        # Scéna umírá když je dlouhá neaktivita (ne jen ticho)
        return self.consecutive_inactivity >= 2 and self.scene_energy < 0.15

    def is_stale(self) -> bool:
        """Je scéna 'zatuchlá'? (dlouho bez speech, ale nějaká aktivita je)"""
        return self.consecutive_silence >= 4 and self.scene_energy < 0.3


@dataclass
class IntentLogEntry:
    """Záznam pro DEV_INTENT_LOG."""
    timestamp: float
    action: str
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.timestamp:.2f}] {self.action}: {self.details}"
