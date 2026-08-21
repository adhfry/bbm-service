import pytest
from pydub.generators import Sine

from app.config import Settings
from app.exceptions import BackendUnavailableError, EmptyTextError, MissingAudioUnitsError
from app.schemas import UnitInfo
from app.services import audio_composer
from app.services.synthesis_service import SynthesisService


def _tone_wav_bytes(duration_ms: int = 150) -> bytes:
    segment = Sine(440).to_audio_segment(duration=duration_ms)
    return audio_composer.export_wav(segment)


class FakeRepository:
    """Test double -- tidak melakukan HTTP sungguhan sama sekali."""

    def __init__(self, units: dict[str, UnitInfo], should_fail: bool = False):
        self._units = units
        self._should_fail = should_fail
        self.fetch_calls = 0

    async def fetch_active_units(self) -> dict[str, UnitInfo]:
        if self._should_fail:
            raise BackendUnavailableError("simulated outage")
        self.fetch_calls += 1
        return self._units

    async def fetch_audio_bytes(self, audio_url: str) -> bytes:
        return _tone_wav_bytes()


class FakeCache:
    def __init__(self):
        self.store: dict[str, bytes] = {}

    def get(self, key: str) -> bytes | None:
        return self.store.get(key)

    def set(self, key: str, value: bytes) -> None:
        self.store[key] = value


@pytest.fixture
def settings() -> Settings:
    return Settings(backend_base_url="http://unused.test", backend_internal_token="x")


async def test_synthesize_empty_text_raises_before_touching_repository(settings):
    repo = FakeRepository({})
    service = SynthesisService(settings, repo, FakeCache())

    with pytest.raises(EmptyTextError):
        await service.synthesize("   ")

    assert repo.fetch_calls == 0


async def test_synthesize_success_produces_wav_and_populates_cache(settings):
    units = {"sa": UnitInfo(text="sa", type="suku_kata", audio_url="https://x/sa.wav")}
    repo = FakeRepository(units)
    cache = FakeCache()
    service = SynthesisService(settings, repo, cache)

    result = await service.synthesize("sa")

    assert result.cached is False
    assert result.audio_bytes[:4] == b"RIFF"
    assert result.segments_used == ["sa"]
    assert len(cache.store) == 1


async def test_synthesize_returns_cached_audio_without_calling_repository(settings):
    units = {"sa": UnitInfo(text="sa", type="suku_kata", audio_url="https://x/sa.wav")}
    repo = FakeRepository(units)
    cache = FakeCache()
    service = SynthesisService(settings, repo, cache)

    first = await service.synthesize("sa")
    calls_after_first = repo.fetch_calls
    second = await service.synthesize("sa")

    assert second.cached is True
    assert second.audio_bytes == first.audio_bytes
    assert repo.fetch_calls == calls_after_first  # tidak ada panggilan tambahan


async def test_synthesize_missing_unit_propagates_domain_error(settings):
    repo = FakeRepository({})  # tidak ada unit sama sekali
    service = SynthesisService(settings, repo, FakeCache())

    with pytest.raises(MissingAudioUnitsError):
        await service.synthesize("bâbâ")


async def test_synthesize_backend_outage_propagates_domain_error(settings):
    repo = FakeRepository({}, should_fail=True)
    service = SynthesisService(settings, repo, FakeCache())

    with pytest.raises(BackendUnavailableError):
        await service.synthesize("apa saja")
