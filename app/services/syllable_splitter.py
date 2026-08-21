"""
Port Python dari FsaSyllableService.php (bbm-backend) -- Finite State
Automaton dua tingkat untuk memenggal kata bahasa Madura menjadi suku kata.
Logikanya sengaja disalin PERSIS dari versi PHP (termasuk urutan cabang
if/elif dan pola indeks array-nya) supaya kedua sisi selalu menghasilkan
pemenggalan yang identik -- lihat tests/test_syllable_splitter.py yang
memvalidasi paritas terhadap output PHP asli untuk sejumlah kata nyata dari
kamus.

Berbeda dari versi PHP: di sini TIDAK ada state instance (`self.pola`)
yang dibagi antar pemanggilan. FastAPI melayani request secara konkuren,
jadi state mutable di level instance/module akan bocor antar request yang
berbarengan -- versi ini murni fungsional, `pola` dan `hasil1` selalu lokal
per pemanggilan.
"""

from __future__ import annotations

_VOCAL = {"a", "â", "e", "è", "i", "o", "u", "'", "é", "ê"}
_KONSONAN2 = {"b", "g", "d", "j", "k"}


def _fsa_tingkat_satu(kata: str) -> tuple[str, list[int]]:
    kata = kata.lower().replace("\\", "").replace("-", "")
    huruf = list(kata)
    panjang = len(huruf)

    pola: list[int] = []
    hasil1 = ""
    i = 0

    while i < panjang:
        cur = huruf[i]
        nxt1 = huruf[i + 1] if i + 1 < panjang else ""
        nxt2 = huruf[i + 2] if i + 2 < panjang else ""

        if cur == "n":
            if nxt1 in ("g", "y") and nxt2 in _VOCAL:
                hasil1 += cur + nxt1 + nxt2
                pola.append(3)
                i += 2
            elif nxt1 in ("g", "y"):
                hasil1 += cur + nxt1
                pola.append(2)
                i += 1
            elif nxt1 in _VOCAL:
                hasil1 += cur + nxt1
                pola.append(3)
                i += 1
            else:
                hasil1 += cur
                pola.append(2)
            hasil1 += "-"
        elif cur in _KONSONAN2:
            if nxt1 == "h" and nxt2 in _VOCAL:
                hasil1 += cur + nxt1 + nxt2
                pola.append(3)
                i += 2
            elif nxt1 == "h":
                hasil1 += cur + nxt1
                pola.append(2)
                i += 1
            elif nxt1 in _VOCAL:
                hasil1 += cur + nxt1
                pola.append(3)
                i += 1
            else:
                hasil1 += cur
                pola.append(2)
            hasil1 += "-"
        elif cur in _VOCAL:
            hasil1 += cur + "-"
            pola.append(4 if cur == "'" else 1)
        else:
            if nxt1 in _VOCAL:
                hasil1 += cur + nxt1
                pola.append(3)
                i += 1
            else:
                hasil1 += cur
                pola.append(2)
            hasil1 += "-"

        i += 1

    return hasil1, pola


def _fsa_tingkat_dua(kata: str, pola: list[int]) -> str:
    arr = kata.split("-")
    jumlah = len(arr)
    hasil2 = ""
    i = 0

    while i < jumlah - 1:
        p0 = pola[i] if i < len(pola) else None
        p1 = pola[i + 1] if i + 1 < len(pola) else None
        p2 = pola[i + 2] if i + 2 < len(pola) else None

        if p0 == 1 and p1 in (2, 4):
            hasil2 += arr[i] + arr[i + 1]
            i += 1
        elif p0 == 1:
            hasil2 += arr[i]
        elif p0 == 2 and p1 == 3 and p2 in (2, 4):
            hasil2 += arr[i] + arr[i + 1] + arr[i + 2]
            i += 2
        elif p0 == 2 and p1 == 3:
            hasil2 += arr[i] + arr[i + 1]
            i += 1
        elif p0 == 3 and p1 in (2, 4):
            hasil2 += arr[i] + arr[i + 1]
            i += 1
        elif p0 == 3:
            hasil2 += arr[i]

        i += 1
        hasil2 += "-"

    return hasil2.rstrip("-")


def split_syllables(kata: str) -> str:
    """Mengembalikan pemenggalan suku kata, mis. 'sapedha' -> 'sa-pe-dha'."""
    hasil1, pola = _fsa_tingkat_satu(kata)
    return _fsa_tingkat_dua(hasil1, pola)


def split_syllables_list(kata: str) -> list[str]:
    result = split_syllables(kata)
    return [s for s in result.split("-") if s]
