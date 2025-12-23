# Lavička nad mořem - Technická dokumentace

## Přehled projektu

**Lavička nad mořem** je AI-driven simulace, kde NPC postavy sedí na lavičce u moře a vedou rozhovory. Každá postava má vlastní osobnost, paměť a vztahy s ostatními.

### Klíčové vlastnosti
- **Behavior Engine** - NPC rozhodují sami na základě vnitřních stavů
- **Persistentní paměť** - NPC si pamatují předchozí rozhovory
- **Dynamické vztahy** - vztahy se vyvíjejí na základě kvality interakcí
- **Director systém** - fallback pro jednoho NPC
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
│    BEHAVIOR ENGINE (engine/)        │
│  WorldEvent, Scorer, AntiRep        │
│  (pro 2 NPC - hlavní systém)        │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      GAME LOGIC (rules/)            │
│  Director (fallback), Relationships │
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

### Tok jednoho tahu (Behavior Engine)

```
main.py (event loop)
    │
    ▼
app.tah() [v threadu]
    │
    ├─► _zpracuj_prichody()  → náhodný příchod NPC
    ├─► _zpracuj_odchody()   → kontrola odchodů
    │
    ▼ (pokud 2 NPC a USE_BEHAVIOR_ENGINE=True)
_tah_engine()
    │
    ├─► WorldEventGenerator.generate() → STIMULUS/PRESSURE/SILENCE
    ├─► SpeakScorer.select_top_k() → výběr NPC pro AI
    ├─► AntiRepetitionTracker.get_penalties()
    │
    ▼ (pro TOP K NPC)
ai_call_fn() callback
    │
    ├─► PromptBuilder.build_engine_prompt()
    ├─► AIClient.get_engine_response() → volání LLM
    └─► Parser.parse() → extrakce odpovědi
    │
    ▼
_zpracuj_engine_odpoved()
    │
    ├─► _add_to_history()    → přidání do chatu
    ├─► relationships.update_after_speech()
    ├─► pamet.aktualizuj_vztah()
    └─► zobrazení bubliny
```

### Tok jednoho tahu (Legacy/Fallback)

```
_tah_legacy() [pro 1 NPC nebo engine vypnutý]
    │
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
│   ├── engine/               # Behavior Engine (nový systém)
│   │   ├── types.py          # WorldEvent, NPCBehaviorState, ResponseType
│   │   ├── world_event.py    # Generátor světových událostí
│   │   ├── scorer.py         # Skórování NPC pro výběr mluvčího
│   │   ├── anti_repetition.py # Sledování opakování frází
│   │   └── behavior_engine.py # Hlavní orchestrátor + DEV_INTENT_LOG
│   │
│   ├── npc/                  # Modul postav
│   │   ├── base.py           # Třída NPC
│   │   └── archetypes.py     # Načítání postav z JSON
│   │
│   ├── rules/                # Herní logika (fallback)
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

### 3. Behavior Engine (engine/)

Nový systém řízení NPC chování pro dva NPC na lavičce.

#### Princip

1. **Director neřídí repliky** - jen generuje WorldEvent
2. **NPC rozhodují sami** na základě vnitřních stavů
3. **TOP K=1** NPC jde do AI za tah
4. **Dynamické drives** - speak_drive a stay_drive se mění každý tah
5. **Post-check anti-repetition** - opakující se repliky jsou downgradovány nebo odmítnuty
6. **Aktivita ≠ ticho** - action/thought nepočítá jako "mrtvá scéna"

#### Struktura souborů

```
engine/
├── types.py              # Datové typy (WorldEvent, NPCBehaviorState, SceneContext...)
├── behavior_engine.py    # Hlavní orchestrátor + DEV_INTENT_LOG
├── world_event.py        # Generátor světových událostí
├── scorer.py             # Skórování NPC pro výběr mluvčího
├── anti_repetition.py    # Sledování opakování + rejection logic
└── drive_update.py       # Dynamická aktualizace speak_drive a stay_drive
```

#### Datové typy (types.py)

```python
class WorldEventType(Enum):
    STIMULUS = "stimulus"    # Něco se stalo (racek, vítr)
    PRESSURE = "pressure"    # Tlak na reakci (otázka)
    SILENCE = "silence"      # Ticho - prostor pro iniciativu

