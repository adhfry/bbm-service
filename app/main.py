from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="BBM Service - Madurese TTS",
    description="Layanan internal TTS bahasa Madura, dipanggil oleh bbm-backend (Laravel).",
    version="0.1.0",
)


class TtsRequest(BaseModel):
    text: str


@app.get("/health")
def health():
    return {"status": "ok", "service": "bbm-service"}


@app.post("/tts")
def synthesize(request: TtsRequest):
    """
    Kontrak endpoint TTS untuk Laravel. Belum diimplementasikan -- pipeline
    unit-selection (pemenggalan suku kata -> pencarian unit audio -> trim/
    normalize/crossfade) menyusul setelah struktur data unit audio & lokasi
    penyimpanan (MinIO) dikonfirmasi. Menjawab 501 secara jujur, bukan
    berpura-pura menghasilkan audio.
    """
    raise HTTPException(status_code=501, detail="TTS belum diimplementasikan.")
