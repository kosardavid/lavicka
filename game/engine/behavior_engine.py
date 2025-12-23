"""
BehaviorEngine - hlavní orchestrátor nového systému chování NPC.

Director generuje jen WORLD EVENT (STIMULUS/PRESSURE/SILENCE), ne repliky.
NPC rozhodují sami na základě speak_drive, stay_drive, cooldown, energy.
TOP K NPC jdou do AI, ostatní čekají nebo dělají scripted akce.
"""

import re
import time
import random
from typing import Optional, List, Dict, Any, Callable

from .types import (
    WorldEvent,
    WorldEventType,
    NPCBehaviorState,
    ResponseType,
    NPCResponse,
    AssistedOption,
    SceneContext,
    IntentLogEntry,
)
from .world_event import WorldEventGenerator, detect_question_target
from .scorer import SpeakScorer, NPCScore
from .anti_repetition import AntiRepetitionTracker
from .drive_update import DriveUpdater, detect_addressing, detect_question_to_npc


# Globální DEV_INTENT_LOG pro debugging
DEV_INTENT_LOG: List[IntentLogEntry] = []


def _log(action: str, details: Dict = None) -> None:
    """Přidá záznam do DEV_INTENT_LOG."""
    entry = IntentLogEntry(
        timestamp=time.time(),
        action=action,
        details=details or {},
    )
    DEV_INTENT_LOG.append(entry)

    # Udržuj max 100 záznamů
    if len(DEV_INTENT_LOG) > 100:
        DEV_INTENT_LOG.pop(0)


# Možnosti pro ASSISTED mód - měkké impulsy, ne příkazy
ASSISTED_OPTIONS: List[AssistedOption] = [
    AssistedOption(
        label="Nové téma",
        instruction="Napadá tě něco, co bys mohl/a zmínit - možná něco co vidíš, slyšíš, nebo o čem přemýšlíš. Ale klidně můžeš i mlčet.",
    ),
    AssistedOption(
        label="Osobní otázka",
        instruction="Možná by ses mohl/a na něco zeptat - ale jen pokud tě to opravdu zajímá. Nemusíš.",
    ),
    AssistedOption(
        label="Myšlenka",
        instruction="Přemýšlíš o něčem, co by stálo za zmínku. Nebo možná jen pozoruješ okolí.",
    ),
]


