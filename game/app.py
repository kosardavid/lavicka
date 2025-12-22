"""
app.py - Hlavní aplikační třída
================================

Spojuje všechny moduly dohromady a řídí herní logiku.
"""

import time
import random
import threading
from datetime import datetime
from typing import Optional

import pygame

from .settings import (
    RES_X, RES_Y,
    AUTO_TAH_INTERVAL,
    BUBLINA_MIN_TRVANI, BUBLINA_RYCHLOST,
    PRAVDEPODOBNOST_PRICHODU, PRAVDEPODOBNOST_ODCHODU_SAM,
    PRAVDEPODOBNOST_ODCHODU_PO_ROZHOVORU, MIN_REPLIK_PRO_ODCHOD,
    TICHO_SAM,
)
from .npc import ARCHETYPY, get_available_archetypes
from .rules import RelationshipManager, EventManager, Director
from .ai import AIClient
from .memory import get_pamet, vytvor_kontext_z_pameti
from .ui import Renderer, ChatPanel, InputBox
from .utils import safe_print


class LavickaApp:
    """
    Hlavní aplikace hry Lavička nad mořem.

    Koordinuje:
    - Pygame vykreslování
    - NPC příchody/odchody
    - AI rozhovory
    - Události prostředí
    - Paměť NPC
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((RES_X, RES_Y))
        pygame.display.set_caption("Lavička nad mořem")

        # UI komponenty
        self.renderer = Renderer(self.screen)
        self.chat_panel = ChatPanel(self.screen)
        self.input_box = InputBox(self.screen)

        # Herní stav
        self.sedadla = [None, None]  # [levé, pravé]
        self.historie = []
        self.aktualni_bublina = None

        # Manažery
        self.relationships = RelationshipManager()
        self.events = EventManager()
        self.director = Director()
        self.ai_client = AIClient()
        self.pamet = get_pamet()

        # Řízení
        self.ai_mysli = False
        self.automat = True
        self._lock = threading.Lock()

    # === HERNÍ LOGIKA ===

    def tah(self):
        """
        Provede jeden herní tah.

        Volá se automaticky nebo manuálně (mezerník).
        """
        with self._lock:
            if self.ai_mysli or self.input_box.is_active():
                return
            self.ai_mysli = True

        try:
            self._zpracuj_prichody()
            self._zpracuj_odchody()

            obsazeno = [i for i, x in enumerate(self.sedadla) if x]
            if not obsazeno:
                return

            # Událost prostředí
            forced_event = self.events.get_pending_event()

            # Automatická událost od Directora
            if not forced_event and self.director.is_active():
                auto_event = self.director.suggest_event()
                if auto_event:
                    self.add_environment_event(auto_event)
                    forced_event = auto_event

            # Director plánuje reakce na event
            event_reactions = {}
            if forced_event and self.director.is_active():
                npcs_on_scene = [s for s in self.sedadla if s]
                event_reactions = self.director.plan_event_reaction(forced_event, npcs_on_scene)

            # Rozhodnutí o tichu
            if not self._should_speak(obsazeno, forced_event):
                return

            # Výběr mluvčího
            idx = self._vyber_mluvciho(obsazeno, forced_event)
            npc = self.sedadla[idx]
            soused = self.sedadla[1 - idx] if len(obsazeno) == 2 else None

            # Získání instrukce od Directora pro event
            director_instruction = None
            if event_reactions and npc:
                npc_reaction = event_reactions.get(npc.get('id'))
                if npc_reaction and npc_reaction.get('should_react'):
                    director_instruction = npc_reaction.get('instruction')

            # Získání odpovědi od AI
            resp = self._get_ai_response(npc, soused, forced_event, director_instruction)

            if forced_event:
                self.events.clear_pending()

            if not resp:
                return

            # Zpracování odpovědi
            self._zpracuj_odpoved(npc, soused, resp, idx)

        finally:
            with self._lock:
                self.ai_mysli = False

    def _zpracuj_prichody(self):
        """Zpracuje náhodné příchody NPC."""
        for i in range(2):
            if self.sedadla[i] is None:
                if random.random() < PRAVDEPODOBNOST_PRICHODU:
                    self._pridej_npc(i)

    def _zpracuj_odchody(self):
        """Zpracuje odchody NPC."""
        for i in range(2):
            npc = self.sedadla[i]
            if not npc:
                continue

            je_sam = sum(1 for s in self.sedadla if s) == 1

            if npc.get('chce_odejit', False):
                self._odejdi_npc(i)
            elif je_sam and random.random() < PRAVDEPODOBNOST_ODCHODU_SAM:
                self._odejdi_npc(i)

    def _should_speak(self, obsazeno: list, forced_event) -> bool:
        """Rozhodne jestli někdo promluví."""
        if forced_event:
            return True

        if len(obsazeno) == 1:
            return random.random() >= TICHO_SAM

        # Šance na ticho podle vztahu
        npc_a = self.sedadla[0]
        npc_b = self.sedadla[1]
        silence_chance = self.relationships.get_silence_chance(npc_a, npc_b)
        return random.random() >= silence_chance

    def _vyber_mluvciho(self, obsazeno: list, forced_event) -> int:
        """Vybere kdo bude mluvit."""
        if len(obsazeno) == 1:
            return obsazeno[0]

        # Střídání - kdo naposledy mluvil?
        posledni_mluvci = None
        for h in reversed(self.historie[-16:]):
            if h.get('type') == 'speech':
                posledni_mluvci = h.get('role')
                break

        if posledni_mluvci == self.sedadla[0]['role']:
            return 1
        elif posledni_mluvci == self.sedadla[1]['role']:
            return 0
        else:
            return random.choice([0, 1])

    def _get_ai_response(self, npc, soused, forced_event, director_instruction=None) -> Optional[dict]:
        """Získá odpověď od AI."""
        # Příprava kontextu
        relationship_rules = {}
        memory_context = ""

        if soused:
            vztah = self.relationships.get(npc, soused)
            relationship_rules = {
                "pacing": self.relationships.get_pacing_rule(npc, soused),
                "addressing": self.relationships.get_addressing_rule(npc, soused),
                "familiarity": vztah.familiarity,
                "sympathy": vztah.sympathy,
                "tykani": vztah.tykani,
            }
            memory_context = vytvor_kontext_z_pameti(
                self.pamet, npc['id'], soused['id'], vztah.familiarity
            )

        event_context = self.events.get_recent_events_text()

        # Pokud máme director_instruction pro event, použijeme ji jako intent
        if director_instruction:
            npc["intent"] = director_instruction
        # Intent od Directora (pokud není event instrukce)
        elif self.director.is_active():
            director_intent = self.director.get_intent(npc)
            if director_intent:
                npc["intent"] = director_intent

        # Kontrola jestli má odejít (Director nebo fallback)
        is_goodbye = False
        if self.director.is_active() and self.director.should_end():
            is_goodbye = True
            npc["intent"] = "Chce zdvořile ukončit rozhovor."
        else:
            # Fallback - staré chování
            speech_count = sum(1 for h in self.historie[-50:] if h.get("type") == "speech")
            is_goodbye = (
                speech_count >= MIN_REPLIK_PRO_ODCHOD
                and random.random() < PRAVDEPODOBNOST_ODCHODU_PO_ROZHOVORU
            )
            if is_goodbye and soused:
                npc["intent"] = "Chce zdvořile ukončit rozhovor."

        return self.ai_client.get_response(
            npc=npc,
            soused=soused,
            historie=self.historie,
            relationship_rules=relationship_rules,
            memory_context=memory_context,
            event_context=event_context,
            forced_event=forced_event,
            is_goodbye=is_goodbye,
        )

    def _zpracuj_odpoved(self, npc, soused, resp: dict, idx: int):
        """Zpracuje odpověď od AI."""
        text = resp.get('text', '').strip()
        typ = resp.get('type', 'speech')

        if not text:
            return

        # Informovat Directora
        if self.director.is_active():
            self.director.observe(resp)
            safe_print(f"[DIRECTOR] {self.director.get_debug_info()}")

        if typ == 'goodbye':
            npc['chce_odejit'] = True
            typ = 'speech'

        # Přidat do historie
        self._add_to_history(npc['role'], text, typ)

        # Aktualizovat vztah
        if soused and typ == 'speech':
            self.relationships.update_after_speech(npc, soused, text)

            # Synchronizovat tykání z RelationshipManager do paměti
            vztah_session = self.relationships.get(npc, soused)
            self.pamet.aktualizuj_vztah(
                npc['id'], soused['id'],
                sympatie_zmena=0.02,
                tykani=vztah_session.tykani if vztah_session.tykani else None
            )

        # Zobrazit bublinu
        trvani = max(BUBLINA_MIN_TRVANI, len(text) / BUBLINA_RYCHLOST)
        self.aktualni_bublina = {
            'text': text,
            'is_thought': typ == 'thought',
            'idx': idx,
            'konec': time.time() + trvani,
        }

    # === NPC MANAGEMENT ===

    def _pridej_npc(self, seat_index: int):
        """Přidá nové NPC na sedadlo."""
        # Zjisti kdo už sedí
        exclude = [s['id'] for s in self.sedadla if s]
        dostupne = get_available_archetypes(exclude)

        if not dostupne:
            return

        archetype = random.choice(dostupne)
        npc = archetype.copy()
        npc['chce_odejit'] = False
        npc['intent'] = "Chce si na chvíli odpočinout a užít moře."

        # Inicializace emocí
        npc['baseline_mood'] = random.randint(-10, 10)
        npc['emotion'] = random.choice(["calm", "bored", "content", "curious"])
        npc['emotion_intensity'] = random.randint(15, 45)

        with self._lock:
            self.sedadla[seat_index] = npc
        self._add_to_history('SYSTEM', f"Přišel: {npc['role']}", 'sys')
        safe_print(f"[NPC] Přišel: {npc['role']}")

        # Spustit scénu pokud jsou dva NPC
        soused = self.sedadla[1 - seat_index]
        if soused:
            vztah = self.relationships.get(npc, soused)
            self.director.start_scene(npc, soused, vztah)
            safe_print(f"[DIRECTOR] {self.director.get_debug_info()}")

    def _odejdi_npc(self, seat_index: int):
        """Odebere NPC ze sedadla."""
        npc = self.sedadla[seat_index]
        if not npc:
            return

        # Uložit paměť před odchodem
        soused = self.sedadla[1 - seat_index]
        if soused:
            self._uloz_pamet(npc, soused)

        self._add_to_history('SYSTEM', f"Odešel: {npc['role']}", 'sys')
        with self._lock:
            self.sedadla[seat_index] = None
        safe_print(f"[NPC] Odešel: {npc['role']}")

        # Ukončit scénu
        if self.director.is_active():
            self.director.end_scene()
            safe_print("[DIRECTOR] Scéna ukončena")

    def _uloz_pamet(self, npc, soused):
        """Uloží paměť po rozhovoru."""
        safe_print(f"\n=== UKLÁDÁM PAMĚŤ: {npc['role']} o {soused['role']} ===")

        shrnuti = self.ai_client.get_summary(npc, soused, self.historie)

        if shrnuti:
            self.pamet.uloz_osobu(
                npc_id=npc['id'],
                osoba_id=soused['id'],
                popis=shrnuti.get('popis', soused['popis']),
                jmeno=shrnuti.get('jmeno'),
                dojem=shrnuti.get('dojem', ''),
                temata=shrnuti.get('temata', []),
                fakta=shrnuti.get('fakta', []),
                emoce_intenzita=shrnuti.get('emoce_intenzita', 0.5)
            )
            safe_print(f"Paměť uložena: {shrnuti}")
        else:
            self.pamet.uloz_osobu(
                npc_id=npc['id'],
                osoba_id=soused['id'],
                popis=soused['popis'],
                dojem="normální rozhovor"
            )
            safe_print("Paměť uložena (základní)")

    # === UDÁLOSTI ===

    def add_environment_event(self, text: str):
        """Přidá událost prostředí."""
        if not text:
            return

        self._add_to_history('PROSTŘEDÍ', text, 'sys')
        self.events.add_event(text, self.sedadla)
        safe_print(f"[ENV] Událost: {text}")

    # === HISTORIE ===

    def _add_to_history(self, role: str, text: str, msg_type: str):
        """Přidá zprávu do historie."""
        self.historie.append({
            'role': role,
            'text': text,
            'type': msg_type,
            'ts': time.time(),
        })

        # Auto-scroll na konec
        self.chat_panel.scroll_to_bottom()

    # === VYKRESLOVÁNÍ ===

    def vykresli(self):
        """Vykreslí celou scénu."""
        # Pozadí a lavička
        self.renderer.draw_background()
        self.renderer.draw_bench()

        # NPC - thread-safe kopie
        with self._lock:
            sedadla_snapshot = list(self.sedadla)

        for i, npc in enumerate(sedadla_snapshot):
            if npc:
                self.renderer.draw_npc(npc, i)

        # Bublina
        if self.aktualni_bublina:
            b = self.aktualni_bublina
            if time.time() < b.get('konec', 0):
                self.renderer.draw_bubble(
                    b['text'],
                    b['idx'],
                    b.get('is_thought', False)
                )
            else:
                self.aktualni_bublina = None

        # Chat panel
        self.chat_panel.draw(self.historie)

        # Input box
        self.input_box.draw()

        # Status bar
        cas = datetime.now().strftime("%H:%M:%S")
        stav = "AI PŘEMÝŠLÍ..." if self.ai_mysli else "Čekám..."
        status = f"{cas} | {stav} | [A] Auto | [MEZERNÍK] Tah | [E] Event"
        self.renderer.draw_status_bar(status)

        pygame.display.flip()

    # === VEŘEJNÉ METODY ===

    def is_busy(self) -> bool:
        """Vrací True pokud AI přemýšlí nebo je aktivní input."""
        return self.ai_mysli or self.input_box.is_active() or self.aktualni_bublina is not None

    def toggle_automat(self):
        """Přepne automatický režim."""
        self.automat = not self.automat
        safe_print(f"Automat: {'ZAP' if self.automat else 'VYP'}")

    def aplikuj_decay(self):
        """Aplikuje zapomínání na paměť."""
        self.pamet.aplikuj_decay(1)
        safe_print("Decay aplikován (1 den)")

    def vypis_pamet(self):
        """Vypíše paměť všech NPC."""
        safe_print("\n=== PAMĚŤ VŠECH NPC ===")
        for arch in ARCHETYPY:
            lidi = self.pamet.seznam_lidi(arch['id'])
            if lidi:
                safe_print(f"\n{arch['role']} zná:")
                for osoba in lidi:
                    jmeno = osoba.get('jmeno') or osoba['popis']
                    dojem = osoba.get('dojem', '?')
                    sila = osoba.get('sila', 0)
                    safe_print(f"  - {jmeno}: {dojem} (síla: {sila:.2f})")

    def reset_pamet(self):
        """Vymaže veškerou paměť."""
        self.pamet.vymaz_vse()
        safe_print("Paměť vymazána!")
