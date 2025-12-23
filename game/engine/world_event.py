"""
WorldEvent Generator - generuje světové události.

Director generuje jen WORLD EVENT (STIMULUS/PRESSURE/SILENCE), ne repliky.
NPC pak sami rozhodují jak reagovat.
"""

import random
import time
from typing import Optional, List, Dict, Any

from .types import WorldEvent, WorldEventType, SceneContext


# Ambient události pro STIMULUS
AMBIENT_EVENTS = [
    "Kolem proletěl racek.",
    "Od moře zafoukal vítr.",
    "Někde v dálce zahoukal parník.",
    "Na lavičku dopadl list.",
    "Přeběhla kolem kočka.",
    "V dálce se ozval smích.",
    "Nad mořem zakroužil albatros.",
    "Vlna se silněji rozbila o břeh.",
    "Slunce na chvíli vykouklo z mraků.",
    "Kolem prošel člověk se psem.",
]

# Události pro oživení umírající scény
REVIVAL_EVENTS = [
    "Silnější vlna vystříkla až na břeh.",
    "Náhle se ozval výkřik rackého hejna.",
    "Kolem profrčel cyklista a málem srazil koš.",
    "Začalo drobně mrholit.",
    "Na moři se objevila plachetnice.",
]


class WorldEventGenerator:
    """Generátor světových událostí."""

    def __init__(
        self,
        ambient_time_cooldown: float = 20.0,
        ambient_turn_cooldown: int = 3,
        ambient_chance: float = 0.15,
    ):
        """
        Args:
            ambient_time_cooldown: Minimální čas (sekundy) mezi ambient událostmi
            ambient_turn_cooldown: Minimální počet tahů mezi ambient událostmi
            ambient_chance: Šance na ambient událost (po splnění cooldownů)
        """
        self._last_ambient_time: float = 0
        self._last_ambient_turn: int = -100
        self._ambient_time_cooldown = ambient_time_cooldown
        self._ambient_turn_cooldown = ambient_turn_cooldown
        self._ambient_chance = ambient_chance

    def generate(
        self,
        scene_context: SceneContext,
        forced_event: Optional[str] = None,
        last_response_was_question: bool = False,
        question_target_id: Optional[str] = None,
    ) -> WorldEvent:
        """
        Vygeneruje světovou událost pro aktuální tah.

        Args:
            scene_context: Kontext scény
            forced_event: Vynucená událost od uživatele (klávesa E)
            last_response_was_question: Zda poslední replika byla otázka
            question_target_id: ID NPC na kterého směřuje otázka

        Returns:
            WorldEvent s typem a popisem
        """
        # 1. Vynucená událost od uživatele -> PRESSURE nebo STIMULUS
        if forced_event:
            return self._create_forced_event(forced_event)

        # 2. Poslední replika byla otázka -> PRESSURE na druhého
        if last_response_was_question and question_target_id:
            return WorldEvent(
                event_type=WorldEventType.PRESSURE,
                description="Čeká se na odpověď na otázku.",
                pressure_target=question_target_id,
                intensity=0.7,
            )

        # 3. Scéna "umírá" -> zkus STIMULUS pro oživení
        if scene_context.is_dying():
            return self._create_revival_event()

        # 4. Náhodná ambient událost (s cooldownem turn + time)
        if self._should_generate_ambient(scene_context.turn_number):
            return self._create_ambient_event(scene_context.turn_number)

        # 5. Výchozí: SILENCE - prostor pro iniciativu
        return WorldEvent(
            event_type=WorldEventType.SILENCE,
            description="Ticho. Prostor pro iniciativu.",
            intensity=0.3,
        )

    def _create_forced_event(self, event_text: str) -> WorldEvent:
        """Vytvoří událost z textu od uživatele."""
        # Detekuj jestli je to otázka/oslovení (PRESSURE) nebo jen událost (STIMULUS)
        pressure_keywords = ["?", "oslovil", "zeptal", "řekl", "křikl"]
        is_pressure = any(kw in event_text.lower() for kw in pressure_keywords)

        return WorldEvent(
            event_type=WorldEventType.PRESSURE if is_pressure else WorldEventType.STIMULUS,
            description=event_text,
            intensity=0.8,
        )

    def _create_revival_event(self) -> WorldEvent:
        """Vytvoří událost pro oživení umírající scény."""
        event = random.choice(REVIVAL_EVENTS)
        return WorldEvent(
            event_type=WorldEventType.STIMULUS,
            description=event,
            intensity=0.6,
        )

    def _create_ambient_event(self, current_turn: int) -> WorldEvent:
        """Vytvoří náhodnou ambient událost."""
        self._last_ambient_time = time.time()
        self._last_ambient_turn = current_turn
        event = random.choice(AMBIENT_EVENTS)
        return WorldEvent(
            event_type=WorldEventType.STIMULUS,
            description=event,
            intensity=0.4,
        )

    def _should_generate_ambient(self, current_turn: int) -> bool:
        """
        Má se generovat ambient událost?

        Kombinuje turn-based i time-based cooldown pro robustní chování
        nezávisle na rychlosti automatu.
        """
        # Time cooldown check
        if time.time() - self._last_ambient_time < self._ambient_time_cooldown:
            return False

        # Turn cooldown check
        if current_turn - self._last_ambient_turn < self._ambient_turn_cooldown:
            return False

        # Šance na ambient událost
        return random.random() < self._ambient_chance


def detect_question_target(
    last_response_text: str,
    last_speaker_id: str,
    all_npc_ids: List[str],
) -> Optional[str]:
    """
    Detekuje na koho směřuje otázka v poslední replice.

    Returns:
        ID NPC na kterého směřuje otázka, nebo None
    """
    if "?" not in last_response_text:
        return None

    # Otázka směřuje na druhého NPC (ne na mluvícího)
    for npc_id in all_npc_ids:
        if npc_id != last_speaker_id:
            return npc_id

    return None
