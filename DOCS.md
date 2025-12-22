# Lavička nad mořem - Technická dokumentace

## Přehled projektu

**Lavička nad mořem** je AI-driven simulace, kde NPC postavy sedí na lavičce u moře a vedou rozhovory. Každá postava má vlastní osobnost, paměť a vztahy s ostatními.

### Klíčové vlastnosti
- **Persistentní paměť** - NPC si pamatují předchozí rozhovory
- **Dynamické vztahy** - vztahy se vyvíjejí na základě kvality interakcí
- **Director systém** - řídí tok a dramaturgii scén
- **Lokální LLM** - běží na LM Studio (Qwen 2.5 nebo jiný model)

---

## Struktura projektu

```
lavicka/
├── run.py                    # Vstupní bod - spouští hru
├── ai_log.txt                # Log AI komunikace
│
├── game/
│   ├── app.py                # Hlavní orchestrace (LavickaApp)
│   ├── main.py               # Pygame smyčka + klávesové zkratky
│   ├── settings.py           # Konfigurace a konstanty
│   │
│   ├── npc/                  # Modul postav
│   │   ├── base.py           # Třída NPC
│   │   └── archetypes.py     # Načítání postav z JSON
│   │
│   ├── rules/                # Herní logika
│   │   ├── director.py       # Režisér scény
│   │   ├── relationships.py  # Správce vztahů
│   │   └── events.py         # Události prostředí
│   │
│   ├── ai/                   # AI komunikace
│   │   ├── client.py         # API wrapper pro LLM
│   │   ├── prompts.py        # Šablony promptů
│   │   ├── parser.py         # Parser odpovědí
│   │   └── logger.py         # Logování
│   │
│   ├── ui/                   # Pygame vykreslování
│   │   ├── renderer.py       # Scéna, lavička, NPC
│   │   ├── chat.py           # Chat panel
│   │   └── input_box.py      # Vstup pro události
│   │
│   ├── memory/               # Paměťový systém
│   │   └── pamet.py          # Persistentní paměť NPC
│   │
│   ├── utils/                # Pomocné funkce
│   │   └── helpers.py        # safe_print, strip_non_latin
│   │
│   └── data/                 # Datové soubory
│       ├── postavy.json      # Definice 5 archetypů
│       ├── pameti.json       # Paměť NPC (persistentní)
│       └── vztahy.json       # Vztahy mezi NPC
```

---

## Architektura

### Vrstvy systému

```
┌─────────────────────────────────────┐
│         UI LAYER (pygame)           │
│  Renderer, ChatPanel, InputBox      │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    ORCHESTRATION (app.py)           │
│  LavickaApp - koordinuje vše        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      GAME LOGIC (rules/)            │
│  Director, Relationships, Events    │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      AI LAYER (ai/)                 │
│  Client, Prompts, Parser            │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      DATA LAYER                     │
│  NPC, Memory, JSON soubory          │
└─────────────────────────────────────┘
```

### Tok jednoho tahu

```
main.py (event loop)
    │
    ▼
app.tah() [v threadu]
    │
    ├─► _zpracuj_prichody()  → náhodný příchod NPC
    ├─► _zpracuj_odchody()   → kontrola odchodů
    ├─► director.suggest_event() → automatické události
    ├─► _should_speak()      → rozhodnutí o tichu
    ├─► _vyber_mluvciho()    → kdo bude mluvit
    │
    ▼
_get_ai_response()
    │
    ├─► PromptBuilder.build_response_prompt()
    ├─► AIClient.get_response() → volání LLM
    └─► Parser.parse() → extrakce odpovědi
    │
    ▼
_zpracuj_odpoved()
    │
    ├─► _add_to_history()    → přidání do chatu
    ├─► relationships.update_after_speech()
    ├─► pamet.aktualizuj_vztah()
    └─► zobrazení bubliny
```

---

## Hlavní komponenty

### 1. LavickaApp (app.py)

Hlavní třída která koordinuje celou hru.

```python
class LavickaApp:
    def __init__(self):
        self.sedadla = [None, None]      # [levé, pravé sedadlo]
        self.historie = []                # historie rozhovorů
        self.relationships = RelationshipManager()
        self.director = Director()
        self.ai_client = AIClient()
        self.pamet = get_pamet()
```

