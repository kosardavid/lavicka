"""
settings.py - Konfigurace a konstanty hry
==========================================

Tento modul obsahuje veškeré konfigurovatelné hodnoty:
- Rozlišení obrazovky
- Barvy
- AI nastavení
- Herní konstanty
"""

# === OBRAZOVKA ===
RES_X = 1280
RES_Y = 720
HRANICE_PANELU = 900  # Kde končí herní plocha a začíná chat

# === BARVY ===
# Pozadí
BARVA_NEBE = (135, 206, 235)
BARVA_MORE = (0, 105, 148)
BARVA_ZEME = (100, 100, 80)

# Lavička
BARVA_LAVICKY = (139, 69, 19)
BARVA_LAVICKY_NOHY = (60, 40, 20)

# UI
BARVA_PANELU = (20, 30, 40)
BARVA_BUBLINY = (255, 255, 255)
BARVA_MYSLENKY = (220, 240, 255)
BARVA_TEXTU = (0, 0, 0)
BARVA_TEXTU_MYSLENKY = (30, 140, 255)

# Input box
BARVA_INPUT_BG = (10, 10, 10)
BARVA_INPUT_FG = (235, 235, 235)
BARVA_INPUT_BORDER = (200, 200, 200)

# === AI NASTAVENÍ ===
CLIENT_URL = "http://localhost:1234/v1"
API_KEY = "lm-studio"
MODEL_NAME = "local-model"

# AI parametry
AI_TEMPERATURE = 0.6
AI_MAX_TOKENS = 110
AI_SUMMARY_MAX_TOKENS = 250

# Debug
DEBUG_AI = True

# === BEHAVIOR ENGINE ===
# Feature flag pro nový engine (True = nový, False = starý Director)
USE_BEHAVIOR_ENGINE = True

# Kolik NPC může jít do AI za jeden tah (default 1)
BEHAVIOR_ENGINE_TOP_K = 1

# Cooldown po promluvení (počet tahů)
BEHAVIOR_COOLDOWN_SPEECH = 1

# Energie - kolik se spotřebuje za mluvení
BEHAVIOR_ENERGY_COST_SPEECH = 0.15

# Energie - regenerace za tah
BEHAVIOR_ENERGY_REGEN_TURN = 0.05

# Minimální skóre pro mluvení
BEHAVIOR_MIN_SCORE_TO_SPEAK = 0.15

# DEV_INTENT_LOG - detailní logování enginu
DEV_INTENT_LOG_ENABLED = True

# === HERNÍ KONSTANTY ===

# Časování
AUTO_TAH_INTERVAL = 2.2  # sekundy mezi automatickými tahy
BUBLINA_MIN_TRVANI = 4.0  # minimální doba zobrazení bubliny
BUBLINA_RYCHLOST = 12.0   # znaků za sekundu

# Pravděpodobnosti
PRAVDEPODOBNOST_PRICHODU = 0.22
PRAVDEPODOBNOST_ODCHODU_SAM = 0.15
PRAVDEPODOBNOST_ODCHODU_PO_ROZHOVORU = 0.16
MIN_REPLIK_PRO_ODCHOD = 16

# Ticho (šance že v tahu nikdo nic neřekne)
TICHO_CIZINCI = 0.55  # familiarity < 6
TICHO_ZNAMI = 0.35    # familiarity 6-12
TICHO_PRATELE = 0.22  # familiarity > 12
TICHO_SAM = 0.88      # když je NPC samo

# Události prostředí
ENV_REACTION_WINDOW = 12.0  # sekund pro reakci na událost
ENV_EVENT_TTL = 35.0        # jak dlouho je událost "aktivní"
MAX_ACTIVE_EVENTS = 10

# === FILTRY AI ODPOVĚDÍ ===
BANNED_SUBSTRINGS = [
    "jsem ai", "umělá inteligence", "language model", "jazykový model",
    "prompt", "instrukc", "system:", "json", "odpověď:", "myšlenka:",
    "jako asistent", "jako chatgpt", "openai", "llm", "token",
]

FORWARD_JUMP_TERMS = [
    "pojďme na káv", "zajdeme na káv", "setkáme se", "sejdeme se",
    "později", "zítra", "příště", "vyměníme si", "telefon", "číslo",
    "instagram", "facebook", "rande", "schůzk", "u mě doma",
    "k vám domů", "odvezu tě", "odvezu vás",
]

GOODBYE_PHRASES = [
    "na shledanou", "nashledanou", "mějte se", "musím jít",
    "půjdu", "loučím se", "hezký den"
]

# === POZICE NA OBRAZOVCE ===
POZICE_SEDADEL = [300, 600]  # X pozice pro levé a pravé sedadlo
POZICE_Y_NPC = 530
POZICE_Y_JMENO = 460
VELIKOST_NPC = 45  # poloměr kruhu

# Lavička
LAVICKA_X = 150
LAVICKA_Y = 550
LAVICKA_SIRKA = 600
LAVICKA_VYSKA = 40
