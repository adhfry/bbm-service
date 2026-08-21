"""
Mirror persis TranslationService::normalizeDiacritics() di bbm-backend
(Laravel) -- huruf â/è/é/ê disamakan ke a/e dan glotal apostrof dibuang,
supaya pencarian unit di sini konsisten dengan pencarian kamus/terjemahan di
backend (kata yang sama harus menemukan unit yang sama, apapun cara
penulisan diakritiknya).
"""

from __future__ import annotations

_DIACRITIC_TRANSLATION = str.maketrans({"â": "a", "è": "e", "é": "e", "ê": "e", "'": ""})


def normalize_diacritics(text: str) -> str:
    return text.lower().translate(_DIACRITIC_TRANSLATION)


def tokenize_words(text: str) -> list[str]:
    """Pecah teks menjadi kata (whitespace-delimited), buang token kosong."""
    return [token for token in text.split() if token]
