"""
ai - Modul pro komunikaci s AI
===============================

Obsahuje:
- AIClient: Klient pro komunikaci s LLM
- Parser: Parsování AI odpovědí
- PromptBuilder: Sestavování promptů
"""

from .client import AIClient
from .parser import parse_response, parse_summary
from .prompts import PromptBuilder
