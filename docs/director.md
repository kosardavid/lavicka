# Director - Režisér scény

## Přehled

Director je "režisér scény" - sleduje průběh rozhovoru a jemně ho koriguje.
Není to tvrdý plánovač, ale **adaptivní pozorovatel a našeptávač**.

## Princip fungování

1. **Průběžně sleduje** stav scény (ne rigidní plán dopředu)
2. **Jemně navádí** AI pomocí hintů v intentu
3. **Adaptuje se** na nečekaný vývoj
4. **Nikdy nenutí** - jen upravuje parametry

---

## Stav scény (SceneState)

```python
@dataclass
class SceneState:
    phase: str           # "intro" | "developing" | "peak" | "closing"
    energy: float        # 0.0-1.0, jak "živá" je scéna
    speech_count: int    # kolik replik proběhlo
    estimated_length: int  # odhad celkové délky
    trajectory: str      # "casual" | "deep" | "conflict" | "quiet"
    start_time: float    # kdy scéna začala
    last_speech_time: float  # kdy byla poslední replika
```

### Fáze scény

| Fáze | Popis | Typický intent |
|------|-------|----------------|
| `intro` | Začátek, oťukávání | "Právě přišel, oťukává situaci" |
| `developing` | Rozvoj tématu | volný průběh |
| `peak` | Vrchol rozhovoru | "Rozhovor je v plném proudu" |
| `closing` | Směřování k závěru | "Pomalu směřuje k rozloučení" |

### Trajektorie

| Trajektorie | Délka | Charakter |
|-------------|-------|-----------|
| `casual` | 8-16 replik | Lehký, příjemný rozhovor |
| `deep` | 14-25 replik | Osobní téma, emoce |
| `conflict` | 6-12 replik | Napětí, kratší |
| `quiet` | 5-10 replik | Málo slov, sdílené ticho |

---

## Dynamický výpočet trajektorie

### Žádná hardcoded matice

Dříve byla trajektorie určena statickou maticí `ARCHETYPE_COMPATIBILITY` která mapovala dvojice NPC na pravděpodobnosti. To bylo **odstraněno** protože:
- Vyžadovalo ruční přidávání každé nové kombinace
- Neškálovalo s přidáváním nových NPC

### Nový přístup: povahové rysy

Každé NPC má v `postavy.json` atribut `povaha`:

```json
"povaha": {
  "konfliktnost": 0.1,   // 0.0-1.0
  "hloubavost": 0.5,     // 0.0-1.0
  "mluvnost": 0.6        // 0.0-1.0
}
```

### Výpočet kompatibility

```python
def _compute_compatibility(npc_a: dict, npc_b: dict) -> tuple:
    """
    Dynamicky vypočítá kompatibilitu dvou NPC z jejich povah.

    Returns:
        (šance_casual, šance_deep, šance_conflict, šance_quiet)
    """
    # Získej povahy
    povaha_a = npc_a.get("povaha", {})
    povaha_b = npc_b.get("povaha", {})

    # Průměry obou NPC
    konfliktnost = (povaha_a.get("konfliktnost", 0.2) + povaha_b.get("konfliktnost", 0.2)) / 2
    hloubavost = (povaha_a.get("hloubavost", 0.3) + povaha_b.get("hloubavost", 0.3)) / 2
    mluvnost = (povaha_a.get("mluvnost", 0.5) + povaha_b.get("mluvnost", 0.5)) / 2

    # Výpočet šancí
    conflict = konfliktnost * 0.8    # vysoká konfliktnost = více konfliktů
    deep = hloubavost * 0.6          # vysoká hloubavost = hlubší rozhovory
    quiet = (1 - mluvnost) * 0.5     # nízká mluvnost = tišší
    casual = max(0.2, 1.0 - conflict - deep - quiet)  # zbytek

    # Normalizace na součet 1.0
    total = casual + deep + conflict + quiet
    return (casual / total, deep / total, conflict / total, quiet / total)
```

### Příklady výsledků

