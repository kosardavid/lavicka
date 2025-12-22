"""
helpers.py - Pomocné funkce
============================

Obsahuje utility funkce používané napříč projektem.
"""

import sys
import re
import unicodedata


def safe_print(*args, **kwargs):
    """
    Bezpečný print, který nikdy nespadne kvůli kódování.

    Řeší problémy s Unicode na Windows konzoli.
    """
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    s = sep.join("" if a is None else str(a) for a in args) + end

    try:
        sys.stdout.write(s)
    except Exception:
        try:
            b = s.encode(sys.stdout.encoding or "utf-8", errors="backslashreplace")
            sys.stdout.buffer.write(b)
        except Exception:
            # Poslední záchrana - odeber nepovolené znaky
            sys.stdout.write(
                (s.encode("utf-8", errors="ignore")).decode("utf-8", errors="ignore")
            )

    try:
        sys.stdout.flush()
    except Exception:
        pass


def strip_non_latin(s: str) -> str:
    """
    Odebere znaky které nejsou latinkou nebo českou diakritikou.

    Používá se pro čištění AI odpovědí od cizích písem (cyrilice apod.).
    """
    allowed = re.compile(
        r"[A-Za-zÀ-ž0-9\s\.\,\!\?\:\;\-\(\)\'\"\%\&\+\=/\*#@\[\]_]",
        re.UNICODE
    )
    return "".join(ch for ch in s if allowed.match(ch))


def strip_accents(s: str) -> str:
    """
    Odebere diakritiku z textu.

    Užitečné pro porovnávání jmen (Adéla -> Adela).
    """
    return "".join(
        ch for ch in unicodedata.normalize("NFD", s)
        if unicodedata.category(ch) != "Mn"
    )


def pair_key(role_a: str, role_b: str) -> str:
    """
    Vytvoří unikátní klíč pro pár osob (seřazený).

    Používá se pro ukládání vztahů - nezáleží na pořadí.

    Příklad:
        pair_key("Petr", "Jana") == pair_key("Jana", "Petr")
    """
    a, b = sorted([role_a, role_b])
    return f"{a}__{b}"


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Omezí hodnotu do rozsahu."""
    return max(min_val, min(max_val, value))


def rod_instrukce(npc: dict) -> str:
    """
    Vrátí instrukce pro správný rod v češtině.

    Args:
        npc: Slovník s klíčem 'rod' ("muž" nebo "žena")

    Returns:
        Instrukce pro AI prompt
    """
    rod = npc.get("rod", "muž")
    if rod == "žena":
        return "Mluv v ženském rodě (např. byla jsem, udělala jsem)."
    return "Mluv v mužském rodě (např. byl jsem, udělal jsem)."


# Pokus o nastavení UTF-8 na Windows
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
except Exception:
    pass
