"""
client.py - Klient pro komunikaci s AI
=======================================

Wrapper kolem OpenAI API pro lokální LLM.
"""

import traceback
from typing import Optional
from openai import OpenAI

from ..settings import (
    CLIENT_URL,
    API_KEY,
    MODEL_NAME,
    AI_TEMPERATURE,
    AI_MAX_TOKENS,
    AI_SUMMARY_MAX_TOKENS,
    DEBUG_AI,
    FORWARD_JUMP_TERMS,
    GOODBYE_PHRASES,
)
from ..utils.helpers import safe_print
from .parser import parse_response, parse_summary
from .prompts import PromptBuilder
from .logger import get_ai_logger

# Validní typy odpovědí (rozšířeno o action a nothing pro BehaviorEngine)
VALID_RESPONSE_TYPES = {"speech", "thought", "goodbye", "action", "nothing"}


class AIClient:
    """
    Klient pro komunikaci s lokálním LLM.

    Používá OpenAI API formát pro komunikaci s LM Studio
    nebo podobnými servery.
    """

    def __init__(self):
        self._client = OpenAI(base_url=CLIENT_URL, api_key=API_KEY)
        self._prompt_builder = PromptBuilder()
        self._logger = get_ai_logger()

    def get_response(
        self,
        npc: dict,
        soused: Optional[dict],
        historie: list,
        relationship_rules: dict,
        memory_context: str,
        event_context: str,
        forced_event: Optional[str] = None,
        is_goodbye: bool = False,
    ) -> Optional[dict]:
        """
        Získá odpověď od AI pro NPC.

        Args:
            npc: NPC které má odpovědět
            soused: Druhé NPC (nebo None)
            historie: Historie rozhovoru
            relationship_rules: Pravidla vztahu
            memory_context: Kontext z paměti
            event_context: Nedávné události
            forced_event: Událost na kterou musí reagovat
            is_goodbye: True pokud má NPC odejít

        Returns:
            {"type": "speech"|"thought"|"goodbye", "text": "..."} nebo None
        """
        # Najdi poslední repliku souseda
        posledni_replika = None
        if soused:
            for h in reversed(historie[-50:]):
                if h.get("type") == "speech" and h.get("role") == soused["role"]:
                    posledni_replika = (h.get("text", "") or "").strip()
                    break

        # Sestav roleplay log
        roleplay_log = self._prompt_builder.build_roleplay_log(
            npc, soused, historie, limit=8
        )

        # Sestav prompt
        if is_goodbye and soused:
            system_prompt, user_prompt = self._prompt_builder.build_goodbye_prompt(
                npc=npc,
                soused=soused,
                relationship_rules=relationship_rules,
                memory_context=memory_context,
            )
        else:
            system_prompt, user_prompt = self._prompt_builder.build_response_prompt(
                npc=npc,
                soused=soused,
                roleplay_log=roleplay_log,
                posledni_replika=posledni_replika,
                relationship_rules=relationship_rules,
                memory_context=memory_context,
                event_context=event_context,
                forced_event=forced_event,
            )

        # Loguj request
        request_type = "goodbye" if is_goodbye else "response"
        self._logger.log_request(npc['role'], request_type, system_prompt, user_prompt)

        # Volej AI
        try:
            if DEBUG_AI:
                safe_print(f"\n--- PROMPT ({npc['role']}) ---")
                preview = system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt
                safe_print(preview)

            response = self._client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
            )

            raw = response.choices[0].message.content
            safe_print(f"RAW ({npc['role']}): {raw}")

            # Parsuj odpověď
            data = parse_response(raw)
            if not data:
                self._logger.log_response(npc['role'], raw, None)
                return None

            text = (data.get("text", "") or "").strip()
            typ = (data.get("type", "speech") or "speech").strip().lower()

            # Validace
            if not text or len(text) > 220:
                self._logger.log_response(npc['role'], raw, None, "Text prázdný nebo moc dlouhý")
                return None

            # Kontrola forward jump (příliš rychlé návrhy schůzek)
            familiarity = relationship_rules.get("familiarity", 0)
            if soused and familiarity < 9 and typ == "speech":
                if self._looks_like_forward_jump(text):
                    self._logger.log_response(npc['role'], raw, None, "Forward jump rejected")
                    return None

            # Detekce rozloučení
            if self._looks_like_goodbye(text):
                typ = "goodbye"

            result = {"type": typ, "text": text}
            self._logger.log_response(npc['role'], raw, result)
            return result

        except Exception as e:
            self._logger.log_response(npc['role'], "", None, str(e))
            safe_print(f"Chyba LLM: {e}")
            safe_print(traceback.format_exc())
            return None

    def get_summary(
        self,
        npc: dict,
        soused: dict,
        historie: list,
    ) -> Optional[dict]:
        """
        Získá shrnutí rozhovoru pro uložení do paměti.

        Args:
            npc: NPC které si pamatuje
            soused: Druhé NPC
            historie: Historie rozhovoru

        Returns:
            Slovník se shrnutím nebo None
        """
        # Extrahuj repliky
        repliky = []
        for h in historie[-20:]:
            if h.get('type') == 'speech':
                if h.get('role') in [npc['role'], soused['role']]:
                    repliky.append(f"{h['role']}: {h['text']}")

        if len(repliky) < 2:
            return None

        rozhovor_text = "\n".join(repliky)
        prompt = self._prompt_builder.build_summary_prompt(
            npc_role=npc['role'],
            partner_popis=soused['popis'],
            rozhovor_text=rozhovor_text,
        )

        system_prompt = "Jsi pomocník. Odpovídej POUZE validním JSON. JAZYK: česky."
        self._logger.log_request(npc['role'], "summary", system_prompt, prompt)

        try:
            response = self._client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=AI_SUMMARY_MAX_TOKENS,
            )

            raw = response.choices[0].message.content
            safe_print(f"SHRNUTÍ ({npc['role']} o {soused['role']}): {raw}")

            result = parse_summary(raw)
            self._logger.log_response(npc['role'], raw, result)
            return result

        except Exception as e:
            self._logger.log_response(npc['role'], "", None, str(e))
            safe_print(f"Chyba při shrnutí: {e}")
            return None

    def get_engine_response(
        self,
        npc: dict,
        soused: Optional[dict],
        historie: list,
        relationship_rules: dict,
        memory_context: str,
        world_event_desc: str,
        extra_instruction: str = "",
    ) -> Optional[dict]:
        """
        Získá odpověď od AI pro BehaviorEngine.

        Na rozdíl od get_response používá WorldEvent místo forced_event
        a podporuje nové typy odpovědí (action, nothing).

        Args:
            npc: NPC které má odpovědět
            soused: Druhé NPC (nebo None)
            historie: Historie rozhovoru
            relationship_rules: Pravidla vztahu
            memory_context: Kontext z paměti
            world_event_desc: Popis světové události
            extra_instruction: Extra instrukce (např. z ASSISTED módu)

        Returns:
            {"type": "speech"|"thought"|"action"|"nothing"|"goodbye", "text": "..."} nebo None
        """
        # Najdi poslední repliku souseda
        posledni_replika = None
        if soused:
            for h in reversed(historie[-50:]):
                if h.get("type") == "speech" and h.get("role") == soused["role"]:
                    posledni_replika = (h.get("text", "") or "").strip()
                    break

        # Sestav roleplay log
        roleplay_log = self._prompt_builder.build_roleplay_log(
            npc, soused, historie, limit=8
        )

        # Sestav prompt pro engine
        system_prompt, user_prompt = self._prompt_builder.build_engine_prompt(
            npc=npc,
            soused=soused,
            roleplay_log=roleplay_log,
            posledni_replika=posledni_replika,
            relationship_rules=relationship_rules,
            memory_context=memory_context,
            world_event_desc=world_event_desc,
            extra_instruction=extra_instruction,
        )

        # Loguj request
        self._logger.log_request(npc['role'], "engine", system_prompt, user_prompt)

        # Volej AI
        try:
            if DEBUG_AI:
                safe_print(f"\n--- ENGINE PROMPT ({npc['role']}) ---")
                preview = system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt
                safe_print(preview)

            response = self._client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=AI_TEMPERATURE,
                max_tokens=AI_MAX_TOKENS,
            )

            raw = response.choices[0].message.content
            safe_print(f"RAW ENGINE ({npc['role']}): {raw}")

            # Parsuj odpověď
            data = parse_response(raw)
            if not data:
                self._logger.log_response(npc['role'], raw, None)
                return None

            text = (data.get("text", "") or "").strip()
            typ = (data.get("type", "speech") or "speech").strip().lower()

            # Validace typu
            if typ not in VALID_RESPONSE_TYPES:
                typ = "speech"  # Fallback

            # Pro nothing a action může být text kratší nebo prázdný
            if typ in ("nothing",):
                # Pro nothing je OK nemít text
                if not text:
                    text = ""
            elif typ == "action":
                # Pro action musí být alespoň nějaký text
                if not text:
                    self._logger.log_response(npc['role'], raw, None, "Action bez textu")
                    return None
            else:
                # Pro speech/thought validace délky
                if not text or len(text) > 220:
                    self._logger.log_response(npc['role'], raw, None, "Text prázdný nebo moc dlouhý")
                    return None

            # Kontrola forward jump (příliš rychlé návrhy schůzek)
            familiarity = relationship_rules.get("familiarity", 0)
            if soused and familiarity < 9 and typ == "speech":
                if self._looks_like_forward_jump(text):
                    self._logger.log_response(npc['role'], raw, None, "Forward jump rejected")
                    return None

            # Detekce rozloučení
            if typ == "speech" and self._looks_like_goodbye(text):
                typ = "goodbye"

            result = {"type": typ, "text": text}
            self._logger.log_response(npc['role'], raw, result)
            return result

        except Exception as e:
            self._logger.log_response(npc['role'], "", None, str(e))
            safe_print(f"Chyba LLM (engine): {e}")
            safe_print(traceback.format_exc())
            return None

    def _looks_like_forward_jump(self, text: str) -> bool:
        """Kontroluje jestli text obsahuje příliš rychlé návrhy."""
        t = text.lower()
        return any(x in t for x in FORWARD_JUMP_TERMS)

    def _looks_like_goodbye(self, text: str) -> bool:
        """Kontroluje jestli text vypadá jako rozloučení."""
        t = text.lower()
        return any(x in t for x in GOODBYE_PHRASES)
