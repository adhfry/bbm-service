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
from app.schemas import UnitIndex, UnitInfo
from app.services.text_normalizer import case_fold, normalize_diacritics


class RecordingRepository:
    def __init__(self, settings: Settings | None = None, client: httpx.AsyncClient | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = client or httpx.AsyncClient(timeout=self._settings.request_timeout_seconds)
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def fetch_active_units(self) -> UnitIndex:
        """
        Membangun DUA peta dari daftar unit aktif -- lihat UnitIndex dan
        text_normalizer.py untuk kenapa keduanya harus terpisah (korpus
        legacy punya 317 pasang/kelompok unit yang HANYA berbeda diakritik/
        glotal, mis. "a" vs "a'" vs "â" -- itu tiga rekaman berbeda, bukan
        duplikat, jadi tidak boleh saling menimpa lewat kunci ternormalisasi).
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

        index = UnitIndex()
        for row in rows:
            info = UnitInfo(text=row["text"], type=row["type"], audio_url=row["audio_url"])
            index.exact[case_fold(str(row["text"]))] = info
            # first-wins untuk peta fallback: kalau beberapa unit bertabrakan
            # setelah dinormalisasi, yang lebih dulu di korpus yang dipakai --
            # ini cuma best-effort fallback, bukan sumber kebenaran utama.
            index.normalized.setdefault(normalize_diacritics(str(row["text"])), info)

        return index

    async def fetch_audio_bytes(self, audio_url: str) -> bytes:
        try:
            response = await self._client.get(audio_url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise BackendUnavailableError(f"Gagal mengunduh audio unit dari {audio_url}: {exc}") from exc
        return response.content
