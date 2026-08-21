# BBM Service — Madurese TTS Speech Service

Layanan internal Python yang dipanggil oleh `bbm-backend` (Laravel) untuk fitur
text-to-speech (TTS) bahasa Madura. Bukan API publik — hanya dipanggil
server-to-server dari Laravel, mengikuti arsitektur:

```
Nuxt (bbm-frontend)
      |
      v
Laravel (bbm-backend) -- gateway utama, pemilik data (users, tts_recordings, MinIO)
      |
      v  GET /api/v2/tts/units (token internal, lihat EnsureInternalServiceToken)
bbm-service (layanan ini) -- TTS engine
      |
      v
  Audio (WAV)
```

Laravel tetap satu-satunya pemilik data dan gateway yang diakses frontend.
Layanan ini murni engine sintesis: tidak punya database sendiri, tidak
menyentuh MinIO secara langsung — semua metadata unit & file audio diambil
lewat API backend.

## Kenapa layanan terpisah, bukan ditambahkan ke Laravel

Pemrosesan audio (trim silence, normalisasi, crossfade antar-unit) lebih
alami dikerjakan di Python (pydub). Memisahkannya juga berarti engine bisa
diganti/ditingkatkan (lihat roadmap Fase 3/4) tanpa mengubah kontrak API ke
Laravel/frontend sama sekali.

## Arsitektur kode

```
app/
├── main.py                        # FastAPI app + exception handlers
├── config.py                      # Settings (pydantic-settings, baca .env)
├── schemas.py                     # Model data (TtsRequest, UnitInfo, SynthesisPlan)
├── exceptions.py                  # Hierarki error domain (lihat "Penanganan error")
├── routers/tts.py                 # Endpoint HTTP tipis, tidak ada logika bisnis
├── services/
│   ├── text_normalizer.py         # Mirror normalizeDiacritics() Laravel
│   ├── syllable_splitter.py       # Port FsaSyllableService.php (FSA 2 tingkat)
│   ├── unit_selector.py           # Algoritma hybrid unit selection (lihat di bawah)
│   ├── audio_composer.py          # trim -> normalize -> crossfade -> export WAV
│   └── synthesis_service.py       # Orkestrasi: cache -> pilih unit -> gabung -> cache
├── repositories/recording_repository.py  # Klien HTTP async ke bbm-backend
└── cache/tts_cache.py             # Cache file, dikunci dari hash(teks ternormalisasi)
```

Router sengaja setipis mungkin — semua alur nyata ada di `synthesis_service.py`
supaya bisa diuji tanpa menjalankan server HTTP sungguhan (lihat `tests/`).

## Algoritma unit selection (Fase 1 — hybrid, bukan neural)

Untuk tiap kata dalam teks, dicoba berurutan sebelum menyerah:

1. **Exact match** — rekaman utuh untuk kata itu sendiri.
2. **Suku kata** — kata dipecah lewat `syllable_splitter` (FSA, identik
   dengan `FsaSyllableService.php` — lihat `tests/test_syllable_splitter.py`
   yang memvalidasi paritas terhadap output PHP asli), tiap suku kata dicari
   rekamannya.
3. **Huruf** — kalau satu suku kata tertentu belum direkam, suku kata itu
   dipecah lagi jadi huruf tunggal.
4. **Gagal** — kalau masih ada segmen yang tidak ditemukan di level huruf
   sekalipun, seluruh request ditolak dengan `MissingAudioUnitsError` (422,
   berisi daftar persis segmen yang hilang). Sistem ini SENGAJA tidak pernah
   mengembalikan audio parsial yang diam-diam bolong.

Pencarian tidak peka diakritik (â/è disamakan ke a/e, sama seperti
pencarian kamus di backend) — lihat `text_normalizer.py`.

## Pipeline audio (audio_composer.py)

Tiap unit yang terpilih: trim hening di ujung → normalisasi volume →
disambung berurutan dengan crossfade singkat (default 25ms, otomatis
dipangkas kalau segmennya lebih pendek dari itu supaya tidak error pada
rekaman huruf tunggal yang sangat pendek) → di-resample ke 22050Hz mono →
diekspor sebagai WAV.