@dataclass
class NPCBehaviorState:
    npc_id: str
    speak_drive: float = 0.3      # Jak moc chce mluvit (0-1) - DYNAMICKY SE MĚNÍ
    stay_drive: float = 0.7       # Jak moc chce zůstat (0-1) - DYNAMICKY SE MĚNÍ
    engagement_drive: float = 0.3  # "Sociální povolení" mluvit (0-1) - roste při oslovení
    cooldown_turns: int = 0       # Kolik tahů musí čekat
    energy: float = 1.0           # Energie (0-1)
    last_acted_turn: int = -1     # Poslední tah kdy udělal COKOLI (speech/action/thought)
    last_selected_turn: int = -1  # Poslední tah kdy byl vybrán pro AI (i nothing)
    last_addressed_turn: int = -1  # Poslední tah kdy byl osloven/dotázán

class ResponseType(Enum):
    SPEECH = "speech"       # Mluvená replika
    THOUGHT = "thought"     # Vnitřní myšlenka
    ACTION = "action"       # Fyzická akce bez slov
    NOTHING = "nothing"     # Ticho
    GOODBYE = "goodbye"     # Loučení a odchod (pouze interní, ne v promptu)

@dataclass
class SceneContext:
    turn_number: int = 0
    scene_energy: float = 0.5
    consecutive_silence: int = 0      # Počet tahů bez řeči
    consecutive_inactivity: int = 0   # Počet tahů bez jakékoli aktivity
    # on_speech() / on_action() / on_thought() / on_nothing()
```

#### DriveUpdater (drive_update.py)

Dynamická aktualizace speak_drive, stay_drive a engagement_drive každý tah:

**speak_drive se mění podle:**
- PRESSURE na NPC → +0.25 boost
- Přímé oslovení jménem → +0.15 boost (včetně vokativů!)
- SILENCE → růst jen u mluvných (mluvnost > 0.3)
- Nízká energie → penalizace
- Cooldown → penalizace
- Anti-rep penalty → snížení chuti mluvit

**stay_drive se mění podle:**
- Mrtvá scéna (is_dying) → klesá
- Dlouhé ticho (3+ tahů) → klesá
- Nízká energie NPC → klesá
- Vysoká repetice → klesá (nuda)
- Živá scéna (energy > 0.6) → boost

**engagement_drive ("sociální povolení") se mění podle:**
- Přímé oslovení jménem/titulem → +0.35 boost
- Otázka směřovaná na NPC → +0.25 boost (použije se max, ne součet!)
- PRESSURE event na NPC → +0.10 * intensity
- SILENCE (bez oslovení) → -0.05 decay
- NPC vybráno ale ne osloveno → -0.06 decay
- **Cap růstu za tah:** max +0.45 (aby +0.60 nebylo běžné)

**Permission Gate (před AI voláním):**
```python
# Pokud NPC nemá "sociální povolení", přeskoč AI call
if engagement_drive < 0.25 and speak_drive < 0.65:
    # Vrať NOTHING nebo ACTION místo volání AI
    if speak_drive > 0.45:
        return ACTION("Pozoruje okolí.")
    else:
        return NOTHING
```

**Detekce oslovení (detect_addressing):**
```python
# Podporuje české vokativy:
# Vlasta -> Vlasto, Babička -> Babičko, Karel -> Karle

# Používá regex s word boundary - nechytá substrings!
detect_addressing("Babičko, jak se máte?", "Jana", "Babička") -> True
detect_addressing("S babičkami je to těžké.", "Jana", "Babička") -> False  # substring

# Kontroluje začátek věty nebo po čárce:
detect_addressing("Karle, co myslíte?", "Karel", "") -> True  # po čárce
detect_addressing("Ten Karel je hodný.", "Karel", "") -> False  # uprostřed věty
```

**Detekce otázky na NPC (detect_question_to_npc):**
```python
# Otázka = text obsahuje "?"
# Pro 2 NPC: každá otázka je automaticky na toho druhého
# Pro 3+ NPC: vyžaduje oslovení

detect_question_to_npc("Jak se máte?", "Jana", "Babička", total_npcs=2) -> True   # 2 NPC
detect_question_to_npc("Jak se máte?", "Jana", "Babička", total_npcs=3) -> False  # 3 NPC, žádné oslovení
detect_question_to_npc("Babičko, jak se máte?", "Jana", "Babička", total_npcs=3) -> True
```

```python
class DriveUpdater:
    def update_drives(state, npc_data, world_event, scene_context,
                      anti_rep_penalty, was_addressed, was_asked_question):
        # Aktualizuje speak_drive, stay_drive a engagement_drive

    def on_after_speech(state, was_successful):
        # Drop speak_drive po mluvení
```

#### WorldEvent Generator (world_event.py)

Generuje světové události s **kombinovaným turn + time cooldownem**:

```python
def __init__(
    ambient_time_cooldown: float = 20.0,   # Minimálně 20s mezi ambient
    ambient_turn_cooldown: int = 3,        # Minimálně 3 tahy mezi ambient
    ambient_chance: float = 0.15,          # 15% šance po splnění cooldownů
):

