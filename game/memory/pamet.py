"""
pamet.py - Systém paměti pro NPC
=================================

Lidská paměť nefunguje jako nahrávka. Tento modul simuluje:
- Shrnutí místo doslovného textu
- Zapomínání časem (decay)
- Silnější paměť pro emocionální zážitky
- Rozpoznávání osob podle síly vzpomínky

Paměť se ukládá do JSON souboru pro persistenci mezi sezeními.
"""

import json
import os
from datetime import datetime
from typing import Optional, Dict, List

# Cesta k datům
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
PAMETI_FILE = os.path.join(DATA_DIR, "pameti.json")
VZTAHY_FILE = os.path.join(DATA_DIR, "vztahy.json")


class Pamet:
    """
    Správce paměti pro všechny NPC.

    Ukládá vzpomínky na osoby a vztahy mezi nimi.
    Podporuje zapomínání (decay) a rozpoznávání.
    """

    def __init__(self):
        self.npcs = self._nacti_npcs()
        self.vztahy = self._nacti_vztahy()

    def _nacti_npcs(self) -> Dict:
        """Načte NPC paměti z JSON souboru."""
        if os.path.exists(PAMETI_FILE):
            try:
                with open(PAMETI_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Chyba při načítání pamětí: {e}")
        return {}

    def _nacti_vztahy(self) -> Dict:
        """Načte vztahy z JSON souboru."""
        if os.path.exists(VZTAHY_FILE):
            try:
                with open(VZTAHY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Chyba při načítání vztahů: {e}")
        return {}

    def _uloz_npcs(self):
        """Uloží NPC paměti do JSON souboru."""
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(PAMETI_FILE, "w", encoding="utf-8") as f:
            json.dump(self.npcs, f, ensure_ascii=False, indent=2)

    def _uloz_vztahy(self):
        """Uloží vztahy do JSON souboru."""
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(VZTAHY_FILE, "w", encoding="utf-8") as f:
            json.dump(self.vztahy, f, ensure_ascii=False, indent=2)

    def _get_npc(self, npc_id: str) -> Dict:
        """Získá nebo vytvoří paměť pro NPC."""
        if npc_id not in self.npcs:
            self.npcs[npc_id] = {"lide": {}}
        return self.npcs[npc_id]

    def _pair_key(self, a: str, b: str) -> str:
        """Vytvoří klíč pro vztah (seřazený)."""
        return "__".join(sorted([a, b]))

    # === HLEDÁNÍ V PAMĚTI ===

    def hledej_osobu(self, npc_id: str, osoba_id: str) -> Dict:
        """
        Hledá osobu v paměti NPC.

        Args:
            npc_id: ID NPC které vzpomíná
            osoba_id: ID hledané osoby

        Returns:
            {
                "nalezeno": bool,
                "rozpoznani": "poznam_dobre" | "poznam" | "povedome" | "nejasne" | "neznam",
                "osoba": {...} nebo None
            }
        """
        npc = self._get_npc(npc_id)

        if osoba_id in npc["lide"]:
            osoba = npc["lide"][osoba_id]
            sila = osoba.get("sila", 0)

            if sila > 0.7:
                rozpoznani = "poznam_dobre"
            elif sila > 0.5:
                rozpoznani = "poznam"
            elif sila > 0.3:
                rozpoznani = "povedome"
            elif sila > 0.1:
                rozpoznani = "nejasne"
            else:
                rozpoznani = "neznam"

            return {
                "nalezeno": True,
                "rozpoznani": rozpoznani,
                "osoba": osoba
            }

        return {
            "nalezeno": False,
            "rozpoznani": "neznam",
            "osoba": None
        }

    # === UKLÁDÁNÍ VZPOMÍNKY ===

    def uloz_osobu(
        self,
        npc_id: str,
        osoba_id: str,
        popis: str,
        dojem: str,
        jmeno: Optional[str] = None,
        temata: Optional[List[str]] = None,
        fakta: Optional[List[str]] = None,
        emoce_intenzita: float = 0.5
    ) -> Dict:
        """
        Uloží nebo aktualizuje vzpomínku na osobu.

        Args:
            npc_id: ID NPC které si pamatuje
            osoba_id: ID osoby na kterou vzpomíná
            popis: Jak osoba vypadá
            dojem: Celkový dojem
            jmeno: Jméno (pokud ho zná)
            temata: O čem mluvili
            fakta: Co se dozvěděl
            emoce_intenzita: 0-1, jak silný byl zážitek

        Returns:
            {"success": True, "sila": float, "pocet_setkani": int}
        """
        npc = self._get_npc(npc_id)
        existing = npc["lide"].get(osoba_id, {})

        # Výpočet síly paměti
        stara_sila = existing.get("sila", 0)
        nova_sila = stara_sila + 0.3 if stara_sila > 0 else 0.5
        nova_sila = min(1.0, nova_sila * (1 + emoce_intenzita * 0.3))

        # Sloučení témat a faktů
        stara_temata = existing.get("temata", [])
        nova_temata = list(set(stara_temata + (temata or [])))

        stare_fakta = existing.get("fakta", [])
        nova_fakta = list(set(stare_fakta + (fakta or [])))

        # Uložení
        npc["lide"][osoba_id] = {
            "id": osoba_id,
            "popis": popis or existing.get("popis", ""),
            "jmeno": jmeno or existing.get("jmeno"),
            "dojem": dojem or existing.get("dojem", ""),
            "temata": nova_temata[-10:],  # Max 10 témat
            "fakta": nova_fakta[-10:],     # Max 10 faktů
            "sila": nova_sila,
            "pocet_setkani": existing.get("pocet_setkani", 0) + 1,
            "posledni_setkani": datetime.now().isoformat(),
            "prvni_setkani": existing.get("prvni_setkani", datetime.now().isoformat())
        }

        self._uloz_npcs()

        return {
            "success": True,
            "sila": nova_sila,
            "pocet_setkani": npc["lide"][osoba_id]["pocet_setkani"]
        }

    # === VZTAHY ===

    def get_vztah(self, osoba_a: str, osoba_b: str) -> Dict:
        """Získá vztah mezi dvěma osobami."""
        key = self._pair_key(osoba_a, osoba_b)

        if key in self.vztahy:
            return self.vztahy[key]

        # Výchozí vztah
        return {
            "faze": "cizinci",
            "tykani": False,
            "sympatie": 0.0,
            "pocet_setkani": 0,
            "historie": []
        }

    def aktualizuj_vztah(
        self,
        osoba_a: str,
        osoba_b: str,
        faze: Optional[str] = None,
        tykani: Optional[bool] = None,
        sympatie_zmena: float = 0.0,
        udalost: Optional[str] = None
    ) -> Dict:
        """
        Aktualizuje vztah mezi dvěma osobami.

        Args:
            osoba_a, osoba_b: ID osob
            faze: "cizinci" | "tvare" | "znami" | "pratele"
            tykani: Jestli si tykají
            sympatie_zmena: -1 až +1
            udalost: Co se stalo (pro historii)

        Returns:
            Aktualizovaný vztah
        """
        key = self._pair_key(osoba_a, osoba_b)
        existing = self.vztahy.get(key, {
            "faze": "cizinci",
            "tykani": False,
            "sympatie": 0.0,
            "pocet_setkani": 0,
            "historie": []
        })

        # Aktualizace
        if faze:
            existing["faze"] = faze
        if tykani is not None:
            existing["tykani"] = tykani

        existing["sympatie"] = max(-1.0, min(1.0, existing["sympatie"] + sympatie_zmena))
        existing["pocet_setkani"] = existing.get("pocet_setkani", 0) + 1

        if udalost:
            existing["historie"] = (existing.get("historie", []) + [udalost])[-10:]

        # Automatické povyšování faze podle počtu setkání a sympatií
        existing["faze"] = self._vypocti_fazi(existing)

        self.vztahy[key] = existing
        self._uloz_vztahy()

        return existing

    def _vypocti_fazi(self, vztah: Dict) -> str:
        """
        Vypočítá fázi vztahu podle kvality interakcí, ne počtu.

        Fáze závisí na:
        - sympatie (jak moc si rozumí)
        - tykání (formální posun)
        - historie (významné události)

        Fáze:
        - cizinci: sympatie < 0.15 (neznají se, nebo negativní)
        - tvare: sympatie >= 0.15 (poznali se, neutrální/pozitivní dojem)
        - znami: sympatie >= 0.4 (dobře si rozumí, pravidelně mluví)
        - pratele: sympatie >= 0.6 + tykání (blízký vztah)

        Returns:
            Nová fáze vztahu
        """
        sympatie = vztah.get("sympatie", 0)
        tykani = vztah.get("tykani", False)
        historie = vztah.get("historie", [])
        aktualni_faze = vztah.get("faze", "cizinci")

        # Pořadí fází
        faze_poradi = ["cizinci", "tvare", "znami", "pratele"]
        aktualni_index = faze_poradi.index(aktualni_faze) if aktualni_faze in faze_poradi else 0

        nova_faze = aktualni_faze

        # Bonus za významné události v historii
        historie_bonus = 0
        for udalost in historie:
            udalost_lower = udalost.lower() if udalost else ""
            # Pozitivní události
            if any(w in udalost_lower for w in ["pomohl", "zachránil", "sdílel", "důvěra", "příjemný"]):
                historie_bonus += 0.1
            # Negativní události
            if any(w in udalost_lower for w in ["konflikt", "hádka", "urážka", "zklamání"]):
                historie_bonus -= 0.1

        efektivni_sympatie = sympatie + historie_bonus

        # Pratele: vysoká sympatie + tykání (formální blízkost)
        if efektivni_sympatie >= 0.6 and tykani:
            nova_faze = "pratele"
        # Znami: slušná sympatie (rozumí si, rádi mluví)
        elif efektivni_sympatie >= 0.4:
            nova_faze = "znami"
        # Tvare: pozitivní první dojem (poznali se)
        elif efektivni_sympatie >= 0.15:
            nova_faze = "tvare"
        # Cizinci: nízká nebo negativní sympatie
        else:
            nova_faze = "cizinci"

        # Nikdy automaticky nesnižovat fázi (ale může klesnout při konfliktu)
        nova_index = faze_poradi.index(nova_faze) if nova_faze in faze_poradi else 0
        if nova_index < aktualni_index and historie_bonus >= 0:
            # Snížení jen pokud byla negativní událost
            nova_faze = aktualni_faze

        return nova_faze

    # === ZAPOMÍNÁNÍ ===

    def aplikuj_decay(self, dny: int = 1):
        """
        Aplikuje zapomínání na všechny vzpomínky.

        Args:
            dny: Kolik "dní" uplynulo
        """
        DECAY_RATE = 0.98  # Za den
        MIN_SILA = 0.05

        decay_factor = DECAY_RATE ** dny

        for npc_id in list(self.npcs.keys()):
            npc = self.npcs[npc_id]
            to_delete = []

            for osoba_id in list(npc["lide"].keys()):
                osoba = npc["lide"][osoba_id]
                osoba["sila"] = osoba.get("sila", 0.5) * decay_factor

                if osoba["sila"] < MIN_SILA:
                    to_delete.append(osoba_id)

            for osoba_id in to_delete:
                del npc["lide"][osoba_id]

        self._uloz_npcs()

    # === POMOCNÉ ===

    def seznam_lidi(self, npc_id: str) -> List[Dict]:
        """Vrátí seznam všech lidí které NPC zná."""
        npc = self._get_npc(npc_id)
        return list(npc["lide"].values())

    def vymaz_vse(self):
        """Vymaže všechny vzpomínky (pro testování)."""
        self.npcs = {}
        self.vztahy = {}
        self._uloz_npcs()
        self._uloz_vztahy()


# === HELPER FUNKCE ===

def vytvor_kontext_z_pameti(pamet: Pamet, npc_id: str, partner_id: str, familiarity: float = 0) -> str:
    """
    Vytvoří textový kontext pro AI prompt na základě paměti.

    Args:
        pamet: Instance paměti
        npc_id: ID NPC které vzpomíná
        partner_id: ID partnera v rozhovoru
        familiarity: Aktuální familiarity ze vztahu (pro probíhající rozhovor)

    Returns:
        Text pro přidání do system promptu
    """
    vzpominka = pamet.hledej_osobu(npc_id, partner_id)
    vztah = pamet.get_vztah(npc_id, partner_id)

    # Pokud nemáme vzpomínku z minula, ale familiarity > 0, znamená to
    # že právě probíhá rozhovor a už se trochu znají
    if not vzpominka["nalezeno"]:
        if familiarity >= 3:
            return "Právě se s tímto člověkem bavíte, postupně ho poznáváte."
        elif familiarity >= 1:
            return "Právě jste začali rozhovor s tímto člověkem."
        return "Tohoto člověka neznáš, vidíš ho poprvé."

    osoba = vzpominka["osoba"]
    rozpoznani = vzpominka["rozpoznani"]

    lines = []

    # Jak moc ho znám
    if rozpoznani == "poznam_dobre":
        lines.append("Tohoto člověka dobře znáš.")
    elif rozpoznani == "poznam":
        lines.append("Tohoto člověka znáš, už jste se párkrát viděli.")
    elif rozpoznani == "povedome":
        lines.append("Tento člověk ti je povědomý, asi jste se už potkali.")
    elif rozpoznani == "nejasne":
        lines.append("Něco ti na tom člověku připomíná někoho, ale nejsi si jistý/á.")

    # Jméno - zobrazit pouze pokud si tykají
    # Při vykání se jména nepoužívají (české kulturní norma)
    if osoba.get("jmeno"):
        tykani = vztah.get("tykani", False)
        if tykani:
            lines.append(f"Víš že se jmenuje {osoba['jmeno']}. Můžeš ho/ji oslovit jménem.")
        # Pokud si netykají, jméno vůbec nezmiňujeme - AI ho pak nebude používat

    # Dojem
    if osoba.get("dojem"):
        lines.append(f"Tvůj dojem: {osoba['dojem']}.")

    # Co o něm víš
    if osoba.get("fakta"):
        lines.append(f"Co o něm/ní víš: {', '.join(osoba['fakta'][:3])}.")

    # Témata
    if osoba.get("temata"):
        lines.append(f"Mluvili jste o: {', '.join(osoba['temata'][:3])}.")

    # Vztah
    if vztah["faze"] != "cizinci":
        lines.append(f"Váš vztah: {vztah['faze']}.")
    if vztah["tykani"]:
        lines.append("Tykáte si.")
    else:
        lines.append("Vykáte si.")

    # Počet setkání
    pocet = osoba.get("pocet_setkani", 0)
    if pocet > 1:
        lines.append(f"Potkali jste se už {pocet}x.")

    return "\n".join(lines)


# === SINGLETON ===
_pamet_instance = None


def get_pamet() -> Pamet:
    """Vrátí singleton instanci paměti."""
    global _pamet_instance
    if _pamet_instance is None:
        _pamet_instance = Pamet()
    return _pamet_instance
