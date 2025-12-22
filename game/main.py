"""
main.py - Vstupní bod aplikace
===============================

Spouští hru Lavička nad mořem.

Použití:
    python -m game.main
    nebo
    python game/main.py
"""

import time
import threading
import pygame

from .app import LavickaApp
from .settings import AUTO_TAH_INTERVAL
from .utils import safe_print


def main():
    """Hlavní funkce - spouští hru."""
    app = LavickaApp()
    running = True
    next_auto = time.time() + AUTO_TAH_INTERVAL

    def vlakno_tah():
        """Vlákno pro AI tah."""
        app.tah()

    # Úvodní informace
    safe_print("=" * 50)
    safe_print("LAVIČKA NAD MOŘEM - Modulární verze 2.0")
    safe_print("=" * 50)
    safe_print("[A] Automat ZAP/VYP")
    safe_print("[MEZERNÍK] Ruční tah")
    safe_print("[E] Událost prostředí")
    safe_print("[D] Aplikovat decay (zapomínání)")
    safe_print("[P] Vypsat paměť všech NPC")
    safe_print("[R] Reset paměti")
    safe_print("[Kolečko/PgUp/PgDn] Scroll chatu")
    safe_print("[ESC] Konec")
    safe_print("=" * 50)

    while running:
        # Zpracování událostí
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Input box je aktivní
            if app.input_box.is_active():
                if event.type == pygame.KEYDOWN:
                    result = app.input_box.handle_key(event)
                    if result == "submit":
                        text = app.input_box.get_text()
                        app.add_environment_event(text)
                continue

            # Scroll kolečkem
            if event.type == pygame.MOUSEWHEEL:
                app.chat_panel.scroll(-event.y * 3)

            # Klávesy
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_a:
                    app.toggle_automat()

                elif event.key == pygame.K_SPACE:
                    if not app.is_busy():
                        threading.Thread(target=vlakno_tah, daemon=True).start()

                elif event.key == pygame.K_e:
                    app.input_box.activate()

                elif event.key == pygame.K_d:
                    app.aplikuj_decay()

                elif event.key == pygame.K_p:
                    app.vypis_pamet()

                elif event.key == pygame.K_r:
                    app.reset_pamet()

                elif event.key == pygame.K_PAGEUP:
                    app.chat_panel.scroll(10)

                elif event.key == pygame.K_PAGEDOWN:
                    app.chat_panel.scroll(-10)

                elif event.key == pygame.K_HOME:
                    app.chat_panel.scroll_to_top()

                elif event.key == pygame.K_END:
                    app.chat_panel.scroll_to_bottom()

        # Automatický tah
        if app.automat and not app.is_busy():
            if time.time() >= next_auto:
                threading.Thread(target=vlakno_tah, daemon=True).start()
                next_auto = time.time() + AUTO_TAH_INTERVAL

        # Vykreslení
        app.vykresli()
        pygame.time.delay(50)

    pygame.quit()


if __name__ == "__main__":
    main()
