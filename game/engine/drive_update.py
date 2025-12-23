"""
drive_update.py - Dynamická aktualizace speak_drive a stay_drive.

Toto je klíčový modul pro přirozené chování NPC.
speak_drive a stay_drive se mění podle:
- WorldEvent (PRESSURE boost, SILENCE růst pro mluvné)
- Scene energy (nízká = klesá stay_drive)
- Anti-repetition penalty (opakování = klesá chuť mluvit)
- Energie NPC (nízká = klesá speak_drive)
- Cooldown (po mluvení krátký drop)
"""

import re
from typing import Dict, Optional
from .types import WorldEvent, WorldEventType, NPCBehaviorState, SceneContext


class DriveUpdater:
    """Aktualizuje speak_drive a stay_drive NPC."""

    def __init__(
        self,
        pressure_boost: float = 0.25,
        silence_growth_rate: float = 0.03,
        low_energy_penalty: float = 0.1,
        repetition_penalty_factor: float = 0.15,
        stay_drive_decay_on_dead_scene: float = 0.08,
        stay_drive_decay_on_low_energy: float = 0.05,
        stay_drive_boost_on_good_scene: float = 0.02,
    ):
        """
        Args:
            pressure_boost: Boost speak_drive při PRESSURE na NPC
            silence_growth_rate: Růst speak_drive při SILENCE (pro mluvné)
            low_energy_penalty: Penalizace speak_drive při nízké energii
            repetition_penalty_factor: Snížení speak_drive za opakování
            stay_drive_decay_on_dead_scene: Pokles stay_drive při mrtvé scéně
            stay_drive_decay_on_low_energy: Pokles stay_drive při nízké energii NPC
            stay_drive_boost_on_good_scene: Boost stay_drive při živé scéně
        """
        self.pressure_boost = pressure_boost
        self.silence_growth_rate = silence_growth_rate
        self.low_energy_penalty = low_energy_penalty
        self.repetition_penalty_factor = repetition_penalty_factor
        self.stay_drive_decay_on_dead_scene = stay_drive_decay_on_dead_scene
        self.stay_drive_decay_on_low_energy = stay_drive_decay_on_low_energy
        self.stay_drive_boost_on_good_scene = stay_drive_boost_on_good_scene

    def update_drives(
        self,
        state: NPCBehaviorState,
        npc_data: Dict,
        world_event: WorldEvent,
        scene_context: SceneContext,
        anti_rep_penalty: float = 0.0,
        was_addressed: bool = False,
    ) -> None:
        """
        Aktualizuje speak_drive a stay_drive NPC.

        Args:
            state: Stav NPC k aktualizaci (mutuje se)
            npc_data: Data NPC z postavy.json
            world_event: Aktuální světová událost
            scene_context: Kontext scény
            anti_rep_penalty: Penalizace za opakování (0-1)
            was_addressed: Bylo NPC přímo osloveno?
        """
        povaha = npc_data.get("povaha", {})
        mluvnost = povaha.get("mluvnost", 0.5)

        # === SPEAK DRIVE ===
        self._update_speak_drive(
            state, mluvnost, world_event, anti_rep_penalty, was_addressed
        )

        # === STAY DRIVE ===
        self._update_stay_drive(
            state, scene_context, anti_rep_penalty
        )

    def _update_speak_drive(
        self,
        state: NPCBehaviorState,
        mluvnost: float,
        world_event: WorldEvent,
        anti_rep_penalty: float,
        was_addressed: bool,
    ) -> None:
        """Aktualizuje speak_drive."""
        drive = state.speak_drive

        # 1. PRESSURE na toto NPC -> boost
        if world_event.event_type == WorldEventType.PRESSURE:
            if world_event.pressure_target == state.npc_id:
                drive += self.pressure_boost * world_event.intensity

        # 2. Přímé oslovení -> boost
        if was_addressed:
            drive += 0.15

        # 3. SILENCE -> růst jen u mluvných postav
        if world_event.event_type == WorldEventType.SILENCE:
            # Introvert (mluvnost < 0.3) neroste
            # Extrovert (mluvnost > 0.7) roste rychle
            if mluvnost > 0.3:
                growth = self.silence_growth_rate * (mluvnost - 0.3) * 2
                drive += growth

        # 4. Nízká energie -> penalizace
        if state.energy < 0.3:
            penalty = self.low_energy_penalty * (0.3 - state.energy) / 0.3
            drive -= penalty

        # 5. Cooldown -> mírná penalizace
        if state.cooldown_turns > 0:
            drive -= 0.05 * state.cooldown_turns

        # 6. Anti-repetition penalty -> snížení chuti mluvit
        if anti_rep_penalty > 0:
            drive -= self.repetition_penalty_factor * anti_rep_penalty

        # 7. Po promluvení -> drop (resetuje se v on_spoke, tady jen drobný)
        # (už je v cooldown logice)

        # Clamp na 0-1
        state.speak_drive = max(0.0, min(1.0, drive))

    def _update_stay_drive(
        self,
        state: NPCBehaviorState,
        scene_context: SceneContext,
        anti_rep_penalty: float,
    ) -> None:
        """Aktualizuje stay_drive."""
        drive = state.stay_drive

        # 1. Mrtvá scéna (is_dying) -> klesá chuť zůstat
        if scene_context.is_dying():
            drive -= self.stay_drive_decay_on_dead_scene

        # 2. Dlouhé ticho -> mírný pokles
        if scene_context.consecutive_silence >= 3:
            drive -= 0.03 * (scene_context.consecutive_silence - 2)

        # 3. Nízká energie NPC -> klesá chuť zůstat
        if state.energy < 0.2:
            drive -= self.stay_drive_decay_on_low_energy

        # 4. Vysoká repetice -> nuda, klesá chuť zůstat
        if anti_rep_penalty > 0.5:
            drive -= 0.05 * (anti_rep_penalty - 0.5)

        # 5. Živá scéna (vysoká scene_energy) -> boost
        if scene_context.scene_energy > 0.6:
            drive += self.stay_drive_boost_on_good_scene

        # 6. Příliš dlouhý rozhovor -> únava
        if scene_context.total_speeches > 20:
            drive -= 0.02 * (scene_context.total_speeches - 20) / 10

        # Clamp na 0-1
        state.stay_drive = max(0.0, min(1.0, drive))

    def on_after_speech(
        self,
        state: NPCBehaviorState,
        was_successful: bool = True,
    ) -> None:
        """
        Zavoláno po úspěšné replice.

        Args:
            state: Stav NPC
            was_successful: Byla replika úspěšná (ne rejected)?
        """
        if was_successful:
            # Po mluvení krátký drop speak_drive
            state.speak_drive = max(0.0, state.speak_drive - 0.1)
        else:
            # Rejected (anti-rep) -> frustrující, ale ne moc
            state.speak_drive = max(0.0, state.speak_drive - 0.05)


