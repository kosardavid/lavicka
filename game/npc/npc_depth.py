"""
npc_depth.py - Výpočet allowed_depth pro NPC
==============================================

Tento modul implementuje KROK 3 a 5-6 z návrhu realistických rozhovorů.

Klíčový princip:
----------------
NPC nesmí mluvit hlouběji, než dovoluje kombinace:
1) closeness_level (vztah s partnerem)
2) osobnost NPC (openness, emotion_talk, privacy)
3) kontext (bench motive, tajemství)

I milenci (closeness 3) NESMÍ mluvit hluboce,
pokud to osobnost NPC nedovolí.

Mlčení je validní výstup - NPC nemusí nic říct.
Hlubší rozhovor není vždy možný a to je v pořádku.
"""

from typing import Optional


def _float_to_bucket(value: float) -> int:
    """
    Převede float 0-1 na bucket 1-3.

    Používá se pro openness a emotion_talk.

    Args:
        value: Float hodnota 0.0 - 1.0

    Returns:
        int: 1 (nízký), 2 (střední), 3 (vysoký)
    """
    if value < 0.35:
        return 1
    elif value < 0.65:
        return 2
    else:
        return 3


def _get_privacy_penalty(privacy: float) -> int:
    """
    Vypočítá penaltu za vysokou ochranu soukromí.

    Vysoká privacy (> 0.7) způsobí -1 k allowed_depth.

    Args:
        privacy: Float hodnota 0.0 - 1.0

    Returns:
        int: -1 nebo 0
    """
    return -1 if privacy > 0.7 else 0


def calculate_allowed_depth(
    closeness_level: int,
    social: dict,
) -> int:
    """
    Vypočítá maximální povolenou hloubku rozhovoru.

    Vzorec:
        allowed_depth = clamp(
            min(closeness_level, openness_bucket, emotion_bucket) + privacy_penalty,
            0, 3
        )

    Args:
        closeness_level: Stupeň blízkosti vztahu (0-3)
        social: Dict s klíči openness, emotion_talk, privacy

    Returns:
        int: 0-3 (povolená hloubka témat)
    """
    openness = social.get("openness", 0.5)
    emotion_talk = social.get("emotion_talk", 0.5)
    privacy = social.get("privacy", 0.5)

    # Převod na buckety
    openness_bucket = _float_to_bucket(openness)
    emotion_bucket = _float_to_bucket(emotion_talk)
    privacy_penalty = _get_privacy_penalty(privacy)

    # Výpočet - minimum ze všech faktorů + penalta
    base = min(closeness_level, openness_bucket, emotion_bucket)
    result = base + privacy_penalty

    # Clamp na 0-3
    return max(0, min(3, result))


def filter_topics_by_depth(
    topics: list,
    allowed_depth: int,
) -> tuple:
    """
    Rozdělí témata na povolená a zakázaná podle hloubky.

    Každé téma (hobby, fear) má share_level.
    Povolená jsou témata se share_level <= allowed_depth.

    Args:
        topics: Seznam dict s klíčem "share_level" a "tag"
        allowed_depth: Maximální povolená hloubka (0-3)

    Returns:
        tuple: (allowed_tags, forbidden_tags)
    """
    allowed = []
    forbidden = []

    for topic in topics:
        tag = topic.get("tag", "")
        share_level = topic.get("share_level", 0)

        if share_level <= allowed_depth:
            allowed.append(tag)
        else:
            forbidden.append(tag)

    return (allowed, forbidden)


def filter_secrets(
    secrets: list,
    closeness_level: int,
    scene_state: Optional[str] = None,
) -> tuple:
    """
    Rozdělí tajemství podle policy (KROK 5).

    Policy typy:
    - never_share: nikdy ve speech
    - share_if_intimacy: jen pokud closeness_level >= min_intimacy
    - share_only_if_breakpoint: jen pokud scene_state je goodbye/leaving/conflict_peak

    DŮLEŽITÉ: Tajemství NEMUSÍ být nikdy sdíleno.
    Neexistuje povinnost "vyzpovídat" NPC.

    Args:
        secrets: Seznam tajemství z archetypu
        closeness_level: Aktuální stupeň blízkosti (0-3)
        scene_state: Aktuální stav scény (goodbye, leaving, conflict_peak, ...)

    Returns:
        tuple: (shareable_secrets, forbidden_secrets)
    """
    shareable = []
    forbidden = []

    breakpoint_states = {"goodbye", "leaving", "conflict_peak"}
    is_breakpoint = scene_state in breakpoint_states if scene_state else False

    for secret in secrets:
        tag = secret.get("tag", "")
        policy = secret.get("policy", "never_share")

        if policy == "never_share":
            # Nikdy nesdílet
            forbidden.append(tag)

        elif policy == "share_if_intimacy":
            # Sdílet jen při dostatečné blízkosti
            min_intimacy = secret.get("min_intimacy", 3)
            if closeness_level >= min_intimacy:
                shareable.append(tag)
            else:
                forbidden.append(tag)

        elif policy == "share_only_if_breakpoint":
            # Sdílet jen v klíčových momentech scény
            if is_breakpoint:
                shareable.append(tag)
            else:
                forbidden.append(tag)

        else:
            # Neznámá policy = nepovoleno
            forbidden.append(tag)

    return (shareable, forbidden)


