"""
Endpoint server-to-server, hanya dipanggil bbm-backend (Laravel) setelah
korpus tts_recordings berubah -- lihat TtsCache.clear() untuk alasan cache
ini harus di-flush eksplisit (tidak ada TTL/invalidation otomatis).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException

from app.cache.tts_cache import TtsCache
from app.config import Settings, get_settings

router = APIRouter(prefix="/admin", tags=["admin"])


def get_cache(settings: Settings = Depends(get_settings)) -> TtsCache:
    return TtsCache(settings.cache_dir)


def verify_internal_token(
    x_internal_token: str = Header(default=""),
    settings: Settings = Depends(get_settings),
) -> None:
    expected = settings.backend_internal_token
    if not expected or x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized.")


@router.post("/cache/clear", dependencies=[Depends(verify_internal_token)])
def clear_cache(cache: TtsCache = Depends(get_cache)) -> dict[str, int]:
    removed = cache.clear()
    return {"removed": removed}