**Klíčové metody:**
- `tah()` - provede jeden herní tah
- `vykresli()` - vykreslí celou scénu
- `add_environment_event(text)` - přidá událost prostředí

### 2. Director (rules/director.py)

Režisér který řídí dramaturgii scény.

**Trajektorie scény:**
| Typ | Délka (replik) | Popis |
|-----|----------------|-------|
| casual | 8-16 | Běžný rozhovor |
| deep | 14-25 | Hluboký rozhovor |
| conflict | 6-12 | Konfliktní scéna |
| quiet | 5-10 | Tiché setkání |

**Fáze scény:**
1. `intro` - NPC přišlo, oťukává situaci
2. `developing` - rozhovor se rozvíjí
3. `peak` - vrchol (dramatický moment)
4. `closing` - ukončování

**Intenty** - Director dává NPC cíle:
- "Váhá, jestli začít rozhovor."
- "Rozhovor plyne přirozeně."
- "Chce rozhovor hezky uzavřít."

### 3. RelationshipManager (rules/relationships.py)

Spravuje vztahy mezi NPC v rámci session.

```python
class Relationship:
    familiarity: float = 0      # 0-25, jak dobře se znají
    sympathy: float = 0         # -1 až +1
    tykani: bool = False        # zda si tykají
```

**Pravidla oslovování:**
- Při vykání: "MUSÍTE VYKAT. NIKDY NETYKEJ! Nepoužívej křestní jména."
- Při tykání: "Můžete TYKAT. Oslovuj křestním jménem."

### 4. Paměť (memory/pamet.py)

Persistentní paměť NPC uložená v JSON.

**Struktura vzpomínky:**
```python
{
    "id": "delnik_franta",
    "popis": "Chlap v montérkách",
    "jmeno": "Franta",           # pouze při tykání
    "dojem": "Přátelský člověk",
    "temata": ["počasí", "práce"],
    "fakta": ["Pracuje na stavbě"],
    "sila": 0.65,                # 0-1, síla vzpomínky
    "pocet_setkani": 3
}
```

**Rozpoznání podle síly:**
| Síla | Rozpoznání |
|------|------------|
| > 0.7 | poznam_dobre |
| > 0.5 | poznam |
| > 0.3 | povedome |
| > 0.1 | nejasne |
| ≤ 0.1 | neznam |

**Decay (zapomínání):**
- Faktor: 0.98 za den
- Minimum: 0.05 (pod tím se vzpomínka smaže)

### 5. Fáze vztahů

Vztahy mezi NPC procházejí fázemi:

| Fáze | Sympatie | Podmínky |
|------|----------|----------|
| cizinci | < 0.15 | Neznají se |
| tvare | ≥ 0.15 | Poznali se |
| znami | ≥ 0.4 | Dobře si rozumí |
| pratele | ≥ 0.6 | + tykání |

Fáze se vypočítává automaticky podle:
- `sympatie` (kvalita interakcí)
- `tykani` (formální blízkost)
- `historie` (významné události)

---

## NPC Archetypy

### Definice (data/postavy.json)

| ID | Role | Popis | Osobnost |
|----|------|-------|----------|
| babicka_vlasta | Babička Vlasta | Starší paní v šátku | Milá, nostalgická |
| manazer_petr | Manažer Petr | Muž v obleku | Uspěchaný, věcný |
| rebelka_adela | Rebelka Adéla | Mladá s barevnými vlasy | Ironická, stručná |
| delnik_franta | Dělník Franta | Chlap v montérkách | Bodrý, přímý |
| bezdomovec_lojza | Bezdomovec Lojza | Starší muž s plnovousem | Filosof, pomalý |

### Kompatibilita archetypů

Matice určuje tendenci k typu rozhovoru:

```
(babicka, franta)  → 60% casual, 20% deep, 5% conflict, 15% quiet
(rebelka, manazer) → 20% casual, 15% deep, 45% conflict, 20% quiet
(lojza, franta)    → 40% casual, 30% deep, 5% conflict, 25% quiet
```

---

## AI Systém

### Prompt struktura

