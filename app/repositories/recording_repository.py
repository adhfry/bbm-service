"""
Jembatan HTTP async ke bbm-backend (Laravel) -- satu-satunya sumber daftar
unit audio aktif dan file audionya (disimpan di MinIO lewat backend, lihat
TtsRecordingController). Layanan ini sengaja TIDAK menyentuh MinIO atau
database backend secara langsung, supaya backend tetap satu-satunya pemilik
data (lihat bbm-service/README.md untuk alasan arsitektur ini).
"""

from __future__ import annotations

import httpx

from app.config import Settings, get_settings
from app.exceptions import BackendUnavailableError
from app.schemas import UnitInfo
from app.services.text_normalizer import normalize_diacritics


class RecordingRepository:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client or httpx.AsyncClient(timeout=self._settings.request_timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_active_units(self) -> dict[str, UnitInfo]:
        """
        Mengembalikan pemetaan teks unit (dinormalisasi diakritiknya) ->
        UnitInfo. Kalau dua rekaman punya teks yang sama setelah normalisasi,
        yang terakhir dari backend (biasanya paling baru) yang dipakai.
        """
        url = f"{self._settings.backend_base_url}/api/v2/tts/units"
        headers = {"X-Internal-Token": self._settings.backend_internal_token}

        try:
            response = await self._client.get(url, headers=headers)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(
                f"Tidak bisa mengambil daftar unit audio dari bbm-backend: {exc}"
            ) from exc

        payload = response.json()
        rows = payload.get("data", [])

        units: dict[str, UnitInfo] = {}
        for row in rows:
            key = normalize_diacritics(str(row["text"]))
            units[key] = UnitInfo(text=row["text"], type=row["type"], audio_url=row["audio_url"])

        return units

    async def fetch_audio_bytes(self, audio_url: str) -> bytes:
        try:
            response = await self._client.get(audio_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(f"Gagal mengunduh audio unit dari {audio_url}: {exc}") from exc
        return response.content
