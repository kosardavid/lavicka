# Lavička nad mořem

Simulace rozhovorů mezi NPC postavami sedícími na lavičce u moře. Hra používá lokální LLM pro generování přirozených dialogů.

NPC si pamatují lidi se kterými mluvili - ne doslovně, ale jako skutečný člověk (shrnutí, dojmy, fakta).

## Struktura projektu (Modulární v2.0)

```
lavicka/
├── run.py                 # Spouštěcí skript
├── README.md              # Tato dokumentace
│
└── game/                  # Hlavní herní modul
    ├── __init__.py
    ├── main.py            # Vstupní bod, herní smyčka
    ├── app.py             # Hlavní aplikační třída
    ├── settings.py        # Konfigurace a konstanty
    │
    ├── npc/               # Modul pro NPC postavy
    │   ├── __init__.py
    │   ├── base.py        # Třída NPC
    │   └── archetypes.py  # Definice postav (Babička, Manažer, ...)
    │
    ├── rules/             # Herní pravidla
    │   ├── __init__.py
    │   ├── relationships.py  # Vztahy mezi NPC
    │   └── events.py      # Události prostředí
    │
    ├── ai/                # Komunikace s AI
    │   ├── __init__.py
    │   ├── client.py      # OpenAI API klient
    │   ├── parser.py      # Parsování odpovědí
    │   └── prompts.py     # Šablony promptů
    │
    ├── ui/                # Uživatelské rozhraní
    │   ├── __init__.py
    │   ├── renderer.py    # Vykreslování scény
    │   ├── chat.py        # Chat panel
    │   └── input_box.py   # Vstupní pole
    │
    ├── memory/            # Systém paměti NPC
    │   ├── __init__.py
    │   └── pamet.py       # Persistentní paměť
    │
    ├── utils/             # Pomocné funkce
    │   ├── __init__.py
    │   └── helpers.py     # Utility funkce
    │
    └── data/              # Data hry (automaticky vytvořeno)
        └── memories.json  # Uložená paměť NPC
```

## Požadavky

- Python 3.10+
- pygame
- openai (pro API volání)
- Běžící LLM server (LM Studio, Ollama, nebo podobný)

## Instalace

```bash
pip install pygame openai
```

## Spuštění

1. Spusťte LM Studio (nebo jiný lokální LLM server) na `http://localhost:1234`
2. Spusťte hru:

```bash
python run.py
```

Alternativně:
```bash
python -m game.main
```

## Ovládání

| Klávesa | Akce |
|---------|------|
| **ESC** | Ukončí hru |
| **A** | Přepne automatický režim (ZAP/VYP) |
| **MEZERNÍK** | Ruční tah (AI generuje odpověď) |
| **E** | Zadá událost prostředí |
| **D** | Aplikuje decay (zapomínání) |
| **P** | Vypíše paměť všech NPC |
| **R** | Resetuje paměť |
| **Kolečko myši** | Scrollování chatu |
| **PgUp/PgDn** | Scrollování chatu |
| **Home/End** | Skok na začátek/konec chatu |

## Moduly

### npc/
Definuje NPC postavy a jejich archetypy. Každá postava má:
- **id**: Unikátní identifikátor
- **role**: Zobrazované jméno
- **vibe**: Osobnost pro AI prompt
- **popis**: Krátký popis vzhledu
- **rod**: Pro správné skloňování v češtině

### rules/
Obsahuje herní pravidla:
- **RelationshipManager**: Sleduje vztahy (familiarity, sympathy, tykání)
- **EventManager**: Zpracovává události prostředí

### ai/
Komunikace s LLM:
- **AIClient**: Wrapper pro OpenAI API
- **Parser**: Robustní parsování různých formátů odpovědí
- **PromptBuilder**: Sestavování promptů s kontextem

### ui/
Pygame vykreslování:
- **Renderer**: Lavička, moře, NPC, bubliny
- **ChatPanel**: Historie rozhovorů
- **InputBox**: Zadávání událostí

### memory/
Persistentní paměť NPC:
- Ukládá vzpomínky na setkání
- Podporuje zapomínání (decay)
- Ukládá se do JSON souboru

## Jak paměť funguje

### Ukládání

Po každém rozhovoru (když někdo odejde) se AI zeptá:
- Jak ten člověk vypadal?
- Jaký z něj máš dojem?
- O čem jste mluvili?
- Co ses dozvěděl?

Uloží se **shrnutí**, ne doslovný text.

