"""
Kasus uji ini adalah output NYATA dari FsaSyllableService.php (bbm-backend),
diambil langsung lewat `php artisan tinker` -- bukan hasil yang diasumsikan
atau ditebak. Kalau ada perubahan di masa depan pada versi PHP, jalankan
ulang generator paritas ini dan perbarui kasus-kasus di bawah.
"""

import pytest

from app.services.syllable_splitter import split_syllables, split_syllables_list

PHP_PARITY_CASES = [
    ("bâbâ", "bâ-bâ"),
    ("sapedha", "sa-pe-dha"),
    ("kalambhi", "ka-lam-bhi"),
    ("salamet", "sa-la-met"),
    ("dâteng", "dâ-teng"),
    ("ngangguy", "ngang-guy"),
    ("khodmat", "khod-mat"),
    ("a", "a"),
    ("ngoca", "ngo-ca"),
    ("na'-eng", "na'-eng"),
    ("bhârâh", "bhâ-râh"),
    ("tello", "tel-lo"),
]


@pytest.mark.parametrize("word,expected", PHP_PARITY_CASES)
def test_matches_php_fsa_syllable_service(word, expected):
    assert split_syllables(word) == expected


def test_split_syllables_list_drops_empty_segments():
    assert split_syllables_list("bâbâ") == ["bâ", "bâ"]
    assert split_syllables_list("a") == ["a"]


def test_single_vowel_letter():
    assert split_syllables("a") == "a"


def test_handles_uppercase_input_like_php_lowercases():
    assert split_syllables("SAPEDHA") == split_syllables("sapedha")
