"""
Hierarki exception khusus domain TTS. Setiap exception di sini dipetakan ke
status HTTP + bentuk error yang jelas lewat handler di app/main.py -- supaya
kegagalan (teks kosong, unit audio belum direkam, backend tidak bisa
dihubungi, audio korup) masing-masing punya respons yang jujur dan bisa
ditindaklanjuti, bukan 500 generik untuk semuanya.
"""

from __future__ import annotations


class TtsServiceError(Exception):
    """Basis untuk semua error domain TTS di layanan ini."""


class EmptyTextError(TtsServiceError):
    """Teks request kosong (atau kosong setelah dinormalisasi/di-strip)."""


class MissingAudioUnitsError(TtsServiceError):
    """
    Satu atau lebih segmen (kata/suku kata/huruf) tidak punya rekaman aktif
    sama sekali di korpus -- lihat unit_selector.py untuk urutan fallback
    yang sudah dicoba sebelum sampai ke sini.
    """

    def __init__(self, missing_segments: list[str]) -> None:
        self.missing_segments = missing_segments
        segments_text = ", ".join(missing_segments)
        super().__init__(f"Unit audio belum tersedia untuk: {segments_text}")


class BackendUnavailableError(TtsServiceError):
    """bbm-backend (Laravel) tidak bisa dihubungi untuk mengambil data unit/audio."""


class AudioProcessingError(TtsServiceError):
    """Gagal memproses audio (decode/trim/normalize/crossfade/export)."""
