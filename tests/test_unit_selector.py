import pytest

from app.exceptions import MissingAudioUnitsError
from app.schemas import UnitInfo
from app.services.unit_selector import select_units


def _unit(text: str, type_: str = "kata") -> UnitInfo:
    return UnitInfo(text=text, type=type_, audio_url=f"https://example.test/{text}.wav")


def test_prefers_exact_whole_word_match():
    available = {"sapedha": _unit("sapedha", "kata")}
    plan = select_units("sapedha", available)
    assert [item.segment for item in plan.items] == ["sapedha"]


def test_falls_back_to_syllables_when_no_exact_match():
    # "sapedha" -> sa-pe-dha, tidak ada rekaman utuh tapi tiap suku kata ada.
    available = {
        "sa": _unit("sa", "suku_kata"),
        "pe": _unit("pe", "suku_kata"),
        "dha": _unit("dha", "suku_kata"),
    }
    plan = select_units("sapedha", available)
    assert [item.segment for item in plan.items] == ["sa", "pe", "dha"]


def test_falls_back_to_letters_for_one_missing_syllable():
    # "dha" suku kata belum direkam, tapi huruf d/h/a ada.
    available = {
        "sa": _unit("sa", "suku_kata"),
        "pe": _unit("pe", "suku_kata"),
        "d": _unit("d", "huruf"),
        "h": _unit("h", "huruf"),
        "a": _unit("a", "huruf"),
    }
    plan = select_units("sapedha", available)
    assert [item.segment for item in plan.items] == ["sa", "pe", "d", "h", "a"]


def test_raises_missing_units_error_when_nothing_matches():
    # Pencarian unit tidak peka diakritik (sama seperti kamus/terjemahan di
    # Laravel) -- "bâbâ" dinormalisasi ke "baba" dulu sebelum dipecah suku
    # kata, jadi segmen yang dilaporkan hilang juga bentuk ternormalisasi.
    available: dict[str, UnitInfo] = {}
    with pytest.raises(MissingAudioUnitsError) as exc_info:
        select_units("bâbâ", available)
    assert exc_info.value.missing_segments == ["ba", "ba"]


def test_matches_across_diacritic_variants():
    # Unit direkam sebagai "salamet" (tanpa diakritik di kata ini juga),
    # tapi teks masuk memakai diakritik lain yang senilai setelah normalisasi.
    available = {"nase": _unit("nase")}
    plan = select_units("nasè'", available)
    assert [item.segment for item in plan.items] == ["nase"]


def test_multi_word_text_resolves_each_word_independently():
    available = {"selamat": _unit("selamat"), "pagi": _unit("pagi")}
    plan = select_units("selamat pagi", available)
    assert [item.segment for item in plan.items] == ["selamat", "pagi"]


def test_empty_text_returns_empty_plan_not_error():
    plan = select_units("   ", {})
    assert plan.items == []
