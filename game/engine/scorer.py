"""
SpeakScorer - výběr TOP K NPC pro AI volání.

Skóruje NPC podle jejich stavu a světové události,
vybírá ty s nejvyšším skóre pro AI generování.

Obsahuje anti-starvation mechanismus pro low-engagement NPC.
"""

import random
from typing import List, Dict, Optional
from dataclasses import dataclass

from .types import WorldEvent, WorldEventType, NPCBehaviorState


@dataclass
class NPCScore:
    """Skóre jednoho NPC."""
    npc_id: str
    score: float
    breakdown: Dict[str, float]  # Rozpad skóre pro debug


class SpeakScorer:
    """Skóruje NPC a vybírá TOP K pro AI."""

    def __init__(
        self,
        pressure_bonus: float = 0.4,
        stimulus_bonus: float = 0.2,
        cooldown_penalty: float = 0.3,
        low_energy_penalty: float = 0.2,
        just_acted_penalty: float = 0.25,  # Penalizace za právě provedenou akci
        just_selected_penalty: float = 0.15,  # Penalizace za nedávný výběr (i nothing)
        engagement_bonus: float = 0.15,  # Bonus za vysoký engagement
        low_engagement_penalty: float = 0.20,  # Penalizace za nízký engagement
        anti_starvation_chance: float = 0.08,  # 8% šance pro low-engagement NPC
        anti_starvation_threshold: float = 0.25,  # Pod jaký engagement se aktivuje
    ):
        self.pressure_bonus = pressure_bonus
        self.stimulus_bonus = stimulus_bonus
        self.cooldown_penalty = cooldown_penalty
        self.low_energy_penalty = low_energy_penalty
        self.just_acted_penalty = just_acted_penalty
        self.just_selected_penalty = just_selected_penalty
        self.engagement_bonus = engagement_bonus
        self.low_engagement_penalty = low_engagement_penalty
        self.anti_starvation_chance = anti_starvation_chance
        self.anti_starvation_threshold = anti_starvation_threshold

    def score_npc(
        self,
        state: NPCBehaviorState,
        world_event: WorldEvent,
        npc_data: Dict,
        anti_rep_penalty: float = 0.0,
        current_turn: int = 0,
    ) -> NPCScore:
        """
        Vypočítá skóre pro jedno NPC.

        Args:
            state: Stav chování NPC
            world_event: Aktuální světová událost
            npc_data: Data NPC z postavy.json (pro povahu)
            anti_rep_penalty: Penalizace za opakování (0-1)
            current_turn: Aktuální číslo tahu

        Returns:
            NPCScore s celkovým skóre a rozpadem
        """
        breakdown = {}

        # Základní skóre = speak_drive * energy
        base = state.speak_drive * state.energy
        breakdown["base"] = base

        # Bonus za PRESSURE na toto NPC
        pressure = 0.0
        if world_event.event_type == WorldEventType.PRESSURE:
            if world_event.pressure_target == state.npc_id:
                pressure = self.pressure_bonus * world_event.intensity
        breakdown["pressure"] = pressure

        # Bonus za STIMULUS (všichni mohou reagovat)
        stimulus = 0.0
        if world_event.event_type == WorldEventType.STIMULUS:
            stimulus = self.stimulus_bonus * world_event.intensity
            # Bonus podle mluvnosti
            mluvnost = npc_data.get("povaha", {}).get("mluvnost", 0.5)
            stimulus *= mluvnost
        breakdown["stimulus"] = stimulus

        # Penalizace za cooldown
        cooldown = 0.0
        if state.cooldown_turns > 0:
            cooldown = -self.cooldown_penalty * state.cooldown_turns
        breakdown["cooldown"] = cooldown

        # Penalizace za nízkou energii
        energy_pen = 0.0
        if state.energy < 0.3:
            energy_pen = -self.low_energy_penalty * (0.3 - state.energy)
        breakdown["energy_penalty"] = energy_pen

        # Penalizace za opakování
        anti_rep = -anti_rep_penalty * 0.3
        breakdown["anti_rep"] = anti_rep

        # Penalizace za právě provedenou akci (v tomto nebo minulém tahu)
        # Aby se NPC nestřídalo samo se sebou
        just_acted = 0.0
        if state.last_acted_turn >= 0:
            turns_since_acted = current_turn - state.last_acted_turn
            if turns_since_acted == 0:
                # Právě udělal akci tento tah - vysoká penalizace
                just_acted = -self.just_acted_penalty
            elif turns_since_acted == 1:
                # Udělal akci minulý tah - mírná penalizace
                just_acted = -self.just_acted_penalty * 0.5
        breakdown["just_acted"] = just_acted

        # Penalizace za nedávný výběr pro AI (i když vrátil nothing)
        # Řeší "díru" kdy NPC vrátí nothing a je vybráno znovu
        just_selected = 0.0
        if state.last_selected_turn >= 0:
            turns_since_selected = current_turn - state.last_selected_turn
            if turns_since_selected == 0:
                # Právě byl vybrán tento tah
                just_selected = -self.just_selected_penalty
            elif turns_since_selected == 1:
                # Byl vybrán minulý tah
                just_selected = -self.just_selected_penalty * 0.5
        breakdown["just_selected"] = just_selected

        # Engagement bonus/penalizace
        # NPC s nízkým engagement má menší šanci být vybráno
        # (aby se neplýtvalo AI callem na někoho kdo bude gate-ován)
        engagement_mod = 0.0
        if state.engagement_drive >= 0.5:
            # Vysoký engagement = bonus
            engagement_mod = self.engagement_bonus * (state.engagement_drive - 0.5) * 2
        elif state.engagement_drive < 0.25:
            # Nízký engagement = penalizace
            engagement_mod = -self.low_engagement_penalty * (0.25 - state.engagement_drive) * 4
        breakdown["engagement"] = engagement_mod

        # Anti-starvation: low-engagement NPC občas dostane bonus šanci
        # Aby úplně nezmizelo ze scény
        # Bonus škálovaný podle engagement: čím víc "hladoví", tím větší bonus
        anti_starvation = 0.0
        if state.engagement_drive < self.anti_starvation_threshold:
            if random.random() < self.anti_starvation_chance:
                # Škálovaný bonus: 0.20 při engagement=0.25, až 0.25 při engagement=0
                hunger_factor = (self.anti_starvation_threshold - state.engagement_drive) / self.anti_starvation_threshold
                anti_starvation = 0.20 + 0.05 * hunger_factor  # 0.20-0.25
                breakdown["anti_starvation_triggered"] = True
        breakdown["anti_starvation"] = anti_starvation

        # Celkové skóre
        total = max(0.0, base + pressure + stimulus + cooldown + energy_pen + anti_rep + just_acted + just_selected + engagement_mod + anti_starvation)
        breakdown["total"] = total

        return NPCScore(
            npc_id=state.npc_id,
            score=total,
            breakdown=breakdown,
        )

    def select_top_k(
        self,
        states: Dict[str, NPCBehaviorState],
        world_event: WorldEvent,
        npc_data_map: Dict[str, Dict],
        anti_rep_penalties: Dict[str, float],
        k: int = 1,
        current_turn: int = 0,
    ) -> List[NPCScore]:
        """
        Vybere TOP K NPC s nejvyšším skóre.

        Args:
            states: Slovník stavů NPC (id -> state)
            world_event: Aktuální světová událost
            npc_data_map: Slovník dat NPC (id -> data z postavy.json)
            anti_rep_penalties: Penalizace za opakování pro každé NPC
            k: Kolik NPC vybrat
            current_turn: Aktuální číslo tahu

        Returns:
            Seznam TOP K NPCScore, seřazený od nejvyššího
        """
        scores = []
        for npc_id, state in states.items():
            if not state.can_speak():
                # NPC nemůže mluvit - přeskoč
                continue

            npc_data = npc_data_map.get(npc_id, {})
            anti_rep = anti_rep_penalties.get(npc_id, 0.0)

            score = self.score_npc(state, world_event, npc_data, anti_rep, current_turn)
            scores.append(score)

        # Seřaď podle skóre sestupně
        scores.sort(key=lambda s: s.score, reverse=True)

        # Vrať TOP K
        return scores[:k]

    def should_anyone_speak(
        self,
        top_scores: List[NPCScore],
        min_score_threshold: float = 0.15,
    ) -> bool:
        """
        Rozhodne jestli má někdo mluvit na základě skóre.

        Args:
            top_scores: TOP K skóre z select_top_k
            min_score_threshold: Minimální skóre pro mluvení

        Returns:
            True pokud má alespoň jeden NPC dostatečné skóre
        """
        if not top_scores:
            return False
        return top_scores[0].score >= min_score_threshold
