"""
Hybrid unit selection (Fase 1 roadmap TTS, lihat README.md): untuk tiap kata
dalam teks, coba urutan prioritas berikut sebelum menyerah --

    1. Rekaman utuh untuk kata itu sendiri (exact match)
    2. Rekaman per suku kata (hasil FsaSyllableService/syllable_splitter)
    3. Rekaman per huruf, kalau satu suku kata tertentu belum direkam
    4. Gagal (MissingAudioUnitsError) -- TIDAK menghasilkan audio parsial
       yang diam-diam bolong, karena itu lebih menyesatkan daripada error
       yang jelas.

Modul ini murni logika seleksi (tidak menyentuh jaringan/audio sama sekali)
supaya gampang diuji lewat kombinasi unit yang tersedia/tidak tersedia --
lihat tests/test_unit_selector.py.
"""

from __future__ import annotations

from app.exceptions import MissingAudioUnitsError
from app.schemas import PlanItem, SynthesisPlan, UnitInfo
from app.services.syllable_splitter import split_syllables_list
from app.services.text_normalizer import normalize_diacritics, tokenize_words


def select_units(text: str, available: dict[str, UnitInfo]) -> SynthesisPlan:
    """
    `available` adalah pemetaan teks unit (sudah dinormalisasi diakritiknya,
    lihat recording_repository.py) -> UnitInfo. `text` idealnya juga sudah
    dinormalisasi oleh pemanggil, tapi dinormalisasi ulang di sini supaya
    fungsi ini tetap aman dipanggil sendiri (mis. dari test).
    """
    normalized = normalize_diacritics(text)
    tokens = tokenize_words(normalized)

    if not tokens:
        return SynthesisPlan(items=[])

    plan_items: list[PlanItem] = []
    missing_segments: list[str] = []

    for token in tokens:
        token_items, token_missing = _resolve_token(token, available)
        if token_missing:
            missing_segments.extend(token_missing)
        else:
            plan_items.extend(token_items)

    if missing_segments:
        raise MissingAudioUnitsError(missing_segments)

    return SynthesisPlan(items=plan_items)


def _resolve_token(token: str, available: dict[str, UnitInfo]) -> tuple[list[PlanItem], list[str]]:
    # 1. Exact match untuk seluruh kata.
    if token in available:
        return [PlanItem(segment=token, audio_url=available[token].audio_url)], []

    # 2 & 3. Per suku kata, dengan fallback ke huruf kalau satu suku kata
    # tertentu belum ada rekamannya sendiri.
    syllables = split_syllables_list(token)
    items: list[PlanItem] = []
    missing: list[str] = []

    for syllable in syllables:
        if syllable in available:
            items.append(PlanItem(segment=syllable, audio_url=available[syllable].audio_url))
            continue

        letter_items, letters_missing = _resolve_letters(syllable, available)
        if letters_missing:
            missing.append(syllable)
        else:
            items.extend(letter_items)

    return items, missing


def _resolve_letters(syllable: str, available: dict[str, UnitInfo]) -> tuple[list[PlanItem], list[str]]:
    items: list[PlanItem] = []
    for letter in syllable:
        if letter not in available:
            return [], [letter]
        items.append(PlanItem(segment=letter, audio_url=available[letter].audio_url))
    return items, []
