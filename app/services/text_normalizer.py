"""
Dua fungsi normalisasi dengan tujuan BERBEDA -- jangan disatukan:

- `case_fold()`: satu-satunya normalisasi yang aman diterapkan ke SEMUA teks
  sebelum dicocokkan ke unit audio. â/è/glotal apostrof TETAP dipertahankan,
  karena untuk audio ("a" vs "a'" vs "â") itu bukan variasi ejaan kata yang
  sama -- itu TIGA rekaman yang berbeda secara fonetis (vokal polos, vokal
  dengan hentian glotal, dan vokal belakang Madura). Korpus legacy
  membuktikan ini nyata: menormalisasi diakritik pada 1.924 nama file unit
  legacy membuat 317 di antaranya bertabrakan jadi cuma 1.607 kunci --
  padahal isinya BUKAN duplikat (hash SHA-256 semua file itu berbeda-beda).
  Kalau unit_selector memakai normalisasi sebagai kunci UTAMA, salah satu
  dari ketiga rekaman itu akan diam-diam menimpa dua lainnya dan audio yang
  terputar jadi salah lafal.

- `normalize_diacritics()`: mirror TranslationService::normalizeDiacritics()
  di Laravel -- HANYA dipakai unit_selector sebagai fallback TERAKHIR kalau
  bentuk diakritik persis tidak ada rekamannya sama sekali (lebih baik
  approksimasi daripada gagal total), bukan sebagai kunci pencarian utama.
"""

from __future__ import annotations

_DIACRITIC_TRANSLATION = str.maketrans({"â": "a", "è": "e", "é": "e", "ê": "e", "'": ""})


def case_fold(text: str) -> str:
    """Normalisasi aman: cuma lowercase, TIDAK menyentuh diakritik/glotal."""
    return text.lower()


def normalize_diacritics(text: str) -> str:
    """Normalisasi lossy -- lihat catatan modul. Fallback saja, bukan kunci utama."""
    return text.lower().translate(_DIACRITIC_TRANSLATION)


def tokenize_words(text: str) -> list[str]:
    """Pecah teks menjadi kata (whitespace-delimited), buang token kosong."""
    return [token for token in text.split() if token]