def generate(scene_context, forced_event, last_response_was_question, question_target_id):
    # 1. Vynucená událost od uživatele -> PRESSURE/STIMULUS
    # 2. Poslední replika byla otázka -> PRESSURE na druhého
    # 3. Scéna "umírá" -> STIMULUS pro oživení
    # 4. Náhodná ambient událost (turn + time cooldown)
    # 5. Výchozí: SILENCE
```

#### Scorer (scorer.py)

Skóruje NPC a vybírá TOP K pro AI:

```python
score = speak_drive * energy
      + bonus za PRESSURE target (0.4 * intensity)
      + bonus za STIMULUS * mluvnost (0.2 * intensity * mluvnost)
      - penalizace za cooldown (0.3 * cooldown_turns)
      - penalizace za nízkou energii
      - penalizace za opakování (0.3 * anti_rep)
      - penalizace za právě provedenou akci (just_acted: -0.25/-0.125)
      - penalizace za nedávný výběr (just_selected: -0.15/-0.075)
      + engagement bonus/penalizace (viz níže)
```

**Max consecutive speaker (v3.6):**
```python
# Žádné NPC nemůže mluvit víc než 2x za sebou
max_consecutive_speaker = 2

# Před AI voláním:
if _last_speaker_id == npc_id and _consecutive_speaker_count >= 2:
    -> vrať ACTION bez AI volání

# Po SPEECH:
if _last_speaker_id == npc_id:
    _consecutive_speaker_count += 1
else:
    _consecutive_speaker_count = 1

# Po THOUGHT/ACTION/NOTHING se counter RESETUJE:
_last_speaker_id = None
_consecutive_speaker_count = 0
```

**Engagement v scoringu (v3.5):**
```python
# Vysoký engagement (≥ 0.5) = bonus
engagement_mod = +0.15 * (engagement - 0.5) * 2

# Nízký engagement (< 0.25) = penalizace
engagement_mod = -0.20 * (0.25 - engagement) * 4

# Tím se TOP_K častěji vybírá ten, kdo má právo mluvit
# a neplýtvá se AI callem na někoho kdo bude gate-ován
```

**Penalizace za právě provedenou akci:**
```python
# Aby se jedno NPC nestřídalo samo se sebou
# (např. 15x action za sebou bez šance pro druhé NPC)
if last_acted_turn == current_turn:
    just_acted = -0.25  # Tento tah = vysoká penalizace
elif last_acted_turn == current_turn - 1:
    just_acted = -0.125  # Minulý tah = mírná penalizace
else:
    just_acted = 0  # 2+ tahy = žádná penalizace

# POZOR: "nothing" se NEPOČÍTÁ jako akce!
# NPC které mlčí může být znovu vybráno.
```

**Penalizace za nedávný výběr (řeší "díru" v nothing):**
```python
# Když NPC vrátí nothing, stále ho penalizujeme
# aby druhé NPC dostalo šanci
if last_selected_turn == current_turn:
    just_selected = -0.15  # Tento tah = penalizace
elif last_selected_turn == current_turn - 1:
    just_selected = -0.075  # Minulý tah = mírná penalizace
else:
    just_selected = 0
```

#### Anti-Repetition (anti_repetition.py)

Sleduje tři typy opakování:
1. **Fráze/slova** - opakující se klíčová slova v replikách
2. **Začátky replik** - detekce patternů jako "Ano, ...", "No, ...", "Jasně, ..."
3. **Témata** - volitelné sledování témat (zatím neimplementováno)

**Sledování začátků replik (NOVÉ):**
```python
# Extrahuje první slovo z repliky
_extract_start("Ano, máte pravdu.") -> "ano"

# Penalizace podle počtu opakování:
# 1x stejný začátek = 0.2 (mírná)
# 2x stejný začátek = 0.5 (střední -> downgrade_to_thought)
# 3x+ stejný začátek = 0.8 (vysoká -> reject)
```

**Pre-check:** Penalizace ve scoringu podle minulého opakování.

**Post-check:** Po AI odpovědi kontrola a případný downgrade.

**DŮLEŽITÉ - record_speech se volá POUZE pro finální speech:**
```python
# V _process_response:
if response.is_speech():
    # 1. HARD DUPLICATE CHECK - identický text jako minule?
    last_speech = _get_last_speech_by_npc(npc_id)
    if normalize(response.text) == normalize(last_speech):
        -> downgrade na ACTION, BEZ record_speech

    # 2. Anti-rep check (proti stávající historii)
    rejection_action = anti_rep.get_rejection_action(npc_id, text)
    if rejection_action != "accept":
        -> downgrade/reject, BEZ record_speech

    # 3. AŽ TADY (finální speech) se volá record_speech
    anti_rep.record_speech(npc_id, text)
