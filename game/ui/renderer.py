"""
renderer.py - Vykreslování herní scény
=======================================

Stará se o vykreslení lavičky, moře, NPC a bublin.
"""

import pygame
from typing import Optional
from ..settings import (
    RES_X, RES_Y, HRANICE_PANELU,
    BARVA_NEBE, BARVA_MORE, BARVA_ZEME,
    BARVA_LAVICKY, BARVA_LAVICKY_NOHY,
    BARVA_BUBLINY, BARVA_MYSLENKY,
    BARVA_TEXTU, BARVA_TEXTU_MYSLENKY,
    POZICE_SEDADEL, POZICE_Y_NPC, POZICE_Y_JMENO, VELIKOST_NPC,
    LAVICKA_X, LAVICKA_Y, LAVICKA_SIRKA, LAVICKA_VYSKA,
)


class Renderer:
    """
    Vykresluje herní scénu.

    Používá Pygame pro vykreslování lavičky, moře,
    postav a jejich dialogových bublin.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 18)

    def draw_background(self):
        """Vykreslí pozadí - nebe, moře, zem."""
        # Nebe
        pygame.draw.rect(
            self.screen, BARVA_NEBE,
            (0, 0, HRANICE_PANELU, 400)
        )
        # Moře
        pygame.draw.rect(
            self.screen, BARVA_MORE,
            (0, 400, HRANICE_PANELU, RES_Y - 400)
        )
        # Zem
        pygame.draw.rect(
            self.screen, BARVA_ZEME,
            (0, 600, HRANICE_PANELU, 120)
        )

    def draw_bench(self):
        """Vykreslí lavičku."""
        # Sedadlo
        pygame.draw.rect(
            self.screen, BARVA_LAVICKY,
            (LAVICKA_X, LAVICKA_Y, LAVICKA_SIRKA, LAVICKA_VYSKA)
        )
        # Nohy
        pygame.draw.rect(
            self.screen, BARVA_LAVICKY_NOHY,
            (200, 590, 40, 60)
        )
        pygame.draw.rect(
            self.screen, BARVA_LAVICKY_NOHY,
            (660, 590, 40, 60)
        )

    def draw_npc(self, npc: dict, seat_index: int):
        """
        Vykreslí NPC postavu.

        Args:
            npc: Slovník s NPC daty (role, color)
            seat_index: 0 = levé sedadlo, 1 = pravé
        """
        px = POZICE_SEDADEL[seat_index]
        color = npc.get("color", (100, 100, 100))
        role = npc.get("role", "???")

        # Tělo (kruh)
        pygame.draw.circle(self.screen, color, (px, POZICE_Y_NPC), VELIKOST_NPC)

        # Jméno
        txt = self.font.render(role, True, (255, 255, 255))
        shadow = self.font.render(role, True, (0, 0, 0))

        x = px - txt.get_width() // 2
        self.screen.blit(shadow, (x + 2, POZICE_Y_JMENO))
        self.screen.blit(txt, (x, POZICE_Y_JMENO - 2))

    def draw_bubble(
        self,
        text: str,
        seat_index: int,
        is_thought: bool = False,
    ):
        """
        Vykreslí dialogovou bublinu.

        Args:
            text: Text v bublině
            seat_index: 0 = levé sedadlo, 1 = pravé
            is_thought: True pro myšlenku (jiná barva)
        """
        # Pozice bubliny
        bx = 120 if seat_index == 0 else 420
        by = 450

        # Barvy
        if is_thought:
            bg_color = BARVA_MYSLENKY
            text_color = BARVA_TEXTU_MYSLENKY
        else:
            bg_color = BARVA_BUBLINY
            text_color = BARVA_TEXTU

        # Zalamování textu
        radky = self._wrap_text(text, 30)

        # Velikost bubliny
        sirka = 320
        vyska = len(radky) * 25 + 20
        rect = pygame.Rect(bx, by - vyska, sirka, vyska)

        # Bublina
        pygame.draw.rect(self.screen, bg_color, rect, border_radius=15)
        pygame.draw.rect(self.screen, (0, 0, 0), rect, 2, border_radius=15)

        # Šipka dolů
        pygame.draw.polygon(
            self.screen, bg_color,
            [(bx + 30, by), (bx + 50, by), (bx + 40, by + 15)]
        )

        # Text
        for i, radek in enumerate(radky):
            img = self.font.render(radek, True, text_color)
            self.screen.blit(img, (bx + 15, by - vyska + 10 + i * 25))

    def draw_status_bar(self, status_text: str):
        """
        Vykreslí stavový řádek nahoře.

        Args:
            status_text: Text k zobrazení
        """
        info = self.font.render(status_text, True, (0, 0, 0))
        width = info.get_width() + 20

        pygame.draw.rect(
            self.screen, (255, 255, 255),
            (15, 15, width, 30)
        )
        self.screen.blit(info, (25, 20))

    def _wrap_text(self, text: str, max_chars: int) -> list:
        """Zalamuje text na řádky."""
        slova = text.split(' ')
        radky = []
        radek = []

        for slovo in slova:
            radek.append(slovo)
            if len(' '.join(radek)) > max_chars:
                radek.pop()
                radky.append(' '.join(radek))
                radek = [slovo]

        radky.append(' '.join(radek))
        return radky
