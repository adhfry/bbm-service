"""Model data (Pydantic) yang dipakai lintas layer service ini."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class TtsRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)


class UnitInfo(BaseModel):
    """Satu baris rekaman aktif dari tts_recordings (lihat bbm-backend)."""

    text: str
    type: str
    audio_url: str


@dataclass(slots=True)
class PlanItem:
    """Satu unit audio yang akan diambil & digabung, dalam urutan pemakaian."""

    segment: str
    audio_url: str


@dataclass(slots=True)
class SynthesisPlan:
    """
    Hasil unit selection: daftar PlanItem terurut yang siap diambil audionya
    dan digabung -- lihat unit_selector.py untuk cara plan ini dibangun.
    """

    items: list[PlanItem] = field(default_factory=list)

    @property
    def segments_used(self) -> list[str]:
        return [item.segment for item in self.items]