| NPC A | NPC B | Výsledek |
|-------|-------|----------|
| Babička (konfl=0.1, hloub=0.5) | Dělník (konfl=0.2, hloub=0.2) | casual 50%, deep 20%, conflict 12%, quiet 18% |
| Rebelka (konfl=0.5, hloub=0.3) | Manažer (konfl=0.3, hloub=0.4) | casual 30%, deep 21%, conflict 32%, quiet 17% |
| Bezdomovec (konfl=0.1, hloub=0.8) | Babička (konfl=0.1, hloub=0.5) | casual 35%, deep 39%, conflict 8%, quiet 18% |

---

## Komunikace s AI

Director **nepřikazuje**, ale dává **jemné hinty** v intentu NPC.

### Intenty podle fáze a rodu

```python
PHASE_INTENTS = {
    "intro": [
        {"m": "Právě přišel, oťukává situaci.", "f": "Právě přišla, oťukává situaci."},
        {"m": "Zkoumá, kdo vedle něj sedí.", "f": "Zkoumá, kdo vedle ní sedí."},
        {"m": "Váhá, jestli začít rozhovor.", "f": "Váhá, jestli začít rozhovor."},
    ],
    "developing": [
        {"m": "", "f": ""},  # volný průběh
        {"m": "Rozhovor plyne přirozeně.", "f": "Rozhovor plyne přirozeně."},
    ],
    "peak": [
        {"m": "Rozhovor je v plném proudu.", "f": "Rozhovor je v plném proudu."},
        {"m": "Téma ho opravdu zajímá.", "f": "Téma ji opravdu zajímá."},
    ],
    "peak_conflict": [
        {"m": "Cítí napětí v rozhovoru.", "f": "Cítí napětí v rozhovoru."},
        {"m": "Nesouhlasí s názorem druhého.", "f": "Nesouhlasí s názorem druhého."},
    ],
    "closing": [
        {"m": "Pomalu směřuje k rozloučení.", "f": "Pomalu směřuje k rozloučení."},
        {"m": "Cítí, že je čas jít.", "f": "Cítí, že je čas jít."},
        {"m": "Chce rozhovor hezky uzavřít.", "f": "Chce rozhovor hezky uzavřít."},
    ],
}
```

Výběr intentu:
```python
def get_intent(self, npc: dict) -> str:
    rod = npc.get("rod", "muž")
    intent_dict = random.choice(PHASE_INTENTS[self.state.phase])

    if rod == "žena":
        return intent_dict.get("f", intent_dict.get("m", ""))
    return intent_dict.get("m", "")
```

---

## Adaptace na vývoj

Director sleduje **signály z AI odpovědí**:

### Detekce sentimentu

```python
CONFLICT_KEYWORDS = [
    "ne,", "ne.", "nesouhlasím", "to není pravda", "ale", "jenže",
    "nemyslím", "nesmysl", "blbost", "hloupost",
]

POSITIVE_KEYWORDS = [
    "ano", "souhlasím", "máte pravdu", "zajímavé", "hezké", "příjemné",
]

CLOSING_KEYWORDS = [
    "musím jít", "budu muset", "bylo příjemné", "na shledanou",
    "měl/a jsem", "děkuji za", "sbohem",
]
```

### Pravidla adaptace

1. **AI eskaluje konflikt** → Director přepne na `conflict`, zkrátí scénu
2. **Příjemnější než čekal** → může prodloužit
3. **Detekuje closing keywords** → přejde do `closing` fáze
4. **Scéna "umírá"** (krátké odpovědi) → sníží `energy`, možná ukončí

---

## Události prostředí

### Automatické události

Director může navrhnout automatickou událost v některých situacích:

```python
AUTO_EVENTS_IMPULSE = [
    "Kolem proletěl racek.",
    "Od moře zafoukal vítr.",
    "Někde v dálce zahoukal parník.",
    "Na lavičku dopadl list.",
    "Přeběhla kolem kočka.",
]
```

### Kdy se navrhují

- Ve fázi `developing` s nízkou pravděpodobností (pro oživení)
- Ve fázi `peak` mohou být dramatičtější
- Při dlouhém tichu jako impuls k rozhovoru

