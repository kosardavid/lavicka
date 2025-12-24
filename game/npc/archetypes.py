"""
archetypes.py - Definice NPC archetypů
=======================================

Obsahuje předdefinované typy postav které mohou přijít na lavičku.
Každý archetyp definuje osobnost, vzhled a chování.

Postavy se načítají z game/data/postavy.json pro snadnou editaci.

Rozšířená data (social, values, bench, hobbies, fears, secrets):
----------------------------------------------------------------
Tyto položky umožňují realistické omezení hloubky rozhovorů.
NPC nesmí mluvit hlouběji než dovoluje vztah + osobnost.
Fallback defaulty zajišťují zpětnou kompatibilitu starých archetypů.
"""

import json
import os
from typing import Optional

# Cesta k datům
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
POSTAVY_FILE = os.path.join(DATA_DIR, "postavy.json")

# === FALLBACK DEFAULTY ===
# Používají se pokud archetyp nemá definované rozšířené položky.
# Zajišťuje zpětnou kompatibilitu starých archetypů.

DEFAULT_SOCIAL = {
    "openness": 0.5,       # střední ochota sdílet osobní věci
    "emotion_talk": 0.5,   # střední schopnost mluvit o emocích
    "privacy": 0.5,        # střední ochrana soukromí
}

DEFAULT_VALUES = {
    "values_frame": "humanist",  # výchozí hodnotový rámec
}

DEFAULT_BENCH = {
    "motive": "resting",      # výchozí důvod pobytu na lavičce
    "motive_share_level": 1,  # od jaké hloubky může říct důvod
}

# Prázdné seznamy - NPC bez hobbies/fears/secrets prostě nic nesdílí
DEFAULT_HOBBIES = []
DEFAULT_FEARS = []
DEFAULT_SECRETS = []

# Seznam všech možných emocí
EMOTIONS = [
    "calm",       # klidný
    "bored",      # znuděný
    "curious",    # zvědavý
    "content",    # spokojený
    "tense",      # napjatý
    "irritated",  # podrážděný
    "anxious",    # úzkostný
    "withdrawn",  # uzavřený
    "engaged",    # zaujatý
    "amused",     # pobavený
    "melancholic", # melancholický
    "restless",   # neklidný
]


def _apply_defaults(arch: dict) -> dict:
    """
    Aplikuje fallback defaulty na archetyp.

    Zajišťuje že i staré archetypy bez rozšířených položek
    budou mít všechna potřebná data pro depth systém.
    """
    # Social - kopíruj default a přepiš hodnotami z archetypu
    if "social" not in arch:
        arch["social"] = DEFAULT_SOCIAL.copy()
    else:
        merged = DEFAULT_SOCIAL.copy()
        merged.update(arch["social"])
        arch["social"] = merged

    # Values
    if "values" not in arch:
        arch["values"] = DEFAULT_VALUES.copy()
    else:
        merged = DEFAULT_VALUES.copy()
        merged.update(arch["values"])
        arch["values"] = merged

    # Bench
    if "bench" not in arch:
        arch["bench"] = DEFAULT_BENCH.copy()
    else:
        merged = DEFAULT_BENCH.copy()
        merged.update(arch["bench"])
        arch["bench"] = merged

    # Seznamy - ponech prázdné pokud nejsou definované
    if "hobbies" not in arch:
        arch["hobbies"] = DEFAULT_HOBBIES.copy()
    if "fears" not in arch:
        arch["fears"] = DEFAULT_FEARS.copy()
    if "secrets" not in arch:
        arch["secrets"] = DEFAULT_SECRETS.copy()

    return arch


def _nacti_postavy() -> list:
    """Načte postavy z JSON souboru a aplikuje fallback defaulty."""
    if os.path.exists(POSTAVY_FILE):
        try:
            with open(POSTAVY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Převod dict na list a tuple pro color
                postavy = []
                for arch in data.values():
                    arch = arch.copy()
                    if isinstance(arch.get("color"), list):
                        arch["color"] = tuple(arch["color"])
                    # Aplikuj fallback defaulty pro rozšířená data
                    arch = _apply_defaults(arch)
                    postavy.append(arch)
                return postavy
        except Exception as e:
            print(f"Chyba při načítání postav: {e}")

    # Fallback - prázdný seznam
    return []


# Definice archetypů postav (načtené z JSON)
ARCHETYPY = _nacti_postavy()


def get_archetype_by_id(archetype_id: str) -> Optional[dict]:
    """
    Najde archetyp podle ID.

    Args:
        archetype_id: ID archetypu (např. "babicka_vlasta")

    Returns:
        Slovník s archetypem nebo None
    """
    for arch in ARCHETYPY:
        if arch["id"] == archetype_id:
            return arch.copy()
    return None


def get_archetype_by_role(role: str) -> Optional[dict]:
    """
    Najde archetyp podle role (jména).

    Args:
        role: Jméno postavy (např. "Babička Vlasta")

    Returns:
        Slovník s archetypem nebo None
    """
    for arch in ARCHETYPY:
        if arch["role"] == role:
            return arch.copy()
    return None


def get_available_archetypes(exclude_ids: list = None) -> list:
    """
    Vrátí seznam dostupných archetypů (kromě vyloučených).

    Args:
        exclude_ids: Seznam ID které vynechat

    Returns:
        Seznam archetypů
    """
    exclude_ids = exclude_ids or []
    return [
        arch.copy()
        for arch in ARCHETYPY
        if arch["id"] not in exclude_ids
    ]
