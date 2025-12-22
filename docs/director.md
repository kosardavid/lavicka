# Director - Návrh systému

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
    estimated_remaining: int  # odhad kolik ještě zbývá
    trajectory: str      # "casual" | "deep" | "conflict" | "quiet"
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
| `casual` | 6-10 replik | Lehký, příjemný rozhovor |
| `deep` | 12-20 replik | Osobní téma, emoce |
| `conflict` | 5-8 replik | Napětí, kratší |
| `quiet` | 3-5 replik | Málo slov, sdílené ticho |

---

## Určení směru scény

### Faktory s váhami

| Faktor | Vliv | Popis |
|--------|------|-------|
| Archetypy | 40% | Kombinace postav určuje tendenci |
| Vztah/paměť | 30% | Známí delší, po konfliktu opatrnost |
| Náhoda | 30% | Nepředvídatelnost |

### Kompatibilita archetypů (příklady)

```
Pesimista + Optimista → conflict (60%) | deep (40%)
Důchodce + Dítě → casual, krátké
Umělec + Umělec → deep, delší
Podnikatel + Důchodce → casual | conflict
```

---

## Komunikace s AI

Director **nepřikazuje**, ale dává **jemné hinty** v intentu NPC:

### Příklady intentů podle fáze

```python
PHASE_INTENTS = {
    "intro": [
        "Právě přišel, oťukává situaci.",
        "Zkoumá, kdo vedle něj sedí.",
        "Váhá, jestli začít rozhovor.",
    ],
    "developing": [
        "",  # volný průběh
        "Rozhovor plyne přirozeně.",
    ],
    "peak": [
        "Rozhovor je v plném proudu.",
        "Téma ho opravdu zajímá.",
        "Cítí napětí v rozhovoru.",  # pro conflict
    ],
    "closing": [
        "Pomalu směřuje k rozloučení.",
        "Cítí, že je čas jít.",
        "Chce rozhovor uzavřít.",
    ],
}
```

---

## Adaptace na vývoj

Director sleduje **signály z AI odpovědí**:

### Detekce sentimentu (jednoduché)

```python
CONFLICT_KEYWORDS = ["ne", "nesouhlasím", "to není", "ale", "jenže"]
POSITIVE_KEYWORDS = ["ano", "souhlasím", "máte pravdu", "zajímavé"]
CLOSING_KEYWORDS = ["musím jít", "bylo mi", "na shledanou", "sbohem"]
```

### Pravidla adaptace

1. **AI eskaluje konflikt** → Director přepne na `conflict`, zkrátí scénu
2. **Příjemnější než čekal** → může prodloužit
3. **Detekuje closing keywords** → přejde do `closing` fáze
4. **Scéna "umírá"** (krátké odpovědi) → sníží `energy`, možná ukončí

---

## Události prostředí

### Hybridní přístup

1. **Manuální eventy** (od uživatele) mají vždy prioritu
2. **Automatické návrhy** s nízkou pravděpodobností (15-20%):
   - Scéna "umírá" → malá událost jako impuls
   - Blíží se peak → možná dramatičtější událost
   - Dlouhé ticho → něco se stane

### Typy automatických událostí

```python
AUTO_EVENTS = {
    "impulse": [  # pro oživení
        "Kolem proletěl racek.",
        "Od moře zafoukal vítr.",
        "Někde v dálce zahoukal parník.",
    ],
    "dramatic": [  # pro peak
        "Začalo poprchávat.",
        "Kolem proběhlo dítě s míčem.",
        "Na lavičku dopadl list.",
    ],
}
```

---

## API Directora

```python
class Director:
    def __init__(self):
        self.state: Optional[SceneState] = None
        self.archetype_matrix: dict  # kompatibilita archetypů

    def start_scene(self, npc_a: dict, npc_b: dict, relationship) -> None:
        """Inicializuje novou scénu když se sejdou dva NPC."""

    def observe(self, response: dict) -> None:
        """Sleduje odpověď AI a aktualizuje stav."""

    def update_phase(self) -> None:
        """Přepočítá fázi na základě speech_count a signálů."""

    def get_intent(self, npc: dict) -> str:
        """Vrátí hint pro AI prompt podle aktuální fáze."""

    def should_end(self) -> bool:
        """True když je čas na odchod některého NPC."""

    def suggest_event(self) -> Optional[str]:
        """Návrh automatické události (nebo None)."""

    def end_scene(self) -> None:
        """Ukončí scénu, reset stavu."""
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

## Budoucí rozšíření

- [ ] Učení z historie - které kombinace fungovaly dobře
- [ ] Složitější sentiment analýza
- [ ] Víc typů trajektorií
- [ ] Události závislé na archetypu (umělec reaguje jinak na racka)