## Cache

Hasil komposisi disimpan di `CACHE_DIR`, dikunci dari SHA-256 teks yang
sudah dinormalisasi. Untuk aplikasi edukasi seperti BBM, teks yang sama
kemungkinan besar diminta berulang kali oleh siswa berbeda — cache ini
membuat permintaan kedua dst. tidak perlu memanggil backend/MinIO sama
sekali (`X-Tts-Cached: true` di response header).

## Penanganan error

Semua error domain punya exception khusus (`app/exceptions.py`) yang
dipetakan ke status HTTP + pesan yang jelas oleh handler di `main.py`:

| Exception | Status | Kapan terjadi |
|---|---|---|
| `EmptyTextError` | 400 | Teks kosong/hanya spasi setelah di-strip |
| `MissingAudioUnitsError` | 422 | Ada segmen yang tidak punya unit audio di level manapun (lihat `data.missing_segments`) |
| `BackendUnavailableError` | 503 | bbm-backend tidak bisa dihubungi (daftar unit atau file audio) |
| `AudioProcessingError` | 500 | File audio korup/gagal didekode/digabung/diekspor |

Validasi input dasar (teks kosong string, panjang berlebihan) sudah ditolak
lebih awal oleh Pydantic (`TtsRequest`, 422 bawaan FastAPI) sebelum sempat
menyentuh logika domain sama sekali.

## Roadmap bertahap

- **Fase 1 (sudah diimplementasikan)** — unit-selection dari korpus
  huruf/suku kata/kata yang direkam lewat Lab Bahasa (`bbm-frontend`
  `/admin/lab-bahasa`, super_admin saja).
- **Fase 2** — perluas korpus dengan kata utuh (exact match akan makin
  sering kena, mengurangi ketergantungan pada fallback suku kata/huruf).
- **Fase 3** — kumpulkan korpus kalimat (500–1.000+ rekaman kalimat
  lengkap) untuk eksperimen model neural (mis. Piper/VITS, custom phoneme
  Madura).
- **Fase 4** — kalau korpus sudah besar (5.000–10.000+ kalimat), latih
  model neural TTS Madura yang bisa membaca kalimat yang belum pernah
  direkam secara natural.

Menambah engine baru di Fase 3/4 tidak akan mengubah kontrak `POST /tts`
sama sekali dari sisi Laravel/frontend — cukup tambah cabang di
`synthesis_service.py` yang memilih engine berdasarkan ketersediaan model.

## Menjalankan secara lokal

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements-dev.txt
cp .env.example .env     # isi BACKEND_INTERNAL_TOKEN sama persis dengan
                          # TTS_INTERNAL_TOKEN di .env bbm-backend
uvicorn app.main:app --reload --port 8010
```

`GET /health` untuk memastikan layanan hidup. `bbm-backend` harus sudah
jalan (lihat `../bbm-backend/CLAUDE.md`) karena layanan ini bergantung
padanya untuk daftar unit audio.

## Menjalankan test

```bash
pytest            # 43 test: unit test murni (tidak perlu backend/MinIO jalan)
ruff check app tests
```

Test dipisah rapi per layer: `text_normalizer`/`syllable_splitter` (paritas
dengan PHP), `unit_selector` (logika hybrid selection dengan unit
tersedia/hilang), `audio_composer` (memakai tone sintetis dari
`pydub.generators`, tidak perlu file audio asli), `synthesis_service`
(orkestrasi penuh dengan repository & cache palsu), dan `test_api.py`
(level HTTP lewat `TestClient` + dependency override).

## Endpoint

- `GET /health` — health check.
- `POST /tts` — body `{"text": "..."}`, mengembalikan audio WAV langsung
  (`Content-Type: audio/wav`) beserta header `X-Tts-Cached`,
  `X-Tts-Engine`, `X-Tts-Segments`. Error mengembalikan JSON
  `{"status": "error", "message": "...", "data": {...}}`.
