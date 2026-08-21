"""
Hybrid unit selection (Fase 1 roadmap TTS, lihat README.md): untuk tiap kata
dalam teks, coba urutan prioritas berikut sebelum menyerah --

    1. Rekaman utuh untuk kata itu sendiri (exact match)
    2. Rekaman per suku kata (hasil FsaSyllableService/syllable_splitter)
    3. Rekaman per huruf, kalau satu suku kata tertentu belum direkam
    4. Gagal (MissingAudioUnitsError) -- TIDAK menghasilkan audio parsial
       yang diam-diam bolong, karena itu lebih menyesatkan daripada error
       yang jelas.

PENTING: di tiap tingkat, pencarian dulu dicoba dengan teks PERSIS (cuma
case-folded, diakritik/glotal dipertahankan) sebelum jatuh ke normalisasi
diakritik sebagai fallback -- lihat UnitIndex.lookup() dan text_normalizer.py.
Ini krusial untuk audio: "a", "a'", dan "â" adalah TIGA rekaman yang
berbeda secara fonetis, bukan variasi ejaan kata yang sama seperti pada
pencarian kamus/terjemahan berbasis teks.

Modul ini murni logika seleksi (tidak menyentuh jaringan/audio sama sekali)
supaya gampang diuji lewat kombinasi unit yang tersedia/tidak tersedia --
lihat tests/test_unit_selector.py.
"""

from __future__ import annotations

from app.exceptions import MissingAudioUnitsError
from app.schemas import PlanItem, SynthesisPlan, UnitIndex
from app.services.syllable_splitter import split_syllables_list
from app.services.text_normalizer import case_fold, tokenize_words


def select_units(text: str, index: UnitIndex) -> SynthesisPlan:
    tokens = tokenize_words(case_fold(text))

    if not tokens:
        return SynthesisPlan(items=[])

    plan_items: list[PlanItem] = []
    missing_segments: list[str] = []

    for token in tokens:
        token_items, token_missing = _resolve_token(token, index)
        if token_missing:
            missing_segments.extend(token_missing)
        else:
            plan_items.extend(token_items)

    if missing_segments:
        raise MissingAudioUnitsError(missing_segments)

    return SynthesisPlan(items=plan_items)


def _resolve_token(token: str, index: UnitIndex) -> tuple[list[PlanItem], list[str]]:
    # 1. Exact match untuk seluruh kata (persis dulu, baru fallback ternormalisasi).
    unit = index.lookup(token)
    if unit is not None:
        return [PlanItem(segment=token, audio_url=unit.audio_url)], []

    # 2 & 3. Per suku kata, dengan fallback ke huruf kalau satu suku kata
    # tertentu belum ada rekamannya sendiri. Dipecah dari teks ASLI (bukan
    # yang sudah dinormalisasi diakritiknya) supaya FSA tetap mengenali
    # â/è sebagai vokal yang benar.
    syllables = split_syllables_list(token)
    items: list[PlanItem] = []
    missing: list[str] = []

    for syllable in syllables:
        syllable_unit = index.lookup(syllable)
        if syllable_unit is not None:
            items.append(PlanItem(segment=syllable, audio_url=syllable_unit.audio_url))
            continue

        letter_items, letters_missing = _resolve_letters(syllable, index)
        if letters_missing:
            missing.append(syllable)
        else:
            items.extend(letter_items)

    return items, missing


def _resolve_letters(syllable: str, index: UnitIndex) -> tuple[list[PlanItem], list[str]]:
    items: list[PlanItem] = []
    for letter in syllable:
        unit = index.lookup(letter)
        if unit is None:
            return [], [letter]
        items.append(PlanItem(segment=letter, audio_url=unit.audio_url))
    return items, []
