import pytest

from app.exceptions import MissingAudioUnitsError
from app.schemas import UnitIndex, UnitInfo
from app.services.text_normalizer import case_fold, normalize_diacritics
from app.services.unit_selector import select_units


def _index(*texts: str, type_: str = "kata") -> UnitIndex:
    """Bangun UnitIndex dari daftar teks unit, mengikuti aturan repository asli:
    exact dikunci case-fold saja, normalized dikunci diakritik dibuang."""
    index = UnitIndex()
    for text in texts:
        info = UnitInfo(text=text, type=type_, audio_url=f"https://example.test/{text}.wav")
        index.exact[case_fold(text)] = info
        index.normalized.setdefault(normalize_diacritics(text), info)
    return index


def test_prefers_exact_whole_word_match():
    index = _index("sapedha")
    plan = select_units("sapedha", index)
    assert [item.segment for item in plan.items] == ["sapedha"]


def test_falls_back_to_syllables_when_no_exact_match():
    # "sapedha" -> sa-pe-dha, tidak ada rekaman utuh tapi tiap suku kata ada.
    index = _index("sa", "pe", "dha", type_="suku_kata")
    plan = select_units("sapedha", index)
    assert [item.segment for item in plan.items] == ["sa", "pe", "dha"]


def test_falls_back_to_letters_for_one_missing_syllable():
    # "dha" suku kata belum direkam, tapi huruf d/h/a ada.
    index = _index("sa", "pe", type_="suku_kata")
    for letter in ("d", "h", "a"):
        info = UnitInfo(text=letter, type="huruf", audio_url=f"https://example.test/{letter}.wav")
        index.exact[letter] = info
        index.normalized.setdefault(letter, info)

    plan = select_units("sapedha", index)
    assert [item.segment for item in plan.items] == ["sa", "pe", "d", "h", "a"]


def test_raises_missing_units_error_when_nothing_matches():
    index = UnitIndex()
    with pytest.raises(MissingAudioUnitsError) as exc_info:
        select_units("bâbâ", index)
    # Dipecah dari teks ASLI (diakritik dipertahankan) -- bukan bentuk
    # ternormalisasi, karena "bâ" bukan sekadar variasi ejaan "ba".
    assert exc_info.value.missing_segments == ["bâ", "bâ"]


def test_distinguishes_plain_glottal_and_back_vowel_variants():
    # Ketiganya HARUS jadi tiga entri berbeda, tidak boleh saling menimpa --
    # ini bug nyata yang ditemukan saat audit korpus legacy (317 pasang
    # unit collision kalau dikunci dari bentuk ternormalisasi).
    index = _index("a", "a'", "â")
    assert index.exact["a"].text == "a"
    assert index.exact["a'"].text == "a'"
    assert index.exact["â"].text == "â"

    plan_plain = select_units("a", index)
    plan_glottal = select_units("a'", index)
    plan_back = select_units("â", index)

    assert [i.audio_url for i in plan_plain.items] == ["https://example.test/a.wav"]
    assert [i.audio_url for i in plan_glottal.items] == ["https://example.test/a'.wav"]
    assert [i.audio_url for i in plan_back.items] == ["https://example.test/â.wav"]


def test_falls_back_to_normalized_form_when_exact_diacritic_missing():
    # Hanya "da" (tanpa diakritik) yang direkam -- input "dâ" (dengan
    # diakritik) tidak ada rekaman persisnya, jadi jatuh ke fallback
    # ternormalisasi daripada langsung gagal.
    index = _index("da")
    plan = select_units("dâ", index)
    assert [item.segment for item in plan.items] == ["dâ"]
    assert plan.items[0].audio_url == "https://example.test/da.wav"


def test_multi_word_text_resolves_each_word_independently():
    index = _index("selamat", "pagi")
    plan = select_units("selamat pagi", index)
    assert [item.segment for item in plan.items] == ["selamat", "pagi"]


def test_empty_text_returns_empty_plan_not_error():
    plan = select_units("   ", UnitIndex())
    assert plan.items == []
