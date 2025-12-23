# Lavička nad mořem - Technická dokumentace

## Přehled projektu

**Lavička nad mořem** je AI-driven simulace, kde NPC postavy sedí na lavičce u moře a vedou rozhovory. Každá postava má vlastní osobnost, paměť a vztahy s ostatními.

### Klíčové vlastnosti
- **Persistentní paměť** - NPC si pamatují předchozí rozhovory
- **Dynamické vztahy** - vztahy se vyvíjejí na základě kvality interakcí
- **Director systém** - řídí tok a dramaturgii scén
- **Plně dynamické NPC** - žádný hardcoded kód pro konkrétní postavy
- **Lokální LLM** - běží na LM Studio (Qwen 2.5 nebo jiný model)

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
│   │   └── helpers.py        # safe_print, strip_non_latin, pair_key
│   │
│   └── data/                 # Datové soubory
│       ├── postavy.json      # Definice NPC postav
│       ├── pameti.json       # Paměť NPC (persistentní)
│       └── vztahy.json       # Vztahy mezi NPC
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

---

### 2. NPC Definice (data/postavy.json)

Každá postava je definována v JSON s těmito atributy:

```json
{
  "babicka_vlasta": {
    "id": "babicka_vlasta",
    "jmeno": "Vlasta",
    "prijmeni": "Nováková",
    "titul": "Babička",
    "role": "Babička Vlasta",
    "vek": 75,
    "color": [200, 200, 200],
    "vibe": "Milá, užívá si klid a vzpomíná na mládí. Mluví jemně a občas nostalgicky.",
    "popis": "Starší paní v šátku",
    "rod": "žena",
    "temata": ["vzpomínky na mládí", "rodina a vnoučata", "zdraví", "vaření a recepty"],
    "povaha": {
      "konfliktnost": 0.1,
      "hloubavost": 0.5,
      "mluvnost": 0.6
    }
  }
}
```

#### Povinné atributy

| Atribut | Typ | Popis |
|---------|-----|-------|
| `id` | string | Unikátní identifikátor |
| `jmeno` | string | Křestní jméno |
| `prijmeni` | string | Příjmení |
| `titul` | string | Titul/označení (Babička, Manažer...) |
| `role` | string | Zobrazované jméno |
| `vek` | int | Věk postavy |
| `color` | [r,g,b] | Barva pro UI |
| `vibe` | string | Popis osobnosti pro AI |
| `popis` | string | Krátký popis vzhledu |
| `rod` | "muž"/"žena" | Pro správné skloňování |
| `temata` | string[] | Seznam zájmových témat |
| `povaha` | object | Osobnostní rysy |

#### Povaha (osobnostní rysy)

| Rys | Rozsah | Popis | Vliv |
|-----|--------|-------|------|
| `konfliktnost` | 0.0-1.0 | Tendence ke konfliktům | Vyšší = více konfliktních scén |
| `hloubavost` | 0.0-1.0 | Tendence k hlubokým rozhovorům | Vyšší = delší, hlubší rozhovory |
| `mluvnost` | 0.0-1.0 | Jak moc mluví | Nižší = více ticha |

#### Témata

Pole `temata` obsahuje zájmy postavy. Při rozhovoru dvou NPC se náhodně kombinují témata obou a nabízí se AI jako inspirace.

Příklad: Babička (`["vzpomínky", "rodina"]`) + Dělník (`["fotbal", "pivo"]`) → AI dostane mix: "Možná témata: rodina, fotbal, vzpomínky"

---

### 3. Director (rules/director.py)

Režisér který řídí dramaturgii scény dynamicky na základě osobností NPC.

#### Trajektorie scény

| Typ | Délka (replik) | Popis |
|-----|----------------|-------|
| `casual` | 8-16 | Běžný rozhovor |
| `deep` | 14-25 | Hluboký rozhovor |
| `conflict` | 6-12 | Konfliktní scéna |
| `quiet` | 5-10 | Tiché setkání |

#### Dynamický výpočet trajektorie

Trajektorie se počítá z `povaha` atributů obou NPC:

```python
def _compute_compatibility(npc_a: dict, npc_b: dict) -> tuple:
    """Vrací (casual, deep, conflict, quiet) váhy."""

    # Průměry povah obou NPC
    konfliktnost = (npc_a.povaha.konfliktnost + npc_b.povaha.konfliktnost) / 2
    hloubavost = (npc_a.povaha.hloubavost + npc_b.povaha.hloubavost) / 2
    mluvnost = (npc_a.povaha.mluvnost + npc_b.povaha.mluvnost) / 2

    # Výpočet šancí
    conflict = konfliktnost * 0.8
    deep = hloubavost * 0.6
    quiet = (1 - mluvnost) * 0.5
    casual = max(0.2, 1.0 - conflict - deep - quiet)

    # Normalizace na součet 1.0
    return normalize(casual, deep, conflict, quiet)
```

#### Fáze scény

| Fáze | Popis | Typický intent |
|------|-------|----------------|
| `intro` | Začátek, oťukávání | "Právě přišel, oťukává situaci" |
| `developing` | Rozvoj tématu | volný průběh |
| `peak` | Vrchol rozhovoru | "Rozhovor je v plném proudu" |
| `closing` | Směřování k závěru | "Pomalu směřuje k rozloučení" |

#### Intenty

Director dává NPC "cíle" které ovlivňují jejich chování. Intenty jsou rozděleny podle rodu (muž/žena) pro správné skloňování:

```python
PHASE_INTENTS = {
    "intro": [
        {"m": "Právě přišel, oťukává situaci.", "f": "Právě přišla, oťukává situaci."},
        {"m": "Zkoumá, kdo vedle něj sedí.", "f": "Zkoumá, kdo vedle ní sedí."},
    ],
    "peak_conflict": [
        {"m": "Cítí napětí v rozhovoru.", "f": "Cítí napětí v rozhovoru."},
        {"m": "Nesouhlasí s názorem druhého.", "f": "Nesouhlasí s názorem druhého."},
    ],
    ...
}
```

#### Reakce na události

Reakce na události (hrubost, pití, přírodní jevy) jsou také dynamické podle `konfliktnost`:

```python
if konfliktnost > 0.4:
    instruction = "Reaguj podrážděně nebo ironicky."
elif konfliktnost < 0.2:
    instruction = "Buď překvapený/á a trochu zraněný/á."
else:
    instruction = "Reaguj přirozeně."
```

---

### 4. RelationshipManager (rules/relationships.py)

Spravuje vztahy mezi NPC v rámci session.

```python
class Relationship:
    familiarity: float = 0      # 0-25, jak dobře se znají
    sympathy: float = 0         # -1 až +1
    tykani: bool = False        # zda si tykají
    name_exchange: bool = False # zda si řekli jména
    pending_tykani: dict = None # probíhající návrh tykání
```

#### Pravidla oslovování

**Vykání (striktní):**
```
!!! VYKÁNÍ - STRIKTNÍ PRAVIDLO !!!
Používej POUZE tvary: vy, vás, vám, váš, vaše.
ZAKÁZÁNO: ty, tě, ti, tobě, tvůj, tvoje.
Neříkej jméno - jen "pane/paní" nebo neoslovuj vůbec.
Příklad správně: "Jak se máte?" "Co děláte?" "Líbí se vám tu?"
Příklad ŠPATNĚ: "Jak se máš?" "Co děláš?" "Líbí se ti tu?"
```

**Tykání:**
```
Tykáte si (ty/tobě/tebe). Oslovuj křestním jménem.
```

#### Dynamická témata

```python
def get_topic_suggestions(self, npc_a, npc_b) -> str:
    """Kombinuje témata obou NPC."""
    temata_a = npc_a.get("temata", [])
    temata_b = npc_b.get("temata", [])

    # Vyber 1-2 od každého
    selected = random.sample(temata_a, min(2, len(temata_a)))
    selected += random.sample(temata_b, min(2, len(temata_b)))

    # Zamíchej a vyber max 3
    random.shuffle(selected)
    return "Možná témata: " + ", ".join(selected[:3])
```

