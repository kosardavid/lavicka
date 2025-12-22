"""
chat.py - Chat panel s historií
================================

Zobrazuje historii rozhovorů na pravé straně obrazovky.
Podporuje scrollování.
"""

import pygame
from typing import List
from ..settings import RES_X, RES_Y, HRANICE_PANELU, BARVA_PANELU


class ChatPanel:
    """
    Panel s historií chatů.

    Zobrazuje se na pravé straně obrazovky a obsahuje
    všechny repliky NPC.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Consolas", 14)
        self.scroll_lines = 0

        # Konstanty
        self.line_height = 16
        self.top_margin = 28
        self.bottom_margin = 26
        self.left_margin = 10

    def draw(self, historie: List[dict]):
        """
        Vykreslí chat panel.

        Args:
            historie: Seznam zpráv [{"role": "...", "text": "...", "type": "..."}]
        """
        # Pozadí panelu
        rect = pygame.Rect(HRANICE_PANELU, 0, RES_X - HRANICE_PANELU, RES_Y)
        pygame.draw.rect(self.screen, BARVA_PANELU, rect)

        # Oddělovací čára
        pygame.draw.line(
            self.screen, (255, 255, 255),
            (HRANICE_PANELU, 0), (HRANICE_PANELU, RES_Y), 2
        )

        # Hlavička
        header = self.font.render(
            "CHAT (kolečko / PgUp PgDn)", True, (200, 200, 200)
        )
        self.screen.blit(header, (HRANICE_PANELU + self.left_margin, 8))

        # Sestavení řádků
        lines = self._build_lines(historie)

        # Výpočet viditelné oblasti
        visible_height = RES_Y - self.bottom_margin - self.top_margin
        visible_lines = max(1, visible_height // self.line_height)
        total_lines = len(lines)

        # Omezení scrollu
        self._clamp_scroll(total_lines, visible_lines)

        # Výpočet viditelného rozsahu
        end = total_lines - self.scroll_lines
        start = max(0, end - visible_lines)
        visible = lines[start:end]

        # Vykreslení řádků
        y = self.top_margin
        for item in visible:
            surf = self.font.render(item["text"], True, item["color"])
            self.screen.blit(surf, (HRANICE_PANELU + self.left_margin, y))
            y += self.line_height

        # Indikátor scrollu
        if self.scroll_lines > 0:
            info = self.font.render(
                f"↑ posun: {self.scroll_lines}", True, (180, 180, 180)
            )
            self.screen.blit(info, (HRANICE_PANELU + self.left_margin, RES_Y - 22))

    def scroll(self, delta: int):
        """
        Scrolluje chat.

        Args:
            delta: Kladné = nahoru, záporné = dolů
        """
        self.scroll_lines += delta
        if self.scroll_lines < 0:
            self.scroll_lines = 0

    def scroll_to_bottom(self):
        """Scrolluje na konec (nejnovější zprávy)."""
        self.scroll_lines = 0

    def scroll_to_top(self):
        """Scrolluje na začátek (nejstarší zprávy)."""
        self.scroll_lines = 10**9  # Bude oříznuto v _clamp_scroll

    def _build_lines(self, historie: List[dict]) -> List[dict]:
        """
        Převede historii na seznam řádků pro vykreslení.

        Zalamuje dlouhé texty na více řádků.
        """
        max_width = RES_X - HRANICE_PANELU - 25
        out = []

        for msg in historie:
            role = msg.get("role", "?")
            text = msg.get("text", "") or ""
            msg_type = msg.get("type", "speech")

            # Barvy podle typu
            if msg_type == "thought":
                c_role = (255, 165, 0)
                c_text = (100, 200, 255)
                text = f"({text})"
            elif msg_type == "sys":
                c_role = (50, 255, 50)
                c_text = (150, 255, 150)
            else:
                c_role = (255, 165, 0)
                c_text = (255, 255, 255)

            # Role
            out.append({"text": f"{role}:", "color": c_role})

            # Text (zalomený)
            out.extend(self._wrap_text(text, c_text, max_width))

            # Prázdný řádek
            out.append({"text": "", "color": c_text})

        return out

    def _wrap_text(self, text: str, color: tuple, max_width: int) -> List[dict]:
        """Zalamuje text na řádky podle šířky."""
        words = (text or "").split()
        lines = []

        if not words:
            return [{"text": "", "color": color}]

        current = words[0]
        for w in words[1:]:
            test = current + " " + w
            if self.font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append({"text": current, "color": color})
                current = w

        lines.append({"text": current, "color": color})
        return lines

    def _clamp_scroll(self, total_lines: int, visible_lines: int):
        """Omezí scroll do platného rozsahu."""
        max_scroll = max(0, total_lines - visible_lines)
        self.scroll_lines = max(0, min(self.scroll_lines, max_scroll))
