# BBM Service — Madurese TTS Speech Service

Layanan internal Python yang dipanggil oleh `bbm-backend` (Laravel) untuk fitur
text-to-speech (TTS) bahasa Madura. Bukan API publik — hanya dipanggil
server-to-server dari Laravel (`POST /api/v2/tts` di backend akan meneruskan
ke layanan ini), mengikuti arsitektur:

```
Nuxt (bbm-frontend)
      |
      v
Laravel (bbm-backend) -- gateway utama
      |
      v
bbm-service (layanan ini) -- TTS engine
      |
      v
  Audio (WAV/MP3)
```

## Kenapa layanan terpisah, bukan ditambahkan ke Laravel

Pemrosesan audio (trim silence, normalisasi, crossfade antar-suku-kata) lebih
alami dikerjakan di Python. Laravel tetap jadi satu-satunya gateway yang
diakses frontend; layanan ini murni engine internal.

## Roadmap bertahap

Dataset yang tersedia sekarang di `bbm-backend` (`syllables`, rekaman per
huruf/suku kata) belum berbentuk dataset TTS neural (butuh korpus kalimat).
Jadi urutan pengembangan:

- **Fase 1 (sekarang → ini)**: Unit-selection TTS. Kalimat dipecah jadi
  huruf/suku kata lewat `FsaSyllableService` (porting dari `bbm-backend`,
  logikanya sama), lalu audio unit yang sesuai digabung (concatenative), bukan
  ditempel mentah -- perlu trim silence + normalisasi volume + crossfade.
- **Fase 2**: Kalau kata utuh sudah punya rekaman asli (exact match), pakai itu
  dulu, baru fallback ke gabungan suku kata kalau belum ada.
- **Fase 3**: Mulai kumpulkan korpus kalimat (500–1.000+ rekaman kalimat
  lengkap) untuk eksperimen model neural (mis. Piper/VITS, custom phoneme
  Madura).
- **Fase 4**: Kalau korpus sudah besar (5.000–10.000+ kalimat), latih model
  neural TTS Madura yang bisa membaca kalimat yang belum pernah direkam.

Layanan ini dirancang supaya di Fase 3/4 nanti tinggal menambah "engine" baru
di belakang endpoint yang sama (`POST /tts`), tanpa mengubah kontrak API ke
Laravel/frontend.

## Menjalankan secara lokal

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

Cek `GET /health` untuk memastikan layanan hidup.

## Status saat ini

Baru skeleton (health check + kontrak endpoint `/tts` yang jujur menjawab
"belum diimplementasikan" -- bukan pura-pura jalan). Penyimpanan audio
(MinIO/S3), skema database unit TTS (`tts_units`, `tts_cache`), dan pipeline
audio (trim/normalize/crossfade) menyusul setelah keputusan penyimpanan &
struktur data dikonfirmasi.
