# Lavička nad mořem

Simulace rozhovorů mezi NPC postavami sedícími na lavičce u moře. Hra používá lokální LLM pro generování přirozených dialogů.

NPC si pamatují lidi se kterými mluvili - ne doslovně, ale jako skutečný člověk (shrnutí, dojmy, fakta).

## Klíčové vlastnosti

- **Behavior Engine** - NPC rozhodují sami na základě vnitřních stavů (energie, drive, cooldown)
- **Persistentní paměť** - NPC si pamatují předchozí rozhovory
- **Dynamické vztahy** - vztahy se vyvíjejí na základě kvality interakcí
- **Director systém** - režisér řídí dramaturgii scén (fallback pro 1 NPC)
- **Dynamické postavy** - nové NPC lze přidat pouze editací JSON souboru
- **Lokální LLM** - běží na LM Studio (Qwen 2.5 nebo jiný model)

## Struktura projektu

```
lavicka/
├── run.py                 # Spouštěcí skript
├── README.md              # Tato dokumentace
├── DOCS.md                # Podrobná technická dokumentace
│
└── game/                  # Hlavní herní modul
    ├── __init__.py
    ├── main.py            # Vstupní bod, herní smyčka
    ├── app.py             # Hlavní aplikační třída
    ├── settings.py        # Konfigurace a konstanty
    │
    ├── engine/            # Behavior Engine (nový systém)
    │   ├── types.py       # Datové typy (WorldEvent, NPCBehaviorState...)
    │   ├── world_event.py # Generátor světových událostí
    │   ├── scorer.py      # Skórování NPC pro výběr mluvčího
    │   ├── anti_repetition.py  # Sledování opakování
    │   └── behavior_engine.py  # Hlavní orchestrátor
    │
    ├── npc/               # Modul pro NPC postavy
    │   ├── base.py        # Třída NPC
    │   └── archetypes.py  # Načítání postav z JSON
    │
    ├── rules/             # Herní pravidla
    │   ├── director.py    # Režisér scény (fallback)
    │   ├── relationships.py  # Vztahy mezi NPC
    │   └── events.py      # Události prostředí
    │
    ├── ai/                # Komunikace s AI
    │   ├── client.py      # OpenAI API klient
    │   ├── parser.py      # Parsování odpovědí
    │   ├── prompts.py     # Šablony promptů
    │   └── logger.py      # AI logování
    │
    ├── ui/                # Uživatelské rozhraní
    │   ├── renderer.py    # Vykreslování scény
    │   ├── chat.py        # Chat panel
    │   └── input_box.py   # Vstupní pole
    │
    ├── memory/            # Systém paměti NPC
    │   └── pamet.py       # Persistentní paměť
    │
    ├── utils/             # Pomocné funkce
    │   └── helpers.py     # Utility funkce
    │
    └── data/              # Data hry
        ├── postavy.json   # Definice NPC postav
        ├── pameti.json    # Uložená paměť NPC
        └── vztahy.json    # Vztahy mezi NPC
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

## NPC Postavy

Postavy jsou definovány v `game/data/postavy.json`. Každá postava má:

| Atribut | Popis |
|---------|-------|
| `id` | Unikátní identifikátor |
| `jmeno`, `prijmeni` | Celé jméno |
| `titul` | Titul (Babička, Manažer...) |
| `role` | Zobrazované jméno |
| `vibe` | Osobnost pro AI prompt |
| `popis` | Krátký popis vzhledu |
| `rod` | Pro správné skloňování |
| `temata` | Seznam zájmových témat |
| `povaha` | Osobnostní rysy (viz níže) |

### Osobnostní rysy (povaha)

Každá postava má tři klíčové vlastnosti:

| Rys | Rozsah | Vliv |
|-----|--------|------|
| `konfliktnost` | 0.0-1.0 | Tendence ke konfliktům |
| `hloubavost` | 0.0-1.0 | Tendence k hlubokým rozhovorům |
| `mluvnost` | 0.0-1.0 | Jak moc mluví vs. mlčí |

Tyto rysy určují dynamicky:
- Typ konverzace (casual/deep/conflict/quiet)
- Reakce na události
- Pravděpodobnost ticha

## Přidání nové postavy

Stačí přidat záznam do `game/data/postavy.json`:

```json
{
  "nova_postava": {
    "id": "nova_postava",
    "jmeno": "Jan",
    "prijmeni": "Novák",
    "titul": "Učitel",
    "role": "Učitel Jan",
    "vek": 45,
    "color": [100, 100, 200],
    "vibe": "Klidný, trpělivý, rád vysvětluje. Mluví srozumitelně.",
    "popis": "Muž středního věku s brýlemi",
    "rod": "muž",
    "temata": ["vzdělávání", "knihy", "historie", "děti", "trpělivost"],
    "povaha": {
      "konfliktnost": 0.15,
      "hloubavost": 0.7,
      "mluvnost": 0.6
    }
  }
}
```

**Žádný kód není potřeba měnit** - postava se automaticky načte a bude fungovat.

## Behavior Engine

Nový systém řízení NPC chování (pro dva NPC na lavičce):

### Princip

- **WorldEvent** generátor vytváří události (STIMULUS/PRESSURE/SILENCE)
- **NPC rozhodují sami** na základě vnitřních stavů
- **TOP K=1** NPC jde do AI za tah (minimalizace AI volání)
- **Anti-repetition** penalizuje opakující se NPC

### Stavy NPC

| Stav | Rozsah | Popis |
|------|--------|-------|
| `speak_drive` | 0-1 | Jak moc chce mluvit |
| `energy` | 0-1 | Energie (klesá po mluvení) |
| `cooldown` | 0+ tahů | Čekání po promluvení |

### Typy odpovědí

| Typ | Popis |
|-----|-------|
| `speech` | Mluvená replika |
| `thought` | Vnitřní myšlenka |
| `action` | Fyzická akce ("Podívá se na moře") |
| `nothing` | Ticho |
| `goodbye` | Rozloučení a odchod |

### ASSISTED mód

Když scéna "umírá" (2+ tahy ticha, energie < 0.15), engine nabídne nápovědu pro NPC.

## Director (Fallback)

Director se používá pro jednoho NPC na lavičce nebo když je engine vypnutý.

### Trajektorie

| Typ | Délka | Popis |
|-----|-------|-------|
| `casual` | 8-16 replik | Běžný rozhovor |
| `deep` | 14-25 replik | Hluboký, osobní rozhovor |
| `conflict` | 6-12 replik | Konfliktní scéna |
| `quiet` | 5-10 replik | Tiché setkání |

### Fáze scény

1. `intro` - NPC přišlo, oťukává situaci
2. `developing` - rozhovor se rozvíjí
3. `peak` - vrchol, dramatický moment
4. `closing` - ukončování

## Vztahy a paměť

### Fáze vztahů

| Fáze | Sympatie | Podmínky |
|------|----------|----------|
| cizinci | < 0.15 | Neznají se |
| tvare | ≥ 0.15 | Poznali se |
| znami | ≥ 0.4 | Dobře si rozumí |
| pratele | ≥ 0.6 | + musí si tykat |

### Vykání/Tykání

- Cizinci si **vždy vykají**
- Tykání je možné až po návrhu a přijetí
- AI dostává striktní pravidla pro správné oslovování

### Rozpoznání podle síly paměti

| Síla | Rozpoznání |
|------|------------|
| > 0.7 | "Ahoj Vlastičko!" |
| > 0.5 | "Vy jste ta paní co tu byla minule" |
| > 0.3 | "Vy mi někoho připomínáte..." |
| > 0.1 | Vágní pocit známosti |
| ≤ 0.1 | "Dobrý den" (cizinec) |

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

# === BEHAVIOR ENGINE ===
USE_BEHAVIOR_ENGINE = True      # True = nový engine, False = starý Director
BEHAVIOR_ENGINE_TOP_K = 1       # Kolik NPC jde do AI za tah
BEHAVIOR_COOLDOWN_SPEECH = 1    # Cooldown po promluvení
BEHAVIOR_ENERGY_COST_SPEECH = 0.15  # Spotřeba energie za mluvení
DEV_INTENT_LOG_ENABLED = True   # Detailní logování enginu
```

## Licence

MIT License