---

## Dynamické reakce na události

Reakce NPC na události jsou také dynamické podle jejich `konfliktnost`:

```python
def plan_event_reaction(self, event: str, npc: dict) -> dict:
    povaha = npc.get("povaha", {})
    konfliktnost = povaha.get("konfliktnost", 0.2)

    # Hrubost/konflikt
    if "hrub" in event.lower():
        if konfliktnost > 0.4:
            instruction = "Reaguj podrážděně nebo ironicky na hrubé chování."
        elif konfliktnost < 0.2:
            instruction = "Buď překvapený/á a trochu zraněný/á hrubostí."
        else:
            instruction = "Reaguj přirozeně na hrubé chování vedle tebe."

    return {"should_react": True, "instruction": instruction}
```

---

## API Directora

```python
class Director:
    def __init__(self):
        self.state: Optional[SceneState] = None
        self._logger: DirectorLogger

    def start_scene(self, npc_a: dict, npc_b: dict, relationship=None) -> None:
        """Inicializuje novou scénu když se sejdou dva NPC."""
        trajectory = self._determine_trajectory(npc_a, npc_b, relationship)
        estimated_length = self._get_estimated_length(trajectory)
        self.state = SceneState(
            phase="intro",
            trajectory=trajectory,
            estimated_length=estimated_length,
            ...
        )

    def observe(self, response: dict) -> None:
        """Sleduje odpověď AI a aktualizuje stav."""
        self.state.speech_count += 1
        self._update_energy(response)
        self._check_for_sentiment(response)
        self.update_phase()

    def update_phase(self) -> None:
        """Přepočítá fázi na základě speech_count."""
        progress = self.state.speech_count / self.state.estimated_length
        if progress < 0.2:
            self.state.phase = "intro"
        elif progress < 0.6:
            self.state.phase = "developing"
        elif progress < 0.85:
            self.state.phase = "peak"
        else:
            self.state.phase = "closing"

    def get_intent(self, npc: dict) -> str:
        """Vrátí hint pro AI prompt podle aktuální fáze a rodu."""

    def should_end(self) -> bool:
        """True když je čas na odchod některého NPC."""
        if self.state.phase == "closing":
            return self.state.speech_count >= self.state.estimated_length

    def suggest_event(self) -> Optional[str]:
        """Návrh automatické události (nebo None)."""

    def end_scene(self) -> None:
        """Ukončí scénu, reset stavu."""
        self.state = None

    def plan_event_reaction(self, event: str, npc: dict) -> dict:
        """Naplánuje reakci NPC na událost."""
```

---

## Integrace do app.py

```python
# V LavickaApp.__init__
self.director = Director()

# Při příchodu druhého NPC
if self.sedadla[0] and self.sedadla[1]:
    self.director.start_scene(
        self.sedadla[0],
        self.sedadla[1],
        self.relationships.get(...)
    )

# V tah()
if resp:
    self.director.observe(resp)

# Intent pro AI
npc["intent"] = self.director.get_intent(npc)

# Rozhodnutí o odchodu
if self.director.should_end():
    npc["chce_odejit"] = True

# Automatická událost
auto_event = self.director.suggest_event()
if auto_event:
    self.add_environment_event(auto_event)
```

---

## Designové principy

### 1. Žádný hardcoded kód

- Trajektorie se počítají dynamicky z `povaha`
- Reakce na události závisí na `konfliktnost`
- Intenty jsou parametrizované podle `rod`

### 2. Plně rozšiřitelné

Přidání nového NPC vyžaduje pouze:
1. Přidat záznam do `postavy.json`
2. Definovat `povaha` s třemi atributy

Director automaticky:
- Vypočítá trajektorie s ostatními NPC
- Přizpůsobí reakce na události
- Vybere správně skloněné intenty

### 3. Adaptivní, ne direktivní

Director **navádí**, ne **přikazuje**:
- Sleduje vývoj rozhovoru
- Dává jemné hinty
- Adaptuje se na nečekaný vývoj
- Ukončuje scény přirozeně
