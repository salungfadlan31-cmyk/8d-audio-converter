import sys
import os
import time
import uuid
import shutil
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Path setup – add the project root so we can import the existing Python
# audio engine (effects/, utils/, settings.py) without modification.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # 8d-slow-reverb-main/
sys.path.insert(0, str(PROJECT_ROOT))

from pydub import AudioSegment

BASE_DIR   = Path(__file__).resolve().parent
UPLOADS    = BASE_DIR / "uploads"
OUTPUTS    = BASE_DIR / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav"}
MAX_FILE_SIZE      = 50 * 1024 * 1024  # 50 MB
FILE_TTL_SECONDS   = 300               # 5 menit (otomatis hapus jika tidak di-download/ditinggal)
DOWNLOAD_GRACE_SEC = 20                # 20 detik grace period setelah download mulai

# ---------------------------------------------------------------------------
# Background periodic cleanup (Hapus file yang berumur > 5 menit)
# ---------------------------------------------------------------------------
async def periodic_cleanup_task():
    """Berjalan di background setiap 30 detik untuk menghapus file > 5 menit."""
    while True:
        try:
            now = time.time()
            cutoff = now - FILE_TTL_SECONDS
            for directory in [UPLOADS, OUTPUTS]:
                for item in directory.glob("*"):
                    if item.is_file() and item.name != ".gitkeep":
                        try:
                            if item.stat().st_mtime < cutoff:
                                item.unlink()
                                print(f"[AutoClean 5m] File expired dihapus: {item.name}")
                        except Exception as e:
                            print(f"[AutoClean] Gagal hapus {item.name}: {e}")
        except Exception as e:
            print(f"[AutoClean] Error background cleaner: {e}")
        await asyncio.sleep(30)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: jalankan background auto cleaner
    cleanup_task = asyncio.create_task(periodic_cleanup_task())
    yield
    # Shutdown: batalkan task secara rapi
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="8D Audio Converter API",
    version="1.1.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS – allow Next.js dev server and production origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://8d-audio-converter-pi.vercel.app",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve processed audio files as static content (untuk preview audio player)
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS)), name="outputs")


# ---------------------------------------------------------------------------
# Helper: run the 8D processing pipeline
# ---------------------------------------------------------------------------
def process_audio(input_path: Path, output_path: Path) -> None:
    """
    Runs the full 8D + slow + reverb pipeline using the existing engine.
    """
    import importlib
    import settings as _settings

    original_input  = _settings.inputFile
    original_output = _settings.outputFile

    # Strip extension from paths – the engine appends .mp3 / .wav itself
    _settings.inputFile  = str(input_path.with_suffix(""))
    _settings.outputFile = str(output_path.with_suffix(""))

    try:
        import utils.loadSound  as _loadSound
        import effects.effect8d as _effect8d
        import effects.slow     as _slow
        import effects.reverb   as _reverb
        import utils.saveSound  as _saveSound

        importlib.reload(_loadSound)
        importlib.reload(_effect8d)
        importlib.reload(_slow)
        importlib.reload(_reverb)
        importlib.reload(_saveSound)

        from utils.loadSound  import loadSound
        from effects.effect8d import effect8d
        from effects.slow     import effectSlowedDown
        from effects.reverb   import effectReverb
        from utils.saveSound  import saveSound

        # --- Pipeline (sesuai original main.py) ---
        sound                              = loadSound()
        sound8d                            = effect8d(sound)
        sound8dAndSlowedDown               = effectSlowedDown(sound8d)
        sound8dSlowedDownReverbed, sr      = effectReverb(sound8dAndSlowedDown)
        saveSound(sound8dSlowedDownReverbed, sr)

    finally:
        _settings.inputFile  = original_input
        _settings.outputFile = original_output


def cleanup_files(*paths: Path) -> None:
    """Hapus file secara aman tanpa throw error."""
    for p in paths:
        try:
            if p.exists() and p.name != ".gitkeep":
                p.unlink()
        except Exception:
            pass


async def delayed_delete_file(file_path: Path, delay_seconds: int = DOWNLOAD_GRACE_SEC) -> None:
    """
    Menghapus file setelah waktu jeda (grace period) agar proses streaming download
    ke browser user selesai 100% sebelum file fisik dihapus dari disk.
    """
    await asyncio.sleep(delay_seconds)
    try:
        if file_path.exists() and file_path.name != ".gitkeep":
            file_path.unlink()
            print(f"[AutoClean Download] Sukses menghapus file setelah di-download: {file_path.name}")
    except Exception as e:
        print(f"[AutoClean Download] Gagal hapus {file_path.name}: {e}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "8D Audio Converter API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/process")
async def process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    # --- Validasi tipe file ---
    original_name = file.filename or "audio"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe file '{ext}' tidak didukung. Hanya MP3 dan WAV yang diperbolehkan.",
        )

    # --- Validasi ukuran file (Max 50MB) ---
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File terlalu besar. Maksimal ukuran file adalah 50 MB.",
        )

    # --- Simpan file upload sementara ---
    job_id     = uuid.uuid4().hex
    input_path = UPLOADS / f"{job_id}{ext}"
    input_path.write_bytes(content)

    # Output selalu berformat MP3
    stem        = Path(original_name).stem
    output_path = OUTPUTS / f"{job_id}_{stem}_8d"

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, process_audio, input_path, output_path)
    except Exception as exc:
        cleanup_files(input_path)
        raise HTTPException(
            status_code=500,
            detail=f"Pemrosesan audio gagal: {str(exc)}",
        )

    final_mp3 = output_path.with_suffix(".mp3")
    if not final_mp3.exists():
        cleanup_files(input_path)
        raise HTTPException(status_code=500, detail="Pemrosesan selesai tapi file output tidak ditemukan.")

    # Jadwalkan pembersihan langsung untuk input upload sementara
    background_tasks.add_task(cleanup_files, input_path)

    file_url = f"/outputs/{final_mp3.name}"
    return JSONResponse({
        "success":   True,
        "file_url":  file_url,
        "file_name": final_mp3.name,
        "original":  original_name,
    })


@app.get("/api/download/{filename}")
async def download_file(filename: str, background_tasks: BackgroundTasks):
    """
    Mengunduh file MP3 hasil konversi dan menjadwalkan penghapusan otomatis
    setelah 20 detik (agar browser selesai download sebelum file dihapus).
    """
    safe_name = Path(filename).name
    file_path = OUTPUTS / safe_name

    if not file_path.exists():
        raise HTTPException(
            status_code=404,
            detail="File audio sudah tidak tersedia atau telah otomatis dibersihkan.",
        )

    # Auto clean setelah download (diberi jeda 20 detik)
    background_tasks.add_task(delayed_delete_file, file_path, delay_seconds=DOWNLOAD_GRACE_SEC)

    return FileResponse(
        path=str(file_path),
        filename=safe_name,
        media_type="audio/mpeg",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )


@app.post("/api/cleanup/{filename}")
async def manual_cleanup(filename: str):
    """
    Dijalankan saat user klik 'Convert Another Audio' atau menutup browser.
    Langsung menghapus file dari disk server.
    """
    safe_name = Path(filename).name
    file_path = OUTPUTS / safe_name
    cleanup_files(file_path)
    return {"success": True, "message": f"Cleaned up {safe_name}"}