---

### 5. Paměť (memory/pamet.py)

Persistentní paměť NPC uložená v JSON.

#### Struktura vzpomínky

```python
{
    "id": "delnik_franta",
    "popis": "Chlap v montérkách",
    "jmeno": "Franta",           # pouze pokud zaznělo v rozhovoru
    "dojem": "Přátelský člověk",
    "temata": ["počasí", "práce"],
    "fakta": ["Pracuje na stavbě"],
    "sila": 0.65,                # 0-1, síla vzpomínky
    "pocet_setkani": 3
}
```

#### Rozpoznání podle síly

| Síla | Úroveň | Příklad reakce |
|------|--------|----------------|
| > 0.7 | poznam_dobre | "Ahoj Vlastičko!" |
| > 0.5 | poznam | "Vy jste ta paní co tu byla minule" |
| > 0.3 | povedome | "Vy mi někoho připomínáte..." |
| > 0.1 | nejasne | Vágní pocit známosti |
| ≤ 0.1 | neznam | "Dobrý den" (cizinec) |

#### Decay (zapomínání)

- Faktor: 0.98 za den
- Minimum: 0.05 (pod tím se vzpomínka smaže)
- Silné emoce = pomalejší zapomínání

---

### 6. Fáze vztahů

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

## AI Systém

### Prompt struktura

```
IDENTITY_LOCK (ochrana role)

Jsi {role}. {vibe}
Tvoje skutečné jméno je {jmeno}.
{rod_instrukce}
Místo: lavička u moře.

Emoce: {emotion} (intenzita {intensity}%), nálada {mood}

=== TVŮJ CÍL ===
{intent od Directora}

=== CO VÍŠ O ČLOVĚKU VEDLE ===
{memory_context}

Stav vztahu: familiarity={X}, sympatie={Y}, tykání={ANO/NE}

{addressing_rule}   ← striktní pravidla vykání/tykání
{pacing_rule}       ← pravidla tempa podle familiarity
{topic_suggestions} ← dynamicky generovaná témata

Další pravidla:
- Buď krátký: 1-2 věty, max 170 znaků.
- Neopakuj stejné otázky.
- Neodpovídej otázkou na otázku.

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

```python
AUTO_EVENTS_IMPULSE = [
    "Kolem proletěl racek.",
    "Od moře zafoukal vítr.",
    "Někde v dálce zahoukal parník.",
    "Na lavičku dopadl list.",
    "Přeběhla kolem kočka.",
]
```

---

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

**Žádný Python kód není potřeba měnit.** Postava se automaticky:
- Načte při startu hry
- Získá dynamicky vypočítané trajektorie s ostatními
- Dostane náhodná témata z kombinace svých a partnerových
- Reaguje podle své `konfliktnost` na události

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
Definice všech NPC postav včetně osobnosti, témat a povahových rysů.

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

## Designové principy

### 1. Žádný hardcoded kód pro konkrétní NPC

Veškerá logika je **dynamická**:
- Trajektorie se počítají z `povaha` atributů
- Témata se kombinují z `temata` obou NPC
- Reakce na události závisí na `konfliktnost`
- Intenty jsou parametrizované podle `rod`

### 2. Data-driven design

Nové postavy = jen editace JSON souboru. Žádné změny kódu.

### 3. Adaptivní Director

Director **nenutí**, jen **navádí**:
- Sleduje průběh rozhovoru
- Dává jemné hinty v intentech
- Adaptuje se na vývoj
- Ukončuje scény přirozeně

---

## Známé limitace

1. **Lokální model může ignorovat instrukce** - menší modely (Qwen 2.5) občas ignorují pravidla vykání

2. **Thread-safety** - sdílené proměnné nejsou vždy chráněny lockem

3. **Fyzické reakce** - všechny NPC mají stejné fyzické reakce

---

## Budoucí vylepšení

- [ ] Více archetypů postav
- [ ] Denní/noční cyklus
- [ ] Zvukové efekty
- [ ] Více laviček (více scén současně)
- [ ] Web interface místo pygame