class BehaviorEngine:
    """
    Hlavní orchestrátor nového systému chování.

    Koordinuje:
    - WorldEventGenerator pro události
    - SpeakScorer pro výběr TOP K NPC
    - AntiRepetitionTracker proti opakování
    - Stavy NPCBehaviorState
    """

    def __init__(
        self,
        top_k: int = 1,
        cooldown_after_speech: int = 1,
        energy_cost_speech: float = 0.15,
        energy_regen_turn: float = 0.05,
        min_score_to_speak: float = 0.15,
    ):
        self.top_k = top_k
        self.cooldown_after_speech = cooldown_after_speech
        self.energy_cost_speech = energy_cost_speech
        self.energy_regen_turn = energy_regen_turn
        self.min_score_to_speak = min_score_to_speak

        # Komponenty
        self.event_generator = WorldEventGenerator()
        self.scorer = SpeakScorer()
        self.anti_rep = AntiRepetitionTracker()
        self.drive_updater = DriveUpdater()

        # Stav scény
        self._npc_states: Dict[str, NPCBehaviorState] = {}
        self._npc_data_map: Dict[str, Dict] = {}
        self._scene_context: Optional[SceneContext] = None
        self._last_speaker_id: Optional[str] = None
        self._last_response_text: str = ""
        self._assisted_active: bool = False

        # Historie všech odpovědí pro správné trackování
        self._history: List[Dict[str, Any]] = []

        # Max po sobě jdoucí repliky od stejného NPC
        self.max_consecutive_speaker = 2
        self._consecutive_speaker_count = 0

    # === HELPERS ===

    def _get_last_text_from_history(self) -> str:
        """Vrátí text poslední odpovědi z historie."""
        if not self._history:
            return ""
        return self._history[-1].get("text", "")

    def _get_last_speaker_from_history(self) -> Optional[str]:
        """Vrátí ID posledního mluvčího z historie."""
        if not self._history:
            return None
        return self._history[-1].get("npc_id")

    def _normalize_text(self, text: str) -> str:
        """Normalizuje text pro porovnání (lowercase, bez extra mezer, bez koncové interpunkce)."""
        if not text:
            return ""
        # Lowercase, odstranění přebytečných mezer
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)
        # Odeber koncovou interpunkci (., !, ?, ..., ", ', –, —, ), ] atd.)
        # Opakovaně dokud se mění (pro "text...")
        prev = None
        while prev != normalized:
            prev = normalized
            normalized = re.sub(r'[,.;:!?…"\'–—\)\]]+$', '', normalized)
        return normalized.strip()

    def _append_to_history(self, npc_id: str, response_type: str, text: str) -> None:
        """Přidá odpověď do historie."""
        self._history.append({
            "npc_id": npc_id,
            "type": response_type,
            "text": text,
            "turn": self._scene_context.turn_number if self._scene_context else 0,
        })
        # Udržuj max 20 položek
        if len(self._history) > 20:
            self._history.pop(0)

    def _get_last_speech_by_npc(self, npc_id: str) -> Optional[str]:
        """Vrátí text poslední SPEECH odpovědi od konkrétního NPC."""
        for entry in reversed(self._history):
            if entry.get("npc_id") == npc_id and entry.get("type") == "speech":
                return entry.get("text", "")
        return None

    # === LIFECYCLE ===

    def is_active(self) -> bool:
        """Je engine aktivní (probíhá scéna)?"""
        return self._scene_context is not None

    def start_scene(self, npc_a: Dict, npc_b: Dict) -> None:
        """
        Inicializuje novou scénu.

        Args:
            npc_a: Data prvního NPC z postavy.json
            npc_b: Data druhého NPC z postavy.json
        """
        _log("START_SCENE", {
            "npc_a": npc_a.get("id"),
            "npc_b": npc_b.get("id"),
        })

        # Inicializuj stavy
        self._npc_states = {}
        self._npc_data_map = {}

        for npc in [npc_a, npc_b]:
            npc_id = npc.get("id")
            povaha = npc.get("povaha", {})

            # Speak drive závisí na mluvnosti
            mluvnost = povaha.get("mluvnost", 0.5)
            speak_drive = 0.2 + mluvnost * 0.4  # 0.2 - 0.6

            self._npc_states[npc_id] = NPCBehaviorState(
                npc_id=npc_id,
                speak_drive=speak_drive,
                stay_drive=0.7,
                cooldown_turns=0,
                energy=1.0,
            )
            self._npc_data_map[npc_id] = npc

        # Inicializuj kontext scény
        self._scene_context = SceneContext()
        self._last_speaker_id = None
        self._last_response_text = ""
        self._assisted_active = False
        self._history = []
        self._consecutive_speaker_count = 0

        # Vyčisti anti-repetition
        self.anti_rep.clear()

    def end_scene(self) -> None:
        """Ukončí aktuální scénu."""
        _log("END_SCENE", {
            "total_turns": self._scene_context.turn_number if self._scene_context else 0,
            "total_speeches": self._scene_context.total_speeches if self._scene_context else 0,
        })

        self._npc_states.clear()
        self._npc_data_map.clear()
        self._scene_context = None
        self._last_speaker_id = None
        self._last_response_text = ""
        self._assisted_active = False
        self._history = []
        self._consecutive_speaker_count = 0

    # === MAIN PROCESSING ===

    def process_turn(
        self,
        ai_call_fn: Callable[[str, WorldEvent, str], Optional[NPCResponse]],
        forced_event: Optional[str] = None,
    ) -> Optional[NPCResponse]:
        """
        Zpracuje jeden tah.

        Args:
            ai_call_fn: Funkce pro volání AI
                        (npc_id, world_event, extra_instruction) -> NPCResponse
            forced_event: Vynucená událost od uživatele

        Returns:
            NPCResponse nebo None (ticho)
        """
        if not self.is_active():
            return None

        # 1. Update stavů na začátku tahu
        for state in self._npc_states.values():
            state.on_turn_start(self.energy_regen_turn)

        # 2. Generuj WorldEvent
        # OPRAVA: Používej text z historie, ne cache
        last_text = self._get_last_text_from_history()
        last_speaker = self._get_last_speaker_from_history()

        last_was_question = "?" in last_text
        question_target = None
        if last_was_question and last_speaker:
            question_target = detect_question_target(
                last_text,
                last_speaker,
                list(self._npc_states.keys()),
            )

        world_event = self.event_generator.generate(
            self._scene_context,
            forced_event=forced_event,
            last_response_was_question=last_was_question,
            question_target_id=question_target,
        )

        _log("WORLD_EVENT", {
            "type": world_event.event_type.value,
            "description": world_event.description,
            "intensity": world_event.intensity,
            "pressure_target": world_event.pressure_target,
        })

        # 3. Získej penalizace za opakování
        anti_rep_penalties = self.anti_rep.get_all_penalties(
            list(self._npc_states.keys())
        )

        # 3.5 Update drives pro všechna NPC
        for npc_id, state in self._npc_states.items():
            npc_data = self._npc_data_map.get(npc_id, {})
            was_addressed = False
            was_asked_question = False

            # OPRAVA: Používej last_text z historie
            # Guard: last_speaker může být None (po NOTHING response)
            if last_text and last_speaker and last_speaker != npc_id:
                npc_name = npc_data.get("jmeno", "")
                npc_titul = npc_data.get("titul", "")

                was_addressed = detect_addressing(
                    last_text,
                    npc_name,
                    npc_titul,
                )
                was_asked_question = detect_question_to_npc(
                    last_text,
                    npc_name,
                    npc_titul,
                    total_npcs_in_scene=len(self._npc_states),
                )

            # Debug log pro question targeting
            if was_asked_question:
                _log("QUESTION_TARGET_DETECTED", {
                    "npc_id": npc_id,
                    "total_npcs": len(self._npc_states),
                    "was_addressed": was_addressed,
                })

            self.drive_updater.update_drives(
                state=state,
                npc_data=npc_data,
                world_event=world_event,
                scene_context=self._scene_context,
                anti_rep_penalty=anti_rep_penalties.get(npc_id, 0.0),
                was_addressed=was_addressed,
                was_asked_question=was_asked_question,
            )

        # 4. Skóruj NPC a vyber TOP K
        top_scores = self.scorer.select_top_k(
            self._npc_states,
            world_event,
            self._npc_data_map,
            anti_rep_penalties,
            k=self.top_k,
            current_turn=self._scene_context.turn_number,
        )

        # Loguj všechny skóre
        for npc_id, state in self._npc_states.items():
            score_obj = next((s for s in top_scores if s.npc_id == npc_id), None)
            _log("NPC_SCORE", {
                "npc_id": npc_id,
                "speak_drive": state.speak_drive,
                "engagement_drive": state.engagement_drive,
                "energy": state.energy,
                "cooldown": state.cooldown_turns,
                "score": score_obj.score if score_obj else 0,
                "breakdown": score_obj.breakdown if score_obj else {},
                "selected": score_obj is not None,
            })

        # 5. Kontrola jestli má někdo mluvit
        # OPRAVA: result se nastaví v různých větvích, on_turn_end() se volá JEN JEDNOU na konci
        result = None

        if not self.scorer.should_anyone_speak(top_scores, self.min_score_to_speak):
            # Nikdo nemá dostatečné skóre - ticho
            self._scene_context.on_silence()

            # Kontrola ASSISTED módu
            if self._scene_context.is_dying():
                self._assisted_active = True
                _log("ASSISTED_MODE_TRIGGERED", {
                    "consecutive_silence": self._scene_context.consecutive_silence,
                    "scene_energy": self._scene_context.scene_energy,
                })
            # result zůstává None
        else:
            # 6. Volej AI pro TOP K NPC
            for score in top_scores:
                npc_id = score.npc_id
                state = self._npc_states.get(npc_id)

                # Zaznamenej výběr (i když vrátí nothing)
                if state:
                    state.on_selected(self._scene_context.turn_number)

                # === PERMISSION GATE ===
                # Pokud NPC nemá "sociální povolení" mluvit, přeskoč AI call
                if state and state.engagement_drive < 0.25 and state.speak_drive < 0.65:
                    _log("PERMISSION_DENIED", {
                        "npc_id": npc_id,
                        "engagement_drive": state.engagement_drive,
                        "speak_drive": state.speak_drive,
                    })

                    # Místo AI call vrátíme NOTHING nebo ACTION/THOUGHT
                    if state.speak_drive > 0.45:
                        generic_actions = [
                            "Pozoruje okolí.",
                            "Zamyšleně se dívá na moře.",
                            "Pousměje se.",
                        ]
                        response = NPCResponse(
                            npc_id=npc_id,
                            response_type=ResponseType.ACTION,
                            text=random.choice(generic_actions),
                        )
                    else:
                        response = NPCResponse(
                            npc_id=npc_id,
                            response_type=ResponseType.NOTHING,
                        )

                    result = self._process_response(response, world_event)
                    break  # Konec smyčky, jdeme na společný on_turn_end()

                # === MAX CONSECUTIVE SPEAKER CHECK ===
                # Pokud tento NPC už mluvil 2x za sebou, přeskoč na ACTION
                if self._last_speaker_id == npc_id and self._consecutive_speaker_count >= self.max_consecutive_speaker:
                    _log("MAX_CONSECUTIVE_SPEAKER", {
                        "npc_id": npc_id,
                        "consecutive_count": self._consecutive_speaker_count,
                        "max_allowed": self.max_consecutive_speaker,
                    })

                    generic_actions = [
                        "Chvíli mlčí a pozoruje okolí.",
                        "Zamyšleně se dívá na moře.",
                        "Nechává prostor druhému.",
                    ]
                    response = NPCResponse(
                        npc_id=npc_id,
                        response_type=ResponseType.ACTION,
                        text=random.choice(generic_actions),
                    )
                    result = self._process_response(response, world_event)
                    break  # Konec smyčky, jdeme na společný on_turn_end()

                # Extra instrukce
                extra_instruction = ""
                if self._assisted_active:
                    option = random.choice(ASSISTED_OPTIONS)
                    extra_instruction = option.instruction
                    _log("ASSISTED_INSTRUCTION", {
                        "npc_id": npc_id,
                        "instruction": extra_instruction,
                    })

                _log("AI_CALL", {
                    "npc_id": npc_id,
                    "score": score.score,
                    "engagement_drive": state.engagement_drive if state else 0,
                    "permission_denied": False,
                })

                # Volej AI
                response = ai_call_fn(npc_id, world_event, extra_instruction)

                if response:
                    _log("AI_RESPONSE", {
                        "npc_id": npc_id,
                        "type": response.response_type.value,
                        "text_preview": response.text[:50] if response.text else "",
                    })

                    result = self._process_response(response, world_event)
                    break  # Konec smyčky, jdeme na společný on_turn_end()

            # Pokud smyčka proběhla bez výsledku -> ticho
            if result is None:
                self._scene_context.on_silence()

        # === JEDINÉ MÍSTO kde se volá on_turn_end() ===
        self._scene_context.on_turn_end()
        return result

    def _process_response(
        self,
        response: NPCResponse,
        world_event: WorldEvent,
    ) -> NPCResponse:
        """Zpracuje odpověď od AI a aktualizuje stavy."""
        npc_id = response.npc_id
        state = self._npc_states.get(npc_id)

        if response.is_speech():
            # === HARD ANTI-DUPLICATION CHECK ===
            # Pokud NPC vygeneruje identický text jako jeho poslední speech -> reject
            last_speech_by_npc = self._get_last_speech_by_npc(npc_id)
            if last_speech_by_npc:
                normalized_new = self._normalize_text(response.text)
                normalized_old = self._normalize_text(last_speech_by_npc)
                if normalized_new == normalized_old:
                    _log("HARD_DUPLICATE_REJECT", {
                        "npc_id": npc_id,
                        "text_preview": response.text[:50] if response.text else "",
                        "normalized": normalized_new[:50] if normalized_new else "",
                        "action": "downgrade_to_action",
                    })
                    # Reject -> vrať ACTION místo NOTHING (aby něco dělal)
                    generic_actions = [
                        "Podívá se na moře.",
                        "Zamyšleně přikývne.",
                        "Pozoruje okolí.",
                    ]
                    response = NPCResponse(
                        npc_id=npc_id,
                        response_type=ResponseType.ACTION,
                        text=random.choice(generic_actions)
                    )
                    # Přidej do historie a vrať
                    self._append_to_history(npc_id, "action", response.text)
                    self._scene_context.on_action()
                    if state:
                        state.on_acted(self._scene_context.turn_number)
                    return response

            # Post-check anti-repetition (PŘED záznamem, aby se nepenalizoval sám sebou)
            rejection_action = self.anti_rep.get_rejection_action(npc_id, response.text)

            # OPRAVA: record_speech() se volá AŽ KDYŽ je finální typ speech (dole)
            # Při downgrade/reject se nevolá - protože speech se neřekla

            if rejection_action == "reject":
                # Úplné odmítnutí - změň na nothing
                _log("ANTI_REP_REJECT", {"npc_id": npc_id, "action": "reject"})
                response = NPCResponse(npc_id=npc_id, response_type=ResponseType.NOTHING)
                # npc_id=None aby last_speaker nebyl mlčící NPC
                self._append_to_history(None, "nothing", "")
                self._scene_context.on_nothing()
                # on_turn_end() se volá v process_turn(), ne tady
                if state:
                    self.drive_updater.on_after_speech(state, was_successful=False)
                return response

            elif rejection_action == "downgrade_to_thought":
                # Downgrade na myšlenku
                _log("ANTI_REP_DOWNGRADE", {"npc_id": npc_id, "action": "thought"})
                response = NPCResponse(
                    npc_id=npc_id,
                    response_type=ResponseType.THOUGHT,
                    text=response.text
                )
                # Pokračuj zpracováním jako thought

            elif rejection_action == "downgrade_to_action":
                # Downgrade na akci - generuj obecnou akci
                _log("ANTI_REP_DOWNGRADE", {"npc_id": npc_id, "action": "action"})
                generic_actions = [
                    "Podívá se na moře.",
                    "Zamyšleně přikývne.",
                    "Pozoruje okolí.",
                    "Pousměje se.",
                ]
                response = NPCResponse(
                    npc_id=npc_id,
                    response_type=ResponseType.ACTION,
                    text=random.choice(generic_actions)
                )
                # Pokračuj zpracováním jako action

        # Zpracuj podle finálního typu
        if response.is_speech():
            # Aktualizuj stav NPC
            if state:
                state.on_spoke(
                    self._scene_context.turn_number,
                    self.energy_cost_speech,
                )
                state.cooldown_turns = self.cooldown_after_speech
                self.drive_updater.on_after_speech(state, was_successful=True)

            # Aktualizuj kontext scény
            self._scene_context.on_speech()
            self._assisted_active = False  # Reset assisted modu

            # OPRAVA: record_speech() se volá AŽ TADY - když speech prošla
            self.anti_rep.record_speech(npc_id, response.text)

            # Přidej do historie
            self._append_to_history(npc_id, "speech", response.text)

            # Update consecutive speaker count
            if self._last_speaker_id == npc_id:
                self._consecutive_speaker_count += 1
            else:
                self._consecutive_speaker_count = 1

            # Ulož pro další tah (zachováno pro kompatibilitu)
            self._last_speaker_id = npc_id
            self._last_response_text = response.text

        elif response.response_type == ResponseType.THOUGHT:
            # Myšlenka - menší aktivita
            self._append_to_history(npc_id, "thought", response.text)
            self._scene_context.on_thought()
            if state:
                state.on_acted(self._scene_context.turn_number)
            # OPRAVA: THOUGHT není speech -> resetuj consecutive counter
            self._last_speaker_id = None
            self._consecutive_speaker_count = 0

        elif response.response_type == ResponseType.ACTION:
            # Akce - střední aktivita
            self._append_to_history(npc_id, "action", response.text)
            self._scene_context.on_action()
            if state:
                state.on_acted(self._scene_context.turn_number)
            # OPRAVA: ACTION není speech -> resetuj consecutive counter
            self._last_speaker_id = None
            self._consecutive_speaker_count = 0

        elif response.response_type == ResponseType.NOTHING:
            # Úplná nečinnost - NPC nic nedělá, NENÍ to akce
            # DŮLEŽITÉ: npc_id=None aby last_speaker nebyl mlčící NPC
            self._append_to_history(None, "nothing", "")
            self._scene_context.on_nothing()
            _log("NOTHING_RESPONSE", {"original_npc_id": npc_id})
            # OPRAVA: NOTHING není speech -> resetuj consecutive counter
            self._last_speaker_id = None
            self._consecutive_speaker_count = 0

        elif response.is_leaving():
            # Goodbye - NPC chce odejít (speech + odchod)
            if state:
                state.stay_drive = 0.0
            self._scene_context.on_speech()
            self.anti_rep.record_speech(npc_id, response.text)
            self._append_to_history(npc_id, "goodbye", response.text)

            # Update consecutive speaker count
            if self._last_speaker_id == npc_id:
                self._consecutive_speaker_count += 1
            else:
                self._consecutive_speaker_count = 1

            self._last_speaker_id = npc_id
            self._last_response_text = response.text

        # on_turn_end() se volá v process_turn(), ne tady
        return response

    # === QUERIES ===

    def get_npc_state(self, npc_id: str) -> Optional[NPCBehaviorState]:
        """Vrátí stav NPC."""
        return self._npc_states.get(npc_id)

    def get_scene_context(self) -> Optional[SceneContext]:
        """Vrátí kontext scény."""
        return self._scene_context

    def is_assisted_mode(self) -> bool:
        """Je aktivní ASSISTED mód?"""
        return self._assisted_active

    def get_assisted_options(self) -> List[AssistedOption]:
        """Vrátí možnosti pro ASSISTED mód."""
        return ASSISTED_OPTIONS

    def should_npc_leave(self, npc_id: str) -> bool:
        """Má NPC odejít?"""
        state = self._npc_states.get(npc_id)
        if not state:
            return False
        return state.stay_drive <= 0.1

    def get_debug_info(self) -> str:
        """Vrátí debug info o stavu enginu."""
        if not self.is_active():
            return "Engine: neaktivní"

        ctx = self._scene_context
        states_info = []
        for npc_id, state in self._npc_states.items():
            states_info.append(
                f"{npc_id}: drive={state.speak_drive:.2f}, "
                f"energy={state.energy:.2f}, cd={state.cooldown_turns}"
            )

        return (
            f"Turn: {ctx.turn_number}, "
            f"Speeches: {ctx.total_speeches}, "
            f"Energy: {ctx.scene_energy:.2f}, "
            f"Silence: {ctx.consecutive_silence} | "
            + " | ".join(states_info)
        )


def clear_intent_log() -> None:
    """Vymaže DEV_INTENT_LOG."""
    DEV_INTENT_LOG.clear()


def print_intent_log() -> None:
    """Vypíše DEV_INTENT_LOG do konzole."""
    print("\n=== DEV_INTENT_LOG ===")
    for entry in DEV_INTENT_LOG[-20:]:
        print(entry)
    print("======================\n")
