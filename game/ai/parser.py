"""
parser.py - Parsování AI odpovědí
==================================

Robustní parser který zvládne různé formáty odpovědí
od různých LLM modelů (Qwen, Llama, atd.).
"""

import re
import json
from typing import Optional
from ..utils.helpers import strip_non_latin
from ..settings import BANNED_SUBSTRINGS


def _clean_text(s: str) -> str:
    """Vyčistí text od markdown a dalších artefaktů."""
    s = (s or "").strip()
    s = re.sub(r'```(?:json)?', '', s, flags=re.IGNORECASE).strip()
    s = s.replace('```', '').strip()
    return s


def _attempt_fix_json(s: str) -> str:
    """Pokusí se opravit běžné JSON chyby."""
    s = s.strip()
    # Chybějící uzavírací závorka
    if s.startswith("{") and not s.endswith("}"):
        s = s + "}"
    # Trailing comma
    s = re.sub(r',\s*}', '}', s)
    s = re.sub(r',\s*]', ']', s)
    return s


def _is_banned(text: str) -> bool:
    """Kontroluje jestli text obsahuje zakázané podřetězce."""
    t = text.lower()
    return any(x in t for x in BANNED_SUBSTRINGS)


def parse_response(raw_text: str) -> Optional[dict]:
    """
    Parsuje odpověď od AI modelu.

    Podporované formáty:
    - Validní JSON: {"type": "speech", "text": "..."}
    - Poškozený JSON s opravitelnými chybami
    - Čistý text (fallback)

    Args:
        raw_text: Surový text od AI

    Returns:
        {"type": "speech"|"thought"|"goodbye", "text": "..."} nebo None
    """
    if not raw_text:
        return None

    text = _clean_text(raw_text)
    if len(text) < 2:
        return None

    # 1. Pokus: JSON parse
    m = re.search(r'\{.*\}', text, flags=re.DOTALL)
    if m:
        candidate = m.group(0)
        # Opravy překlepů
        candidate = candidate.replace('"speach"', '"speech"')
        candidate = candidate.replace("'speach'", "'speech'")
        candidate = _attempt_fix_json(candidate)

        try:
            data = json.loads(candidate)
            if isinstance(data, dict) and "text" in data:
                out_text = str(data.get("text", "")).strip()
                out_type = str(data.get("type", "speech")).strip().lower()

                # Oprava překlepu
                if out_type == "speach":
                    out_type = "speech"

                out_text = strip_non_latin(out_text)

                if out_text and not _is_banned(out_text):
                    return {"type": out_type, "text": out_text}
        except Exception:
            pass

    # 2. Pokus: Regex pro type + text
    m2 = re.search(
        r'["\']type["\']\s*:\s*["\']([^"\']+)["\'].*?'
        r'["\']text["\']\s*:\s*["\']([^"\']+)["\']',
        text, flags=re.DOTALL
    )
    if m2:
        out_type = m2.group(1).strip().lower()
        out_text = strip_non_latin(m2.group(2).strip())

        if out_type == "speach":
            out_type = "speech"

        if out_text and not _is_banned(out_text):
            return {"type": out_type, "text": out_text}

    # 3. Pokus: Jen text pole
    m3 = re.search(r'["\']text["\']\s*:\s*["\']([^"\']+)["\']', text)
    if m3:
        out_text = strip_non_latin(m3.group(1).strip())
        out_type = "thought" if "thought" in text.lower() else "speech"

        if out_text and not _is_banned(out_text):
            return {"type": out_type, "text": out_text}

    # 4. Fallback: Čistý text
    if "{" not in text and "}" not in text and len(text) <= 220:
        if not _is_banned(text):
            # Odeber předpony jako "Řekne:", "Myšlenka:" atd.
            text2 = re.sub(
                r'^(Pozdraví|Řekne|Odpověď|Myšlenka)\s*:\s*',
                '', text, flags=re.IGNORECASE
            ).strip()
            text2 = strip_non_latin(text2)

            if text2 and not _is_banned(text2):
                # Odeber uvozovky kolem textu
                q = re.match(r'^[\'"](.+)[\'"]$', text2)
                if q:
                    text2 = q.group(1).strip()
                return {"type": "speech", "text": text2}

    return None


def parse_summary(raw_text: str) -> Optional[dict]:
    """
    Parsuje shrnutí rozhovoru od AI.

    Očekávaný formát:
    {
        "popis": "...",
        "jmeno": "..." nebo null,
        "dojem": "...",
        "temata": ["...", "..."],
        "fakta": ["...", "..."],
        "emoce_intenzita": 0.5
    }

    Args:
        raw_text: Surový text od AI

    Returns:
        Slovník se shrnutím nebo None
    """
    if not raw_text:
        return None

    text = _clean_text(raw_text)
    text = _attempt_fix_json(text)

    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except json.JSONDecodeError:
        # Fallback: extrakce jednotlivých polí
        result = {}

        popis = re.search(r'"popis"\s*:\s*"([^"]+)"', text)
        if popis:
            result['popis'] = popis.group(1)

        jmeno = re.search(r'"jmeno"\s*:\s*"([^"]+)"', text)
        if jmeno:
            result['jmeno'] = jmeno.group(1)

        dojem = re.search(r'"dojem"\s*:\s*"([^"]+)"', text)
        if dojem:
            result['dojem'] = dojem.group(1)

        if result:
            result.setdefault('temata', [])
            result.setdefault('fakta', [])
            result.setdefault('emoce_intenzita', 0.5)
            return result

    return None
