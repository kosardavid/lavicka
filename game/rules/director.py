"""
director.py - Režisér scény
============================

Director sleduje průběh rozhovoru a jemně ho koriguje.
Je to adaptivní pozorovatel a našeptávač, ne tvrdý plánovač.
"""

import random
import time
from typing import Optional
from dataclasses import dataclass, field

from ..ai.logger import get_ai_logger


@dataclass
class SceneState:
    """Aktuální stav scény."""
    phase: str = "intro"  # intro, developing, peak, closing
    energy: float = 0.5   # 0.0-1.0, jak živá je scéna
    speech_count: int = 0
    estimated_length: int = 10  # odhad celkové délky
    trajectory: str = "casual"  # casual, deep, conflict, quiet
    start_time: float = field(default_factory=time.time)
    last_speech_time: float = field(default_factory=time.time)


# Intenty podle fáze - varianty pro muže (m) a ženy (f)
PHASE_INTENTS = {
    "intro": [
        {"m": "Právě přišel, oťukává situaci.", "f": "Právě přišla, oťukává situaci."},
        {"m": "Zkoumá, kdo vedle něj sedí.", "f": "Zkoumá, kdo vedle ní sedí."},
        {"m": "Váhá, jestli začít rozhovor.", "f": "Váhá, jestli začít rozhovor."},
    ],
    "developing": [
        {"m": "", "f": ""},  # volný průběh
        {"m": "Rozhovor plyne přirozeně.", "f": "Rozhovor plyne přirozeně."},
    ],
    "peak": [
        {"m": "Rozhovor je v plném proudu.", "f": "Rozhovor je v plném proudu."},
        {"m": "Téma ho opravdu zajímá.", "f": "Téma ji opravdu zajímá."},
    ],
    "peak_conflict": [
        {"m": "Cítí napětí v rozhovoru.", "f": "Cítí napětí v rozhovoru."},
        {"m": "Nesouhlasí s názorem druhého.", "f": "Nesouhlasí s názorem druhého."},
    ],
    "closing": [
        {"m": "Pomalu směřuje k rozloučení.", "f": "Pomalu směřuje k rozloučení."},
        {"m": "Cítí, že je čas jít.", "f": "Cítí, že je čas jít."},
        {"m": "Chce rozhovor hezky uzavřít.", "f": "Chce rozhovor hezky uzavřít."},
    ],
}

# Klíčová slova pro detekci sentimentu
CONFLICT_KEYWORDS = [
    "ne,", "ne.", "nesouhlasím", "to není pravda", "ale", "jenže",
    "nemyslím", "nesmysl", "blbost", "hloupost",
]
POSITIVE_KEYWORDS = [
    "ano", "souhlasím", "máte pravdu", "zajímavé", "hezké",
    "příjemné", "rád", "ráda", "děkuji",
]
CLOSING_KEYWORDS = [
    "musím jít", "bylo mi", "na shledanou", "sbohem", "nashle",
    "půjdu", "měl bych jít", "měla bych jít", "čeká mě",
]

# Trajektorie - délky
TRAJECTORY_LENGTHS = {
    "casual": (8, 16),      # běžný rozhovor - delší
    "deep": (14, 25),       # hluboký rozhovor - ještě delší
    "conflict": (6, 12),    # konflikt - kratší ale ne moc
    "quiet": (5, 10),       # tichý - pár replik, ale ne 3
}

def _compute_compatibility(npc_a: dict, npc_b: dict) -> tuple:
    """
    Dynamicky vypočítá kompatibilitu dvou NPC z jejich povah.

    Returns:
        (šance_casual, šance_deep, šance_conflict, šance_quiet)
    """
    # Získej povahy (default hodnoty pokud chybí)
    povaha_a = npc_a.get("povaha", {})
    povaha_b = npc_b.get("povaha", {})

    konfl_a = povaha_a.get("konfliktnost", 0.2)
    konfl_b = povaha_b.get("konfliktnost", 0.2)
    hloub_a = povaha_a.get("hloubavost", 0.3)
    hloub_b = povaha_b.get("hloubavost", 0.3)
    mluv_a = povaha_a.get("mluvnost", 0.5)
    mluv_b = povaha_b.get("mluvnost", 0.5)

    # Průměry
    konfliktnost = (konfl_a + konfl_b) / 2
    hloubavost = (hloub_a + hloub_b) / 2
    mluvnost = (mluv_a + mluv_b) / 2

    # Výpočet šancí
    # Konflikt: vyšší konfliktnost obou = vyšší šance
    conflict = konfliktnost * 0.8

    # Deep: vyšší hloubavost = hlubší rozhovory
    deep = hloubavost * 0.6

    # Quiet: nízká mluvnost = tišší rozhovor
    quiet = (1 - mluvnost) * 0.5

    # Casual: zbytek
    casual = max(0.2, 1.0 - conflict - deep - quiet)

    # Normalizace
    total = casual + deep + conflict + quiet
    return (casual / total, deep / total, conflict / total, quiet / total)

