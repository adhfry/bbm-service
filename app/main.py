from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import (
    AudioProcessingError,
    BackendUnavailableError,
    EmptyTextError,
    MissingAudioUnitsError,
    TtsServiceError,
)
from app.routers import admin, tts

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="BBM Service - Madurese TTS",
    description="Layanan internal TTS bahasa Madura, dipanggil oleh bbm-backend (Laravel).",
    version="0.2.0",
)
app.include_router(tts.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bbm-service"}


def _error_body(message: str, data: dict | None = None) -> dict:
    return {"status": "error", "message": message, "data": data}


@app.exception_handler(EmptyTextError)
async def handle_empty_text(request: Request, exc: EmptyTextError) -> JSONResponse:
    return JSONResponse(status_code=400, content=_error_body(str(exc)))


@app.exception_handler(MissingAudioUnitsError)
async def handle_missing_units(request: Request, exc: MissingAudioUnitsError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_error_body(str(exc), {"missing_segments": exc.missing_segments}),
    )


@app.exception_handler(BackendUnavailableError)
async def handle_backend_unavailable(request: Request, exc: BackendUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=503, content=_error_body(str(exc)))


@app.exception_handler(AudioProcessingError)
async def handle_audio_processing(request: Request, exc: AudioProcessingError) -> JSONResponse:
    return JSONResponse(status_code=500, content=_error_body(str(exc)))


@app.exception_handler(TtsServiceError)
async def handle_generic_tts_error(request: Request, exc: TtsServiceError) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled TtsServiceError")
    return JSONResponse(status_code=500, content=_error_body(str(exc)))
