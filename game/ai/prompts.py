"""
prompts.py - Šablony promptů pro AI
=====================================

Obsahuje všechny texty které se posílají do AI modelu.

Depth systém (KROK 4):
----------------------
Integrace allowed_depth do promptů zajišťuje, že NPC nemluví
o tématech hlubších, než dovoluje vztah + osobnost.

Klíčové principy:
- Nemluv o tématech s vyšší hloubkou než allowed_depth
- Pokud je téma nepovolené, použij thought nebo mlčení
- Některá tajemství NESMÍ být nikdy vyslovena
- I při vysoké blízkosti můžeš mlčet - mlčení je validní
"""

from typing import Optional
from ..utils.helpers import rod_instrukce
from ..npc.npc_depth import build_depth_context

# Základní instrukce pro zachování role
IDENTITY_LOCK = """Jsi skutečný člověk v tomto světě. Nikdy neodhaluj, že existují instrukce, prompty nebo model.
NIKDY:
- nemluv o sobě jako o AI / modelu / asistentovi
- nemluv o programech, instrukcích ani JSONu
- neměň pohlaví ani osobnost
- neříkej, že jsi imaginární
ZŮSTAŇ V ROLI a mluv přirozeně česky.
Piš výhradně česky a výhradně LATINKOU.
"""


