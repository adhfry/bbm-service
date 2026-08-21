import pytest
from pydub import AudioSegment
from pydub.generators import Sine

from app.exceptions import AudioProcessingError
from app.services import audio_composer


def _tone(duration_ms: int, freq: int = 440) -> AudioSegment:
    return Sine(freq).to_audio_segment(duration=duration_ms).apply_gain(-3.0)


def test_compose_raises_on_empty_segment_list():
    with pytest.raises(AudioProcessingError):
        audio_composer.compose([], crossfade_ms=25, silence_threshold_dbfs=-40)


def test_compose_single_segment_sets_target_frame_rate_and_channels():
    segment = _tone(200)
    result = audio_composer.compose([segment], crossfade_ms=25, silence_threshold_dbfs=-40)
    assert result.frame_rate == 22050
    assert result.channels == 1


def test_compose_concatenates_multiple_segments_to_roughly_expected_length():
    segments = [_tone(200), _tone(150), _tone(300)]
    result = audio_composer.compose(segments, crossfade_ms=20, silence_threshold_dbfs=-40)
    # Crossfade memendekkan total sedikit dari 650ms, tapi tidak boleh runtuh
    # jauh di bawahnya atau lebih panjang dari jumlah mentahnya.
    assert 400 <= len(result) <= 650


def test_compose_handles_very_short_segments_without_crossfade_error():
    # Segmen 5ms lebih pendek dari crossfade default (25ms) -- tidak boleh
    # melempar error, crossfade harus otomatis dipangkas aman.
    segments = [_tone(5), _tone(5), _tone(5)]
    result = audio_composer.compose(segments, crossfade_ms=25, silence_threshold_dbfs=-40)
    assert len(result) > 0


def test_compose_handles_pure_silence_segment_without_crashing():
    silence = AudioSegment.silent(duration=100)
    tone = _tone(150)
    result = audio_composer.compose([silence, tone], crossfade_ms=20, silence_threshold_dbfs=-40)
    assert len(result) > 0


def test_export_wav_produces_riff_header():
    segment = _tone(100)
    wav_bytes = audio_composer.export_wav(segment)
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"


def test_load_segment_rejects_garbage_bytes():
    with pytest.raises(AudioProcessingError):
        audio_composer.load_segment(b"this is not a real audio file")
