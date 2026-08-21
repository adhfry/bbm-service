import pytest
from fastapi.testclient import TestClient
from pydub.generators import Sine

from app.exceptions import BackendUnavailableError
from app.main import app
from app.routers.tts import get_synthesis_service
from app.schemas import UnitInfo
from app.services import audio_composer
from app.services.synthesis_service import SynthesisResult


class StubSynthesisService:
    def __init__(self, result: SynthesisResult | None = None, error: Exception | None = None):
        self._result = result
        self._error = error

    async def synthesize(self, text: str) -> SynthesisResult:
        if self._error:
            raise self._error
        return self._result


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_health_endpoint():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "bbm-service"}


def test_tts_endpoint_returns_wav_audio_on_success():
    wav_bytes = audio_composer.export_wav(Sine(440).to_audio_segment(duration=100))
    stub = StubSynthesisService(SynthesisResult(audio_bytes=wav_bytes, cached=False, segments_used=["sa"]))
    app.dependency_overrides[get_synthesis_service] = lambda: stub

    client = TestClient(app)
    response = client.post("/tts", json={"text": "sa"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-tts-segments"] == "sa"
    assert response.content[:4] == b"RIFF"


def test_tts_endpoint_rejects_empty_text_with_422_validation_error():
    client = TestClient(app)
    response = client.post("/tts", json={"text": ""})
    # Kosong ditolak oleh validasi Pydantic (min_length=1) sebelum domain
    # logic sempat jalan sama sekali.
    assert response.status_code == 422


def test_tts_endpoint_reports_missing_units_as_422_with_details():
    from app.exceptions import MissingAudioUnitsError

    stub = StubSynthesisService(error=MissingAudioUnitsError(["bâ"]))
    app.dependency_overrides[get_synthesis_service] = lambda: stub

    client = TestClient(app)
    response = client.post("/tts", json={"text": "bâbâ"})

    assert response.status_code == 422
    body = response.json()
    assert body["status"] == "error"
    assert body["data"]["missing_segments"] == ["bâ"]


def test_tts_endpoint_reports_backend_outage_as_503():
    stub = StubSynthesisService(error=BackendUnavailableError("down"))
    app.dependency_overrides[get_synthesis_service] = lambda: stub

    client = TestClient(app)
    response = client.post("/tts", json={"text": "apa saja"})

    assert response.status_code == 503
    assert response.json()["status"] == "error"


def test_tts_endpoint_unit_info_model_roundtrip():
    # Sanity check kecil bahwa UnitInfo tetap kompatibel dengan bentuk JSON
    # yang dikirim backend (text/type/audio_url).
    unit = UnitInfo(text="sa", type="suku_kata", audio_url="https://x/sa.wav")
    assert unit.model_dump() == {"text": "sa", "type": "suku_kata", "audio_url": "https://x/sa.wav"}
