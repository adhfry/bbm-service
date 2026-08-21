"""
Cache berbasis file, dikunci dari hash teks yang sudah dinormalisasi. Untuk
aplikasi edukasi seperti BBM, teks yang dibacakan cenderung berulang (mis.
kata-kata di modul belajar yang sama dibuka banyak siswa) -- cache murah ini
menghindari proses ulang unit-selection + audio composition setiap kali.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


class TtsCache:
    def __init__(self, cache_dir: str) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, normalized_text: str) -> Path:
        key = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
        return self._dir / f"{key}.wav"

    def get(self, normalized_text: str) -> bytes | None:
        path = self._path_for(normalized_text)
        if not path.exists():
            return None
        return path.read_bytes()

    def set(self, normalized_text: str, audio_bytes: bytes) -> None:
        self._path_for(normalized_text).write_bytes(audio_bytes)

    def clear(self) -> int:
        """Hapus semua entri cache. Dipanggil backend tiap kali korpus
        tts_recordings berubah (rekam/ganti/hapus/toggle aktif) -- tanpa ini,
        kata yang sudah pernah disintesis akan terus memutar audio LAMA
        selamanya walau baris/audio di database sudah diperbaiki, karena
        cache ini tidak punya TTL dan hanya dikunci dari teks, bukan dari isi
        korpus."""
        removed = 0
        for path in self._dir.glob("*.wav"):
            path.unlink(missing_ok=True)
            removed += 1
        return removed