# Automatické události
AUTO_EVENTS_IMPULSE = [
    "Kolem proletěl racek.",
    "Od moře zafoukal vítr.",
    "Někde v dálce zahoukal parník.",
    "Na lavičku dopadl list.",
    "Přeběhla kolem kočka.",
]

AUTO_EVENTS_DRAMATIC = [
    "Začalo poprchávat.",
    "Kolem proběhlo dítě s míčem.",
    "Silný poryv větru.",
    "Slunce vyšlo zpoza mraků.",
]


class Director:
    """
    Režisér scény - sleduje a jemně koriguje průběh rozhovoru.
    """

    def __init__(self):
        self.state: Optional[SceneState] = None
        self._npc_a_id: Optional[str] = None
        self._npc_b_id: Optional[str] = None
        self._logger = get_ai_logger()

    def start_scene(self, npc_a: dict, npc_b: dict, relationship=None) -> None:
        """
        Inicializuje novou scénu.

        Args:
            npc_a: První NPC
            npc_b: Druhé NPC
            relationship: Vztah mezi nimi (volitelné)
        """
        self._npc_a_id = npc_a.get("id")
        self._npc_b_id = npc_b.get("id")

        # Určení trajektorie podle kompatibility
        trajectory = self._determine_trajectory(npc_a, npc_b, relationship)

        # Délka podle trajektorie
        min_len, max_len = TRAJECTORY_LENGTHS.get(trajectory, (6, 12))
        estimated_length = random.randint(min_len, max_len)

        self.state = SceneState(
            phase="intro",
            energy=0.5,
            speech_count=0,
            estimated_length=estimated_length,
            trajectory=trajectory,
        )

        self._logger.log_director(
            "START_SCENE",
            f"{npc_a.get('role')} + {npc_b.get('role')} | "
            f"trajectory={trajectory} | est_length={estimated_length}"
        )

    def _determine_trajectory(
        self, npc_a: dict, npc_b: dict, relationship=None
    ) -> str:
        """Určí trajektorii scény podle povah NPC a vztahu."""
        # Dynamicky vypočítej kompatibilitu z povah NPC
        weights = _compute_compatibility(npc_a, npc_b)

        # Úprava podle vztahu
        if relationship:
            familiarity = getattr(relationship, 'familiarity', 0)
            sympathy = getattr(relationship, 'sympathy', 0)

            # Známí mají tendenci k deep
            if familiarity > 1.0:
                weights = (
                    weights[0] * 0.7,
                    weights[1] * 1.5,
                    weights[2],
                    weights[3],
                )
            # Nízká sympatie = víc konfliktu
            if sympathy < -0.3:
                weights = (
                    weights[0] * 0.5,
                    weights[1] * 0.5,
                    weights[2] * 2.0,
                    weights[3],
                )

        # Normalizace
        total = sum(weights)
        weights = tuple(w / total for w in weights)

        # Náhodný výběr
        r = random.random()
        cumulative = 0
        trajectories = ["casual", "deep", "conflict", "quiet"]

        for i, w in enumerate(weights):
            cumulative += w
            if r <= cumulative:
                return trajectories[i]

        return "casual"

    def observe(self, response: dict) -> None:
        """
        Sleduje odpověď AI a aktualizuje stav.

        Args:
            response: Odpověď od AI {"text": ..., "type": ...}
        """
        if not self.state:
            return

        text = response.get("text", "").lower()
        resp_type = response.get("type", "speech")

        if resp_type in ("speech", "thought"):
            self.state.speech_count += 1
            self.state.last_speech_time = time.time()

        # Detekce sentimentu
        conflict_score = sum(1 for kw in CONFLICT_KEYWORDS if kw in text)
        positive_score = sum(1 for kw in POSITIVE_KEYWORDS if kw in text)
        closing_detected = any(kw in text for kw in CLOSING_KEYWORDS)

        # Úprava energie
        if conflict_score > positive_score:
            self.state.energy = min(1.0, self.state.energy + 0.1)
            if self.state.trajectory != "conflict" and conflict_score >= 2:
                # Přepnutí na konfliktní trajektorii
                self.state.trajectory = "conflict"
                self.state.estimated_length = min(
                    self.state.estimated_length,
                    self.state.speech_count + 4
                )
        elif positive_score > conflict_score:
            self.state.energy = max(0.0, self.state.energy - 0.05)

        # Detekce closing
        old_phase = self.state.phase
        if closing_detected:
            self.state.phase = "closing"

        # Aktualizace fáze
        self._update_phase()

        # Loguj změny
        self._logger.log_director(
            "OBSERVE",
            f"phase={self.state.phase} | {self.state.speech_count}/{self.state.estimated_length} | "
            f"energy={self.state.energy:.2f} | trajectory={self.state.trajectory}"
        )

    def _update_phase(self) -> None:
        """Přepočítá fázi podle speech_count."""
        if not self.state:
            return

        progress = self.state.speech_count / max(1, self.state.estimated_length)

        if self.state.phase == "closing":
            return  # Už jsme v closing, zůstáváme

        if progress < 0.2:
            self.state.phase = "intro"
        elif progress < 0.7:
            self.state.phase = "developing"
        elif progress < 0.9:
            self.state.phase = "peak"
        else:
            self.state.phase = "closing"

    def get_intent(self, npc: dict) -> str:
        """
        Vrátí hint pro AI prompt.

        Args:
            npc: NPC pro které generujeme intent

        Returns:
            Text intentu
        """
        if not self.state:
            return ""

        phase = self.state.phase

        # Speciální intent pro konflikt
        if phase == "peak" and self.state.trajectory == "conflict":
            intents = PHASE_INTENTS.get("peak_conflict", [{"m": "", "f": ""}])
        else:
            intents = PHASE_INTENTS.get(phase, [{"m": "", "f": ""}])

        intent_dict = random.choice(intents)

        # Vyber variantu podle rodu NPC
        rod = npc.get("rod", "muž")
        if rod == "žena":
            intent = intent_dict.get("f", intent_dict.get("m", ""))
        else:
            intent = intent_dict.get("m", "")

        if intent:
            self._logger.log_director("INTENT", f"{npc.get('role')}: \"{intent}\"")
        return intent

    def should_end(self) -> bool:
        """
        Rozhodne jestli má scéna skončit.

        Returns:
            True pokud je čas na odchod
        """
        if not self.state:
            return False

        reason = None

        # Už v closing fázi a proběhlo dost replik
        if self.state.phase == "closing":
            if self.state.speech_count >= self.state.estimated_length - 1:
                reason = "closing phase complete"

        # Přesáhli odhad
        if self.state.speech_count >= self.state.estimated_length + 2:
            reason = "exceeded estimated length"

        # Konflikt - rychlejší konec
        if self.state.trajectory == "conflict":
            if self.state.speech_count >= self.state.estimated_length:
                reason = "conflict trajectory complete"

        if reason:
            self._logger.log_director("SHOULD_END", f"True - {reason}")
            return True

        return False

    def suggest_event(self) -> Optional[str]:
        """
        Navrhne automatickou událost.

        Returns:
            Text události nebo None
        """
        if not self.state:
            return None

        # Nízká šance
        if random.random() > 0.15:
            return None

        # Scéna "umírá" - dlouho nic nebylo
        time_since_last = time.time() - self.state.last_speech_time
        if time_since_last > 20 and self.state.energy < 0.3:
            event = random.choice(AUTO_EVENTS_IMPULSE)
            self._logger.log_director("SUGGEST_EVENT", f"impulse: \"{event}\"")
            return event

        # Blíží se peak - dramatičtější událost
        if self.state.phase == "peak" and random.random() < 0.3:
            event = random.choice(AUTO_EVENTS_DRAMATIC)
            self._logger.log_director("SUGGEST_EVENT", f"dramatic: \"{event}\"")
            return event

        return None

    def plan_event_reaction(self, event: str, npcs: list) -> dict:
        """
        Naplánuje reakce NPC na událost.

        Args:
            event: Text události
            npcs: Seznam NPC na scéně [npc_a, npc_b] nebo [npc] pokud je sám

        Returns:
            {
                "npc_id": {
                    "should_react": bool,
                    "reaction_type": "speech" | "thought" | "ignore",
                    "instruction": str  # konkrétní instrukce pro AI
                },
                ...
            }
        """
        if not npcs:
            return {}

        reactions = {}

        for npc in npcs:
            if not npc:
                continue

            npc_id = npc.get("id", "")
            role = npc.get("role", "")
            vibe = npc.get("vibe", "")

            # Rozhodnutí jestli reagovat
            should_react = True
            reaction_type = "speech"
            instruction = ""

            # Analýza události a NPC
            event_lower = event.lower()

            # Získej povahu NPC pro dynamickou reakci
            povaha = npc.get("povaha", {})
            konfliktnost = povaha.get("konfliktnost", 0.2)

            # Hrubost/konflikt - reaguje ten koho se to týká
            if "hrub" in event_lower or "nadáv" in event_lower or "křič" in event_lower:
                if npc_id in event_lower or role.lower() in event_lower:
                    # Toto NPC je agresorem
                    reaction_type = "speech"
                    instruction = f"Buď hrubý a nepříjemný. {event}"
                else:
                    # Reakce závisí na konfliktnosti
                    if konfliktnost > 0.4:
                        instruction = "Reaguj podrážděně nebo ironicky na hrubé chování."
                    elif konfliktnost < 0.2:
                        instruction = "Buď překvapený/á a trochu zraněný/á hrubostí."
                    else:
                        instruction = "Reaguj přirozeně na hrubé chování vedle tebe."

            # Pití alkoholu
            elif "pivo" in event_lower or "alkohol" in event_lower or "pít" in event_lower:
                if npc_id in event_lower or role.lower() in event_lower:
                    reaction_type = "speech"
                    instruction = f"Právě piješ. {event}"
                else:
                    should_react = random.random() < 0.5
                    instruction = "Všiml/a sis pití vedle sebe. Můžeš to komentovat."

            # Přírodní události (racek, vítr, etc.)
            elif any(w in event_lower for w in ["racek", "vítr", "list", "kočka", "pes"]):
                # Náhodně vybrat kdo reaguje
                if random.random() < 0.6:
                    reaction_type = random.choice(["speech", "thought"])
                    instruction = f"Všiml/a sis: {event}. Můžeš to krátce okomentovat."
                else:
                    should_react = False

            # Počasí
            elif any(w in event_lower for w in ["déšť", "prší", "slunce", "mrak"]):
                reaction_type = "speech"
                instruction = f"Reaguj na změnu počasí: {event}"

            # Obecná událost
            else:
                instruction = f"Reaguj přirozeně na: {event}"

            reactions[npc_id] = {
                "should_react": should_react,
                "reaction_type": reaction_type,
                "instruction": instruction
            }

        # Logování
        self._logger.log_director(
            "PLAN_EVENT",
            f"event=\"{event[:50]}...\" | reactions={len([r for r in reactions.values() if r['should_react']])}"
        )

        return reactions

    def end_scene(self) -> None:
        """Ukončí scénu, reset stavu."""
        if self.state:
            self._logger.log_director(
                "END_SCENE",
                f"final: {self.state.speech_count} speeches | "
                f"trajectory={self.state.trajectory} | phase={self.state.phase}"
            )
        self.state = None
        self._npc_a_id = None
        self._npc_b_id = None

    def is_active(self) -> bool:
        """Vrací True pokud běží scéna."""
        return self.state is not None

    def get_debug_info(self) -> str:
        """Vrátí debug info o stavu (pro výpis)."""
        if not self.state:
            return "Director: žádná scéna"

        return (
            f"Director: {self.state.phase} | "
            f"{self.state.trajectory} | "
            f"{self.state.speech_count}/{self.state.estimated_length} | "
            f"energy={self.state.energy:.2f}"
        )
