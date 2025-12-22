"""
input_box.py - Vstupní pole pro události
=========================================

Textové pole pro zadávání událostí prostředí.
"""

import pygame
from ..settings import (
    RES_Y, HRANICE_PANELU,
    BARVA_INPUT_BG, BARVA_INPUT_FG, BARVA_INPUT_BORDER,
)


class InputBox:
    """
    Vstupní pole pro zadávání textu.

    Používá se pro zadávání událostí prostředí.
    """

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.font = pygame.font.SysFont("Arial", 18)

        self.active = False
        self.text = ""
        self.hint = "Napiš událost prostředí (Enter = potvrdit, Esc = zrušit)"

        # Rozměry
        self.width = HRANICE_PANELU - 40
        self.height = 44
        self.x = 20
        self.y = RES_Y - self.height - 20

    def draw(self):
        """Vykreslí vstupní pole (pokud je aktivní)."""
        if not self.active:
            return

        # Pozadí
        pygame.draw.rect(
            self.screen, BARVA_INPUT_BG,
            (self.x, self.y, self.width, self.height),
            border_radius=10
        )

        # Okraj
        pygame.draw.rect(
            self.screen, BARVA_INPUT_BORDER,
            (self.x, self.y, self.width, self.height),
            2, border_radius=10
        )

        # Text nebo hint
        if self.text:
            display_text = self.text
            color = BARVA_INPUT_FG
        else:
            display_text = self.hint
            color = (160, 160, 160)

        # Oříznutí textu pokud je moc dlouhý
        while self.font.size(display_text)[0] > (self.width - 20) and len(display_text) > 5:
            display_text = display_text[1:]

        surf = self.font.render(display_text, True, color)
        self.screen.blit(surf, (self.x + 10, self.y + 12))

    def activate(self):
        """Aktivuje vstupní pole."""
        self.active = True
        self.text = ""

    def deactivate(self):
        """Deaktivuje vstupní pole."""
        self.active = False
        self.text = ""

    def handle_key(self, event: pygame.event.Event) -> str:
        """
        Zpracuje stisk klávesy.

        Args:
            event: Pygame KEYDOWN event

        Returns:
            "submit" pokud byl stisknut Enter s textem
            "cancel" pokud byl stisknut Escape
            "" jinak
        """
        if not self.active:
            return ""

        if event.key == pygame.K_ESCAPE:
            self.deactivate()
            return "cancel"

        elif event.key == pygame.K_RETURN:
            result = self.text.strip()
            if result:
                self._submitted_text = result
                self.deactivate()
                return "submit"
            self.deactivate()
            return "cancel"

        elif event.key == pygame.K_BACKSPACE:
            self.text = self.text[:-1]

        else:
            if event.unicode and len(event.unicode) == 1:
                if len(self.text) < 120:
                    self.text += event.unicode

        return ""

    def get_text(self) -> str:
        """Vrátí odeslaný text (nebo aktuální pokud není odeslaný)."""
        if hasattr(self, '_submitted_text') and self._submitted_text:
            result = self._submitted_text
            self._submitted_text = ""
            return result
        return self.text.strip()

    def is_active(self) -> bool:
        """Vrací True pokud je pole aktivní."""
        return self.active