```
IDENTITY_LOCK (ochrana role)

Jsi {role}. {vibe}
{rod_instrukce}
Místo: lavička u moře.

Emoce: {emotion} (intenzita {intensity}%), nálada {mood}

=== TVŮJ CÍL ===
{intent od Directora}

=== CO VÍŠ O ČLOVĚKU VEDLE ===
{memory_context}

Stav vztahu: familiarity={X}, sympatie={Y}, tykání={ANO/NE}

Pravidla:
- {addressing_rule}
- {pacing_rule}
- Buď krátký: 1-2 věty, max 170 znaků.

ROZHOVOR:
{posledních 8 replik}

Právě řekl/a: "{poslední replika}"

Odpověz přirozeně.
Vrať: {"type":"speech","text":"..."} NEBO {"type":"thought","text":"..."}
```

### Parser odpovědí

4 úrovně robustnosti:
1. **JSON parse** s opravami (trailing comma, překlepy)
2. **Regex** pro `"type": "...", "text": "..."`
3. **Regex** jen pro text
4. **Fallback** - čistý text jako speech

### Filtrace

Automaticky se odstraňují:
- Non-latin znaky (čínština apod.)
- Banned substrings: "AI", "model", "prompt", "instrukce"

---

## Události prostředí

### Typy událostí

| Typ | Příklad | Reakce |
|-----|---------|--------|
| hit | "Míč trefil {npc}" | Fyzická + AI |
| bird | "Racek přistál" | AI reakce |
| weather | "Začíná pršet" | Oba reagují |
| sound | "Někdo křičí" | AI reakce |

### Automatické události (Director)

Ve fázi `developing`:
- "Racek prolétl kolem lavičky"
- "Vítr zesílil"
- "Ozvalo se vzdálené houkání lodi"

Ve fázi `peak` (dramatické):
- "Začíná mrholit"
- "Kolem proběhl pes"
- "V dálce se blýsklo"

---

## Ovládání

| Klávesa | Akce |
|---------|------|
| MEZERNÍK | Manuální tah |
| A | Přepnout automat (zap/vyp) |
| E | Zadat událost prostředí |
| D | Aplikovat decay (zapomínání) |
| P | Vypsat paměť do konzole |
| R | Reset paměti |
| ESC | Ukončit hru |
| PageUp/Down | Scrollovat chat |

---

## Konfigurace (settings.py)

```python
# Rozlišení
RES_X, RES_Y = 1200, 800

# Automatický tah
AUTO_TAH_INTERVAL = 8.0  # sekundy

# Bublina
BUBLINA_MIN_TRVANI = 3.0
BUBLINA_RYCHLOST = 15    # znaků/sekunda

# Pravděpodobnosti
PRAVDEPODOBNOST_PRICHODU = 0.22
PRAVDEPODOBNOST_ODCHODU_SAM = 0.15
PRAVDEPODOBNOST_ODCHODU_PO_ROZHOVORU = 0.2
MIN_REPLIK_PRO_ODCHOD = 4

# Ticho
TICHO_SAM = 0.88  # šance že NPC sám mlčí
```

---

## Datové soubory

### postavy.json
Definice archetypů NPC (id, role, vibe, popis, rod, color).

### pameti.json
Persistentní paměť všech NPC - kdo koho zná, dojmy, témata, fakta.

### vztahy.json
Vztahy mezi páry NPC - fáze, tykání, sympatie, počet setkání, historie.

---

## Spuštění

### Požadavky
- Python 3.10+
- pygame
- openai (pro API volání)
- LM Studio běžící na localhost:1234

### Instalace
```bash
pip install pygame openai
```

### Spuštění
```bash
cd c:\_projekty\lavicka
python run.py
```

---

## Známé limitace

1. **RelationshipManager není persistentní** - familiarity se resetuje po restartu (sympatie a fáze se synchronizují do vztahy.json)

2. **Lokální model může ignorovat instrukce** - menší modely (Qwen 2.5) občas ignorují pravidla vykání

3. **Thread-safety** - sdílené proměnné nejsou vždy chráněny lockem

4. **Fyzické reakce** - všechny NPC mají stejné fyzické reakce, neliší se podle osobnosti

---

## Budoucí vylepšení

- [ ] Persistentní RelationshipManager
- [ ] Více archetypů postav
- [ ] Denní/noční cyklus
- [ ] Zvukové efekty
- [ ] Více lavičku (více scén současně)
- [ ] Web interface místo pygame