### Rozpoznávání

Při dalším setkání se hledá v paměti:
- `poznam_dobre` (síla > 0.7) - "Ahoj Vlastičko!"
- `poznam` (síla > 0.5) - "Vy jste ta paní co tu byla minule"
- `povedome` (síla > 0.3) - "Vy mi někoho připomínáte..."
- `nejasne` (síla > 0.1) - Vágní pocit známosti
- `neznam` - "Dobrý den" (cizinec)

### Zapomínání (Decay)

- Každý "den" síla paměti klesá o 2%
- Pod 5% = vzpomínka se smaže
- Opakovaná setkání posilují paměť
- Silné emoce = pomalejší zapomínání

### Vztahy

Fáze: `cizinci` → `tvare` → `znami` → `pratele`

| Fáze | Sympatie | Podmínky |
|------|----------|----------|
| cizinci | < 0.15 | Neznají se |
| tvare | ≥ 0.15 | Poznali se, neutrální dojem |
| znami | ≥ 0.4 | Dobře si rozumí |
| pratele | ≥ 0.6 | + musí si tykat |

Sleduje se:
- Sympatie (-1 až +1) - kvalita interakcí
- Tykání/vykání - formální blízkost
- Historie - významné události (bonus/penalty)

### Director (Režisér scény)

Director řídí dramaturgii rozhovoru:

**Trajektorie:**
- `casual` (8-16 replik) - běžný rozhovor
- `deep` (14-25 replik) - hluboký rozhovor
- `conflict` (6-12 replik) - konfliktní scéna
- `quiet` (5-10 replik) - tiché setkání

**Fáze scény:**
1. `intro` - NPC přišlo, oťukává situaci
2. `developing` - rozhovor se rozvíjí
3. `peak` - vrchol, dramatický moment
4. `closing` - ukončování

Director dává NPC "intenty" (cíle) které ovlivňují jejich chování.

## Konfigurace

Hlavní nastavení v `game/settings.py`:

```python
# AI server
CLIENT_URL = "http://localhost:1234/v1"
API_KEY = "lm-studio"

# Rozlišení
RES_X, RES_Y = 1280, 720

# Rychlost hry
AUTO_TAH_INTERVAL = 2.2  # sekundy mezi tahy

# Debug
DEBUG_AI = True  # Vypisuje prompty do konzole
```

## Přidání nové postavy

V souboru `game/npc/archetypes.py`:

```python
ARCHETYPY.append({
    "id": "nova_postava",
    "role": "Nová Postava",
    "vek": 30,
    "color": (100, 100, 200),
    "vibe": "Popis osobnosti pro AI...",
    "popis": "Krátký popis vzhledu",
    "rod": "muž",  # nebo "žena"
})
```

## Přidání nového typu události

V souboru `game/rules/events.py`:

```python
EVENT_KEYWORDS["novy_typ"] = ["klíčové", "slovo", "pro", "detekci"]

PHYSICAL_REACTIONS["target"]["novy_typ"] = ["Reakce 1", "Reakce 2"]
PHYSICAL_REACTIONS["observer"]["novy_typ"] = ["Reakce pozorující"]
```

## Architektura

```
┌─────────────┐
│   main.py   │  Herní smyčka, události
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   app.py    │  Koordinuje všechny moduly
└──────┬──────┘
       │
       ├──────────────┬──────────────┬──────────────┐
       ▼              ▼              ▼              ▼
┌─────────────┐┌─────────────┐┌─────────────┐┌─────────────┐
│   npc/      ││   rules/    ││   ai/       ││   ui/       │
│ Postavy    ││ Pravidla   ││ LLM klient ││ Vykreslení │
└─────────────┘└─────────────┘└─────────────┘└─────────────┘
       │              │              │
       └──────────────┼──────────────┘
                      ▼
               ┌─────────────┐
               │  memory/    │
               │ Persistentní│
               │   paměť     │
               └─────────────┘
```

## Příklad paměti

```json
{
  "id": "delnik_franta",
  "popis": "chlap v montérkách, asi 50 let",
  "jmeno": "Franta",
  "dojem": "sympatický, bodrý, trochu unavený",
  "temata": ["práce", "rodina", "moře"],
  "fakta": [
    "pracuje na stavbě",
    "je rozvedený",
    "syn se s ním nebaví"
  ],
  "sila": 0.72,
  "pocet_setkani": 5
}
```

## Licence

MIT License
