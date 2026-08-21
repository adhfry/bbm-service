import httpx
import pytest

from app.config import Settings
from app.exceptions import BackendUnavailableError
from app.repositories.recording_repository import RecordingRepository


def _client_returning(payload: dict, status_code: int = 200) -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _failing_client() -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
def settings() -> Settings:
    return Settings(backend_base_url="http://backend.test", backend_internal_token="secret")


async def test_fetch_active_units_preserves_diacritic_variants_as_distinct_exact_entries(settings):
    # Ini kasus nyata yang ditemukan saat audit korpus legacy: "a", "a'", "â"
    # adalah tiga rekaman berbeda dan HARUS tetap tiga entri terpisah di
    # peta `exact`, walau ketiganya jatuh ke kunci ternormalisasi yang sama.
    payload = {
        "data": [
            {"text": "a", "type": "huruf", "audio_url": "https://x/a.wav"},
            {"text": "a'", "type": "huruf", "audio_url": "https://x/a-glotal.wav"},
            {"text": "â", "type": "huruf", "audio_url": "https://x/a-belakang.wav"},
        ]
    }
    repo = RecordingRepository(settings=settings, client=_client_returning(payload))

    index = await repo.fetch_active_units()

    assert index.exact["a"].audio_url == "https://x/a.wav"
    assert index.exact["a'"].audio_url == "https://x/a-glotal.wav"
    assert index.exact["â"].audio_url == "https://x/a-belakang.wav"
    # Peta fallback ternormalisasi cuma nampung SATU representative (first-wins).
    assert index.normalized["a"].audio_url == "https://x/a.wav"


async def test_fetch_active_units_raises_on_backend_connection_failure(settings):
    repo = RecordingRepository(settings=settings, client=_failing_client())

    with pytest.raises(BackendUnavailableError):
        await repo.fetch_active_units()


async def test_fetch_active_units_raises_on_non_2xx_response(settings):
    repo = RecordingRepository(settings=settings, client=_client_returning({"data": []}, status_code=500))

    with pytest.raises(BackendUnavailableError):
        await repo.fetch_active_units()


async def test_fetch_audio_bytes_returns_raw_content(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"fake-wav-bytes")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    repo = RecordingRepository(settings=settings, client=client)

    audio_bytes = await repo.fetch_audio_bytes("https://x/a.wav")

    assert audio_bytes == b"fake-wav-bytes"