def _generate_vocative_forms(name: str) -> list:
    """
    Generuje možné vokativní tvary českého jména.

    Základní pravidla:
    - Vlasta -> Vlasto (ženská jména na -a)
    - Babička -> Babičko (ženská jména na -ka)
    - Karel -> Karle (mužská jména na souhlásku)
    - Stařek -> Stařku (jména na -ek)
    """
    forms = [name.lower()]
    name_lower = name.lower()

    # Ženská jména na -a -> -o
    if name_lower.endswith("a"):
        forms.append(name_lower[:-1] + "o")

    # Jména na -ek -> -ku (Stařek -> Stařku)
    if name_lower.endswith("ek"):
        forms.append(name_lower[:-2] + "ku")

    # Jména na -ka -> -ko (Babička -> Babičko)
    if name_lower.endswith("ka"):
        forms.append(name_lower[:-2] + "ko")

    # Mužská jména na souhlásku -> přidej -e (Karel -> Karle)
    if name_lower and name_lower[-1] not in "aeiouyáéíóúůý":
        forms.append(name_lower + "e")

    # Jména na -el -> -le (Pavel -> Pavle)
    if name_lower.endswith("el"):
        forms.append(name_lower[:-2] + "le")

    return forms


def detect_addressing(
    last_response_text: str,
    npc_name: str,
    npc_titul: str = "",
) -> bool:
    """
    Detekuje jestli byla poslední replika adresována tomuto NPC.

    Používá regex s word boundary aby nechytala substrings (např. "babička" v "babičkami").
    Kontroluje začátek věty pro oslovení.

    Args:
        last_response_text: Text poslední repliky
        npc_name: Jméno NPC
        npc_titul: Titul NPC (Babička, Manažer...)

    Returns:
        True pokud bylo NPC osloveno
    """
    if not last_response_text:
        return False

    text_lower = last_response_text.lower()

    # Kontrola jména (včetně vokativních tvarů) - celé slovo na začátku věty nebo po čárce
    if npc_name:
        vocative_forms = _generate_vocative_forms(npc_name)
        for form in vocative_forms:
            # Vzor: začátek textu/věty nebo po čárce, pak jméno, pak konec slova
            # (^|[.!?]\s*|,\s*) - začátek nebo po interpunkci/čárce
            # \b{form}\b - celé slovo
            pattern = rf'(^|[.!?]\s*|,\s*){re.escape(form)}\b'
            if re.search(pattern, text_lower):
                return True

    # Kontrola titulu (včetně vokativních tvarů)
    if npc_titul:
        vocative_forms = _generate_vocative_forms(npc_titul)
        for form in vocative_forms:
            pattern = rf'(^|[.!?]\s*|,\s*){re.escape(form)}\b'
            if re.search(pattern, text_lower):
                return True

    # Obecné oslovení (Vy, Ty na začátku věty nebo po interpunkci)
    # "Vy jste...", "Ty máš...", "A vy?", "Co ty?"
    # Pattern: začátek nebo po . ! ? - pak volitelně "a " - pak vy/ty/vám/vás
    addressing_pattern = r'(^|[.!?]\s*)(a\s+)?(vy|ty|vám|vás|tobě|tebe)\b'
    if re.search(addressing_pattern, text_lower):
        return True

    return False
