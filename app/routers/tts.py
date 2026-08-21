from __future__ import annotations

from fastapi import APIRouter, Depends, Response

from app.cache.tts_cache import TtsCache
from app.config import Settings, get_settings
from app.repositories.recording_repository import RecordingRepository
from app.schemas import TtsRequest
from app.services.synthesis_service import SynthesisService

router = APIRouter(prefix="/tts", tags=["tts"])


def get_repository(settings: Settings = Depends(get_settings)) -> RecordingRepository:
    return RecordingRepository(settings=settings)


def get_cache(settings: Settings = Depends(get_settings)) -> TtsCache:
    return TtsCache(settings.cache_dir)


def get_synthesis_service(
    settings: Settings = Depends(get_settings),
    repository: RecordingRepository = Depends(get_repository),
    cache: TtsCache = Depends(get_cache),
) -> SynthesisService:
    return SynthesisService(settings=settings, repository=repository, cache=cache)


@router.post(
    "",
    responses={200: {"content": {"audio/wav": {}}}},
    summary="Sintesis teks Madura menjadi audio (unit-selection, Fase 1)",
)
async def synthesize(
    request: TtsRequest,
    service: SynthesisService = Depends(get_synthesis_service),
) -> Response:
    result = await service.synthesize(request.text)

    return Response(
        content=result.audio_bytes,
        media_type="audio/wav",
        headers={
            "X-Tts-Cached": "true" if result.cached else "false",
            "X-Tts-Engine": "unit_selection_v1",
            "X-Tts-Segments": ",".join(result.segments_used),
        },
    )