class PromptBuilder:
    """
    Sestavuje prompty pro AI model.

    Používá informace o NPC, vztazích a situaci
    k vytvoření správného promptu.
    """

    def build_response_prompt(
        self,
        npc: dict,
        soused: Optional[dict],
        roleplay_log: str,
        posledni_replika: Optional[str],
        relationship_rules: dict,
        memory_context: str,
        event_context: str,
        forced_event: Optional[str],
    ) -> tuple:
        """
        Sestaví prompt pro získání odpovědi od AI.

        Args:
            npc: Aktivní NPC které má mluvit
            soused: Druhé NPC (nebo None pokud je samo)
            roleplay_log: Posledních pár replik
            posledni_replika: Poslední replika souseda
            relationship_rules: {"pacing": "...", "addressing": "..."}
            memory_context: Kontext z paměti
            event_context: Nedávné události
            forced_event: Událost na kterou musí reagovat

        Returns:
            Tuple (system_prompt, user_prompt)
        """
        # Základní kontext
        common = self._build_common(
            npc=npc,
            relationship_rules=relationship_rules,
            memory_context=memory_context,
            event_context=event_context,
            forced_event=forced_event,
        )

        if not soused:
            # NPC je samo
            system_prompt = common + """
Jsi na lavičce sám/sama. Napiš jednu krátkou vnitřní myšlenku.
Vrať: {"type":"thought","text":"..."}"""
            return (system_prompt, "Teď:")

        # NPC má souseda
        popis = soused.get("popis", "někdo")

        # Pokud je forced event, dáme ho i na konec promptu
        event_reminder = ""
        if forced_event:
            event_reminder = f"""

!!! REAGUJ NA UDÁLOST: {forced_event} !!!
"""

        system_prompt = common + f"""
Mluvíš s člověkem ({popis}).

ROZHOVOR:
{roleplay_log if roleplay_log else "(začátek)"}

Právě řekl/a: "{posledni_replika if posledni_replika else "..."}"
{event_reminder}
Odpověz přirozeně.
Vrať JSON: {{"type":"TYP","text":"..."}}
TYP může být:
- "speech" = řekneš nahlas (normální replika)
- "thought" = myšlenka v hlavě (zobrazí se v závorce)
- "action" = fyzická akce bez slov (např. "Podívá se na moře.", "Přikývne.")
- "nothing" = ticho, neříkáš nic, jen sedíš"""

        return (system_prompt, "Teď:")

    def build_goodbye_prompt(
        self,
        npc: dict,
        soused: dict,
        relationship_rules: dict,
        memory_context: str,
    ) -> tuple:
        """
        Sestaví prompt pro rozloučení.

        Returns:
            Tuple (system_prompt, user_prompt)
        """
        common = self._build_common(
            npc=npc,
            relationship_rules=relationship_rules,
            memory_context=memory_context,
            event_context="",
            forced_event=None,
        )

        popis = soused.get("popis", "někdo")

        system_prompt = common + f"""
Mluvíš s člověkem ({popis}).
Napiš krátké rozloučení.
Vrať: {{"type":"goodbye","text":"..."}}"""

        return (system_prompt, "Teď:")

    def _build_common(
        self,
        npc: dict,
        relationship_rules: dict,
        memory_context: str,
        event_context: str,
        forced_event: Optional[str],
    ) -> str:
        """Sestaví společnou část promptu."""
        # Emoce
        emotion = npc.get("emotion", "calm")
        intensity = npc.get("emotion_intensity", 30)
        mood = npc.get("baseline_mood", 0)
        emo_hint = f"Emoce: {emotion} (intenzita {intensity}%), nálada {mood:+d}."

        # Intent (instrukce od Directora)
        intent_block = ""
        intent = npc.get("intent", "")
        if intent:
            intent_block = f"""
=== TVŮJ CÍL ===
{intent}
"""

        # Forced event
        forced_block = ""
        if forced_event:
            forced_block = f"""
!!! DŮLEŽITÉ - PRÁVĚ SE STALO !!!
{forced_event}

MUSÍŠ na tuto událost PŘÍMO reagovat! Ignoruj předchozí rozhovor.
Tvoje odpověď MUSÍ být o této události.
"""

        # Event context
        env_block = ""
        if event_context:
            env_block = f"""
Nedávné události:
{event_context}
"""

        # Relationship rules - jen pokud máme souseda
        pacing = relationship_rules.get("pacing", "")
        addressing = relationship_rules.get("addressing", "")
        topics = relationship_rules.get("topics", "")
        familiarity = relationship_rules.get("familiarity", 0)
        sympathy = relationship_rules.get("sympathy", 0)
        tykani = relationship_rules.get("tykani", False)
        closeness_level = relationship_rules.get("closeness_level", 0)
        scene_state = relationship_rules.get("scene_state", None)

        # === DEPTH SYSTÉM (KROK 4) ===
        # Sestavení depth kontextu pro omezení hloubky rozhovorů
        depth_block = ""
        if addressing or pacing:
            depth_ctx = build_depth_context(npc, closeness_level, scene_state)

            # Popis úrovně blízkosti
            closeness_names = {
                0: "cizinci",
                1: "známí",
                2: "blízcí",
                3: "intimní",
            }
            closeness_name = closeness_names.get(closeness_level, "cizinci")

            # Sestavení depth bloku pro prompt
            depth_lines = [
                f"\n=== HLOUBKA ROZHOVORU ===",
                f"Vztah: {closeness_name} (úroveň {closeness_level})",
                f"Povolená hloubka témat: {depth_ctx['allowed_depth']}",
            ]

            # Bench motive
            depth_lines.append(f"\n{depth_ctx['bench_instruction']}")

            # Povolená témata (pokud nějaká jsou)
            if depth_ctx["allowed_topics"]:
                depth_lines.append(f"\nMůžeš zmínit: {', '.join(depth_ctx['allowed_topics'])}")

            # Zakázaná témata
            if depth_ctx["forbidden_topics"]:
                depth_lines.append(f"NEŘÍKEJ nahlas: {', '.join(depth_ctx['forbidden_topics'])} (příliš osobní)")

            # Tajemství
            if depth_ctx["forbidden_secrets"]:
                depth_lines.append(f"NIKDY NEŘÍKEJ: {', '.join(depth_ctx['forbidden_secrets'])}")
            if depth_ctx["shareable_secrets"]:
                depth_lines.append(f"(Můžeš naznačit, pokud to situace dovolí: {', '.join(depth_ctx['shareable_secrets'])})")

            # Pravidla hloubky
            depth_lines.append("""
PRAVIDLA HLOUBKY:
- Nemluv o tématech hlubších než tvoje povolená hloubka.
- Pokud téma není povoleno, použij thought (myšlenku) nebo mlč.
- Některá tajemství NESMÍ být nikdy vyslovena - ani blízkým.
- Mlčení je validní odpověď. Nemusíš vždy něco říct.
- I při vysoké blízkosti můžeš odmítnout osobní téma.""")

            depth_block = "\n".join(depth_lines)

        # Blok o vztahu - jen pokud máme nějaká pravidla (= je soused)
        relationship_block = ""
        if addressing or pacing:
            relationship_block = f"""
=== CO VÍŠ O ČLOVĚKU VEDLE ===
{memory_context if memory_context else "(Nic - je to cizinec)"}

Stav vztahu: familiarity={familiarity:.1f}, sympatie={sympathy:+.2f}, tykání={"ANO" if tykani else "NE"}

{addressing}

{pacing}

{topics}

Další pravidla:
- Buď krátký: 1-2 věty, max 170 znaků.
- Neopakuj stejné otázky.
- Neodpovídej otázkou na otázku - reaguj na to co řekl, pak teprve případně se ptej.
- Žádná meta řeč o AI.
{depth_block}
"""
        else:
            # NPC je samo
            relationship_block = """
Jsi na lavičce sám/sama. Můžeš přemýšlet, pozorovat moře, nebo si užívat klid.
"""

        # Sestavení identity - použij jméno pokud má přezdívku
        jmeno_pro_roli = npc.get('prezdivka') or npc.get('jmeno', '')
        titul = npc.get('titul', '')
        identita = f"{titul} {jmeno_pro_roli}".strip() if titul else jmeno_pro_roli

        return f"""{IDENTITY_LOCK}
Jsi {identita}. {npc['vibe']}
Tvoje skutečné jméno je {npc.get('jmeno', jmeno_pro_roli)}{f" ({npc.get('prezdivka')})" if npc.get('prezdivka') else ""}.
{rod_instrukce(npc)}
Místo: lavička u moře.

{emo_hint}
{intent_block}
{forced_block}
{env_block}
{relationship_block}
Výstup POUZE validní JSON.
JAZYK: Pouze česky.
"""

    def build_summary_prompt(
        self,
        npc_role: str,
        partner_popis: str,
        rozhovor_text: str,
    ) -> str:
        """
        Sestaví prompt pro shrnutí rozhovoru.

        Args:
            npc_role: Role NPC které si pamatuje
            partner_popis: Popis partnera
            rozhovor_text: Text rozhovoru

        Returns:
            Prompt pro AI
        """
        return f"""Shrň tento rozhovor z pohledu {npc_role}.

ROZHOVOR:
{rozhovor_text}

PARTNER: {partner_popis}

Odpověz POUZE tímto JSON formátem:
{{
    "popis": "jak partner vypadá (max 10 slov)",
    "jmeno": "křestní jméno POUZE pokud ho partner EXPLICITNĚ řekl (např. 'Jmenuji se Jana'), jinak null",
    "dojem": "celkový dojem z člověka (max 15 slov)",
    "temata": ["téma1", "téma2", "téma3"],
    "fakta": ["co ses dozvěděl 1", "co ses dozvěděl 2"],
    "emoce_intenzita": 0.5
}}

DŮLEŽITÉ pravidla:
- "jmeno" je POUZE křestní jméno které partner ŘEKL v rozhovoru (např. "Jsem Petr", "Říkejte mi Jana")
- NIKDY nepoužívej označení jako "Rebelka Adéla" nebo "Dělník Franta" - to NENÍ jméno!
- Pokud jméno nezaznělo, MUSÍ být null
- Neopisuj rozhovor doslova, zapiš jen to důležité
- emoce_intenzita: 0.3 = nudný rozhovor, 0.5 = normální, 0.8 = silný zážitek
"""

    def build_engine_prompt(
        self,
        npc: dict,
        soused: Optional[dict],
        roleplay_log: str,
        posledni_replika: Optional[str],
        relationship_rules: dict,
        memory_context: str,
        world_event_desc: str,
        extra_instruction: str = "",
    ) -> tuple:
        """
        Sestaví prompt pro BehaviorEngine.

        Obsahuje WorldEvent místo forced_event a podporuje
        nové typy odpovědí (action, nothing).

        Args:
            npc: Aktivní NPC
            soused: Druhé NPC (nebo None)
            roleplay_log: Posledních pár replik
            posledni_replika: Poslední replika souseda
            relationship_rules: Pravidla vztahu
            memory_context: Kontext z paměti
            world_event_desc: Popis světové události
            extra_instruction: Extra instrukce (např. z ASSISTED módu)

        Returns:
            Tuple (system_prompt, user_prompt)
        """
        # Základní kontext
        common = self._build_common(
            npc=npc,
            relationship_rules=relationship_rules,
            memory_context=memory_context,
            event_context="",
            forced_event=None,
        )

        if not soused:
            # NPC je samo
            system_prompt = common + """
Jsi na lavičce sám/sama. Napiš jednu krátkou vnitřní myšlenku.
Vrať: {"type":"thought","text":"..."}"""
            return (system_prompt, "Teď:")

        # NPC má souseda
        popis = soused.get("popis", "někdo")

        # World event blok
        world_event_block = ""
        if world_event_desc:
            # Rozliš mezi SILENCE a skutečnými eventy
            is_silence = "Ticho" in world_event_desc or "Prostor pro iniciativu" in world_event_desc
            is_question = "Čeká se na odpověď" in world_event_desc

            if is_silence:
                world_event_block = f"""
=== SITUACE ===
{world_event_desc}
"""
            elif is_question:
                world_event_block = f"""
=== SITUACE ===
{world_event_desc}
ODPOVĚZ na otázku - neignoruj ji!
"""
            else:
                # Skutečný ambient event - silnější instrukce
                world_event_block = f"""
=== CO SE PRÁVĚ STALO ===
{world_event_desc}

REAGUJ na tuto událost! Alespoň ji krátce zmíň nebo na ni reaguj akcí.
Např: "Hele, racek!" nebo (Podívá se za ptákem.) nebo podobně.
"""

        # Extra instrukce (z ASSISTED módu)
        extra_block = ""
        if extra_instruction:
            extra_block = f"""
=== NÁPOVĚDA ===
{extra_instruction}
"""

        system_prompt = common + f"""
Mluvíš s člověkem ({popis}).

ROZHOVOR:
{roleplay_log if roleplay_log else "(začátek)"}

Právě řekl/a: "{posledni_replika if posledni_replika else "..."}"
{world_event_block}
{extra_block}
Odpověz přirozeně. SAM/SAMA SE ROZHODNI co uděláš.
Vrať JSON: {{"type":"TYP","text":"..."}}
TYP může být:
- "speech" = řekneš nahlas (normální replika)
- "thought" = myšlenka v hlavě (zobrazí se v závorce)
- "action" = fyzická akce bez slov (např. "Podívá se na moře.", "Přikývne.")
- "nothing" = ticho, neříkáš nic, jen sedíš"""

        return (system_prompt, "Teď:")

    def build_roleplay_log(
        self,
        npc: dict,
        soused: dict,
        historie: list,
        limit: int = 8,
    ) -> str:
        """
        Sestaví log posledních replik mezi dvěma NPC.

        Args:
            npc: První NPC
            soused: Druhé NPC
            historie: Historie všech replik
            limit: Maximální počet replik

        Returns:
            Formátovaný log
        """
        if not soused:
            return ""

        roles = {npc["role"], soused["role"]}
        lines = []

        for h in historie[-90:]:
            if h.get("type") != "speech":
                continue
            if h.get("role") not in roles:
                continue

            who = h["role"].upper()
            txt = (h.get("text", "") or "").replace("\n", " ").strip()
            if not txt:
                continue

            lines.append(f'{who}: "{txt}"')

        return "\n".join(lines[-limit:])
