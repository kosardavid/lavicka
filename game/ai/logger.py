"""
logger.py - Logování AI komunikace
===================================

Loguje všechny requesty a odpovědi do/z AI do souboru.
Log se přepíše při každém spuštění aplikace.
"""

import os
import time
from datetime import datetime
from typing import Optional

# Cesta k logu
LOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_FILE = os.path.join(LOG_DIR, "ai_log.txt")


class AILogger:
    """Logger pro AI komunikaci."""

    _instance: Optional["AILogger"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._start_time = time.time()
        self._request_count = 0
        self._init_log()

    def _init_log(self):
        """Inicializuje log soubor (přepíše existující)."""
        with open(LOG_FILE, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"AI LOG - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")

    def _write(self, text: str):
        """Zapíše text do logu."""
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text)

    def log_request(
        self,
        npc_role: str,
        request_type: str,
        system_prompt: str,
        user_prompt: str,
    ):
        """
        Loguje request do AI.

        Args:
            npc_role: Role NPC
            request_type: Typ requestu (response/summary)
            system_prompt: System prompt
            user_prompt: User prompt
        """
        self._request_count += 1
        elapsed = time.time() - self._start_time
        timestamp = datetime.now().strftime("%H:%M:%S")

        self._write(f"\n{'─' * 80}\n")
        self._write(f"[{timestamp}] REQUEST #{self._request_count} ({elapsed:.1f}s od startu)\n")
        self._write(f"NPC: {npc_role} | Typ: {request_type}\n")
        self._write(f"{'─' * 80}\n\n")

        self._write("=== SYSTEM PROMPT ===\n")
        self._write(system_prompt + "\n\n")

        self._write("=== USER PROMPT ===\n")
        self._write(user_prompt + "\n\n")

    def log_response(
        self,
        npc_role: str,
        raw_response: str,
        parsed: Optional[dict] = None,
        error: Optional[str] = None,
    ):
        """
        Loguje odpověď od AI.

        Args:
            npc_role: Role NPC
            raw_response: Surová odpověď
            parsed: Parsovaná odpověď (nebo None)
            error: Chybová zpráva (nebo None)
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        self._write(f"=== RESPONSE [{timestamp}] ===\n")
        self._write(f"RAW:\n{raw_response}\n\n")

        if error:
            self._write(f"ERROR: {error}\n\n")
        elif parsed:
            self._write(f"PARSED: {parsed}\n\n")
        else:
            self._write("PARSED: None (rejected)\n\n")

    def log_event(self, event_type: str, message: str):
        """
        Loguje obecnou událost.

        Args:
            event_type: Typ události
            message: Zpráva
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._write(f"[{timestamp}] {event_type}: {message}\n")

    def log_director(self, action: str, details: str):
        """
        Loguje akci Directora.

        Args:
            action: Typ akce (start_scene, observe, end_scene, etc.)
            details: Detaily akce
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._write(f"[{timestamp}] DIRECTOR {action}: {details}\n")


# Singleton instance
_logger: Optional[AILogger] = None


def get_ai_logger() -> AILogger:
    """Vrátí singleton instanci loggeru."""
    global _logger
    if _logger is None:
        _logger = AILogger()
    return _logger