def get_bench_motive_instruction(
    bench: dict,
    allowed_depth: int,
) -> str:
    """
    Vrátí instrukci pro AI ohledně důvodu lavičky (KROK 6).

    Pravidlo:
    - pokud allowed_depth < motive_share_level: jen náznak nebo thought
    - pokud >=: smí být řečeno jednou, krátce

    Důvod lavičky má ovlivňovat chování, ne být automaticky vyřčený.

    Args:
        bench: Dict s motive a motive_share_level
        allowed_depth: Maximální povolená hloubka (0-3)

    Returns:
        str: Instrukce pro prompt
    """
    motive = bench.get("motive", "resting")
    motive_share_level = bench.get("motive_share_level", 1)

    # Překlad motivů do češtiny pro vnitřní kontext
    motive_translations = {
        "resting": "odpočívám",
        "waiting": "čekám na někoho/něco",
        "escaping": "utíkám od něčeho",
        "thinking": "přemýšlím",
        "grieving": "truchlím",
        "peoplewatching": "pozoruji lidi",
    }
    motive_cz = motive_translations.get(motive, motive)

    if allowed_depth < motive_share_level:
        return f"""Důvod lavičky: {motive_cz} (VNITŘNÍ - nesdílej přímo).
Můžeš naznačit v chování, ale NEŘÍKEJ nahlas proč tu jsi."""
    else:
        return f"""Důvod lavičky: {motive_cz}.
Pokud to padne přirozeně, můžeš krátce zmínit - ale jen jednou, ne opakovaně."""


def build_depth_context(
    npc: dict,
    closeness_level: int,
    scene_state: Optional[str] = None,
) -> dict:
    """
    Sestaví kompletní kontext hloubky pro prompt builder.

    Kombinuje všechny výpočty do jednoho výstupu.

    Args:
        npc: Archetyp NPC (dict s social, hobbies, fears, secrets, bench)
        closeness_level: Stupeň blízkosti vztahu (0-3)
        scene_state: Aktuální stav scény (volitelné)

    Returns:
        dict s klíči:
            - closeness_level: int (0-3)
            - allowed_depth: int (0-3)
            - allowed_topics: list[str]
            - forbidden_topics: list[str]
            - shareable_secrets: list[str]
            - forbidden_secrets: list[str]
            - bench_instruction: str
    """
    social = npc.get("social", {})
    hobbies = npc.get("hobbies", [])
    fears = npc.get("fears", [])
    secrets = npc.get("secrets", [])
    bench = npc.get("bench", {})

    # Výpočet allowed_depth
    allowed_depth = calculate_allowed_depth(closeness_level, social)

    # Filtrování témat
    allowed_hobbies, forbidden_hobbies = filter_topics_by_depth(hobbies, allowed_depth)
    allowed_fears, forbidden_fears = filter_topics_by_depth(fears, allowed_depth)

    allowed_topics = allowed_hobbies + allowed_fears
    forbidden_topics = forbidden_hobbies + forbidden_fears

    # Tajemství
    shareable_secrets, forbidden_secrets = filter_secrets(
        secrets, closeness_level, scene_state
    )

    # Bench motive instrukce
    bench_instruction = get_bench_motive_instruction(bench, allowed_depth)

    return {
        "closeness_level": closeness_level,
        "allowed_depth": allowed_depth,
        "allowed_topics": allowed_topics,
        "forbidden_topics": forbidden_topics,
        "shareable_secrets": shareable_secrets,
        "forbidden_secrets": forbidden_secrets,
        "bench_instruction": bench_instruction,
    }