```
Tím se nezanáší anti-repetition tracker downgraded/rejected replikami.

```python
def get_rejection_action(npc_id, proposed_text) -> str:
    penalty = get_penalty(npc_id, proposed_text)
    if penalty < 0.4:   return "accept"
    elif penalty < 0.6: return "downgrade_to_thought"
    elif penalty < 0.8: return "downgrade_to_action"
    else:               return "reject"  # Změna na NOTHING
```

Při downgrade na action se použije generická akce:
```python
generic_actions = [
    "Podívá se na moře.",
    "Zamyšleně přikývne.",
    "Pozoruje okolí.",
    "Pousměje se.",
]
```

#### SceneContext - aktivita vs ticho

```python
on_speech()   # Velká aktivita - reset silence i inactivity, energy +0.1
on_action()   # Střední aktivita - reset inactivity, energy +0.03
on_thought()  # Malá aktivita - reset inactivity, energy +0.01
on_nothing()  # Žádná aktivita - silence++, inactivity++, energy -0.07

def is_dying() -> bool:
    # Scéna umírá při inaktivitě, ne při pouhém tichu!
    return consecutive_inactivity >= 2 and scene_energy < 0.15
```

#### ASSISTED mód

Když scéna "umírá", engine nabídne **měkké impulsy** (ne příkazy):
- "Napadá tě něco... Ale klidně můžeš i mlčet."
- "Možná by ses mohl/a na něco zeptat - ale jen pokud tě to zajímá."
- "Přemýšlíš o něčem... Nebo možná jen pozoruješ okolí."

#### GOODBYE logika

GOODBYE **není v promptu pro AI** - odchody jsou řízeny čistě stay_drive:
- stay_drive klesá při mrtvé scéně, dlouhém tichu, nízké energii
- Když stay_drive <= 0.1, NPC chce odejít
- Detekce loučení v textu (heuristika) nastaví stay_drive = 0

#### DEV_INTENT_LOG

Globální seznam pro debug:
```python
DEV_INTENT_LOG: List[IntentLogEntry] = []
# Loguje: START_SCENE, END_SCENE, WORLD_EVENT, NPC_SCORE, AI_CALL, AI_RESPONSE
# Nově: ANTI_REP_REJECT, ANTI_REP_DOWNGRADE, ASSISTED_INSTRUCTION
```

---

### 4. Director (rules/director.py) - Fallback

Director se používá jako fallback pro jednoho NPC na lavičce nebo když je `USE_BEHAVIOR_ENGINE = False`.

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
RES_X, RES_Y = 1280, 720

# Automatický tah
AUTO_TAH_INTERVAL = 2.2  # sekundy

# Bublina
BUBLINA_MIN_TRVANI = 4.0
BUBLINA_RYCHLOST = 12    # znaků/sekunda

# Pravděpodobnosti
PRAVDEPODOBNOST_PRICHODU = 0.22
PRAVDEPODOBNOST_ODCHODU_SAM = 0.15
PRAVDEPODOBNOST_ODCHODU_PO_ROZHOVORU = 0.16
MIN_REPLIK_PRO_ODCHOD = 16

# Ticho
TICHO_SAM = 0.88  # šance že NPC sám mlčí

# === BEHAVIOR ENGINE ===
USE_BEHAVIOR_ENGINE = True      # True = nový engine, False = starý Director
BEHAVIOR_ENGINE_TOP_K = 1       # Kolik NPC jde do AI za tah
BEHAVIOR_COOLDOWN_SPEECH = 1    # Cooldown po promluvení (tahy)
BEHAVIOR_ENERGY_COST_SPEECH = 0.15  # Spotřeba energie za mluvení
BEHAVIOR_ENERGY_REGEN_TURN = 0.05   # Regenerace energie za tah
BEHAVIOR_MIN_SCORE_TO_SPEAK = 0.15  # Minimální skóre pro mluvení
DEV_INTENT_LOG_ENABLED = True   # Detailní logování enginu
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

### 3. NPC autonomie (Behavior Engine)

NPC **rozhodují sami**:
- Engine generuje jen WorldEvent (STIMULUS/PRESSURE/SILENCE)
- NPC volí typ odpovědi (speech/thought/action/nothing)
- Vnitřní stavy (energy, drive, cooldown) ovlivňují chování
- Anti-repetition brání opakování

### 4. Adaptivní Director (fallback)

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

- [x] Behavior Engine v1 - NPC rozhodují sami
- [ ] Více archetypů postav
- [ ] Denní/noční cyklus
- [ ] Zvukové efekty
- [ ] Více laviček (více scén současně)
- [ ] Web interface místo pygame
