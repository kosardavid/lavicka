"""
archetypes.py - Definice NPC archetypů
=======================================

Obsahuje předdefinované typy postav které mohou přijít na lavičku.
Každý archetyp definuje osobnost, vzhled a chování.

Postavy se načítají z game/data/postavy.json pro snadnou editaci.
"""

import json
import os
from typing import Optional

# Cesta k datům
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
POSTAVY_FILE = os.path.join(DATA_DIR, "postavy.json")

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


def _nacti_postavy() -> list:
    """Načte postavy z JSON souboru."""
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
