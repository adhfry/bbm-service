"""
Menggabungkan segmen-segmen audio (per kata/suku kata/huruf) menjadi satu
file WAV utuh: trim hening di ujung tiap segmen, normalisasi volume, lalu
disambung dengan crossfade singkat -- supaya tidak terdengar seperti dua
rekaman ditempel mentah (lihat README.md §"Ini bisa langsung dipakai").
"""

from __future__ import annotations

import io

from pydub import AudioSegment
from pydub.silence import detect_leading_silence

from app.exceptions import AudioProcessingError


def load_segment(audio_bytes: bytes) -> AudioSegment:
    """
    Semua unit direkam sebagai WAV PCM oleh backend (lihat
    TtsRecordingController::store, ffmpeg selalu -ar 22050 -ac 1) -- decode
    lewat modul `wave` bawaan Python (format="wav") dulu, TANPA perlu
    ffmpeg sama sekali untuk kasus normal ini. ffmpeg cuma dipakai sebagai
    fallback kalau ternyata bukan WAV murni (mis. file lama/berbeda format).
    """
    try:
        return AudioSegment.from_file(io.BytesIO(audio_bytes), format="wav")
    except Exception:
        try:
            return AudioSegment.from_file(io.BytesIO(audio_bytes))
        except Exception as exc:
            raise AudioProcessingError(f"Gagal membaca file audio unit: {exc}") from exc


def _trim_silence(segment: AudioSegment, threshold_dbfs: int) -> AudioSegment:
    duration = len(segment)
    if duration == 0:
        return segment

    start_trim = detect_leading_silence(segment, silence_threshold=threshold_dbfs)
    end_trim = detect_leading_silence(segment.reverse(), silence_threshold=threshold_dbfs)

    # Kalau seluruh segmen "hening" menurut ambang ini, start/end trim bisa
    # saling menimpa (start_trim + end_trim > duration) -- pertahankan
    # segmen aslinya utuh daripada memangkas jadi durasi negatif.
    if start_trim + end_trim >= duration:
        return segment

    return segment[start_trim : duration - end_trim]


def _normalize_volume(segment: AudioSegment) -> AudioSegment:
    if len(segment) == 0:
        return segment
    return segment.normalize()


def compose(segments: list[AudioSegment], crossfade_ms: int, silence_threshold_dbfs: int) -> AudioSegment:
    if not segments:
        raise AudioProcessingError("Tidak ada segmen audio untuk digabung.")

    processed = [_normalize_volume(_trim_silence(seg, silence_threshold_dbfs)) for seg in segments]
    processed = [seg for seg in processed if len(seg) > 0] or processed

    result = processed[0]
    for seg in processed[1:]:
        # Crossfade tidak boleh lebih panjang dari separuh durasi segmen
        # mana pun yang disambung -- pydub melempar error kalau dipaksakan
        # pada segmen yang sangat pendek (mis. rekaman satu huruf vokal).
        safe_crossfade = max(0, min(crossfade_ms, len(result) // 2, len(seg) // 2))
        try:
            result = result.append(seg, crossfade=safe_crossfade)
        except Exception as exc:
            raise AudioProcessingError(f"Gagal menggabungkan segmen audio: {exc}") from exc

    return result.set_frame_rate(22050).set_channels(1)


def export_wav(segment: AudioSegment) -> bytes:
    buffer = io.BytesIO()
    try:
        segment.export(buffer, format="wav")
    except Exception as exc:
        raise AudioProcessingError(f"Gagal mengekspor audio hasil: {exc}") from exc
    return buffer.getvalue()
