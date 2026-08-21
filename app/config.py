"""
Konfigurasi lewat pydantic-settings (baca dari .env, bisa dioverride lewat
environment variable asli saat deploy) -- satu sumber kebenaran untuk semua
nilai yang bisa berubah antar lingkungan (dev/production), bukan hardcoded
di tengah kode service/repository.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # bbm-backend (Laravel) -- sumber daftar unit audio aktif + file audionya.
    backend_base_url: str = "http://localhost:8005"
    # Token internal (bukan token pengguna) -- dicek oleh backend di endpoint
    # GET /api/v2/tts/units supaya korpus rekaman suara tidak bocor publik.
    backend_internal_token: str = ""

    cache_dir: str = "storage/cache"

    # Durasi crossfade antar-unit saat digabung -- dijaga tetap pendek jika
    # tidak, hasil terdengar seperti dua rekaman ditempel kasar (lihat
    # audio_composer.py, nilai ini juga otomatis dipangkas per-pasangan
    # segmen kalau segmennya lebih pendek dari nilai ini).
    crossfade_ms: int = 25

    # Ambang deteksi hening (dBFS) saat trim leading/trailing silence.
    silence_threshold_dbfs: int = -40

    request_timeout_seconds: float = 10.0

    max_text_length: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
