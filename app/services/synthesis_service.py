"""
Orkestrasi alur sintesis penuh: normalisasi -> cek cache -> ambil unit yang
tersedia -> pilih unit (unit_selector) -> unduh audio tiap unit -> gabung
(audio_composer) -> simpan ke cache -> kembalikan bytes WAV + metadata.

Router (app/routers/tts.py) sengaja dibuat setipis mungkin -- semua alur
nyata ada di sini supaya bisa diuji tanpa perlu menjalankan server HTTP
sungguhan (lihat tests/test_synthesis_service.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.cache.tts_cache import TtsCache
from app.config import Settings
from app.exceptions import EmptyTextError
from app.repositories.recording_repository import RecordingRepository
from app.services import audio_composer
from app.services.text_normalizer import normalize_diacritics
from app.services.unit_selector import select_units


@dataclass(slots=True)
class SynthesisResult:
    audio_bytes: bytes
    cached: bool
    segments_used: list[str]


class SynthesisService:
    def __init__(
        self,
        settings: Settings,
        repository: RecordingRepository,
        cache: TtsCache,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._cache = cache

    async def synthesize(self, raw_text: str) -> SynthesisResult:
        normalized = normalize_diacritics(raw_text.strip())
        if not normalized:
            raise EmptyTextError("Teks tidak boleh kosong.")

        cached_audio = self._cache.get(normalized)
        if cached_audio is not None:
            return SynthesisResult(audio_bytes=cached_audio, cached=True, segments_used=[])

        available_units = await self._repository.fetch_active_units()
        plan = select_units(normalized, available_units)

        segments = []
        for item in plan.items:
            audio_bytes = await self._repository.fetch_audio_bytes(item.audio_url)
            segments.append(audio_composer.load_segment(audio_bytes))

        composed = audio_composer.compose(
            segments,
            crossfade_ms=self._settings.crossfade_ms,
            silence_threshold_dbfs=self._settings.silence_threshold_dbfs,
        )
        result_bytes = audio_composer.export_wav(composed)

        self._cache.set(normalized, result_bytes)

        return SynthesisResult(audio_bytes=result_bytes, cached=False, segments_used=plan.segments_used)
