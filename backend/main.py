import sys
import os
import time
import tempfile
import asyncio
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# ---------------------------------------------------------------------------
# Path setup – add project root so we can import the existing Python
# audio engine (effects/, utils/, settings.py) without modification.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # 8d-slow-reverb-main/
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# FFmpeg configuration via imageio-ffmpeg:
# Ensures static Linux binary is used on Vercel production,
# and platform binary is used in local development, without requiring
# manual FFmpeg installation on the host system.
# ---------------------------------------------------------------------------
from pydub import AudioSegment

try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    AudioSegment.converter = ffmpeg_exe
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{os.environ.get('PATH', '')}"
    print(f"[FFmpeg] Configured binary at: {ffmpeg_exe}")
except Exception as e:
    print(f"[FFmpeg] Notice: Could not initialize imageio_ffmpeg ({e}). Falling back to system FFmpeg.")

# ---------------------------------------------------------------------------
# Constants
# Vercel Serverless Function incoming/outgoing payload limit is 4.5 MB.
# ---------------------------------------------------------------------------
ALLOWED_EXTENSIONS = {".mp3", ".wav"}
MAX_FILE_SIZE      = int(4.5 * 1024 * 1024)  # 4.5 MB (Vercel Function payload limit)

# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------
app = FastAPI(
    title="8D Audio Converter API",
    version="1.2.0",
)

# ---------------------------------------------------------------------------
# CORS – for local standalone development
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "https://8d-audio-converter-4ls6.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helper: run the 8D processing pipeline using the existing engine
# ---------------------------------------------------------------------------
def process_audio(input_path: Path, output_path: Path) -> None:
    """
    Runs the full 8D + slow + reverb pipeline using the existing engine.
    File paths are in temporary directories, keeping the filesystem clean.
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
async def process(file: UploadFile = File(...)):
    """
    One-Shot Processing Endpoint:
    Menerima audio, memproses via pipeline 8D, dan langsung mengembalikan file MP3
    sebagai binary response (audio/mpeg).
    
    Arsitektur ini menghilangkan ketergantungan pada disk lokal antar-request,
    sehingga 100% aman untuk lingkungan serverless Vercel yang stateless dan ephemeral.
    """
    # 1. Validasi tipe file
    original_name = file.filename or "audio"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe file '{ext}' tidak didukung. Hanya MP3 dan WAV yang diperbolehkan.",
        )

    # 2. Validasi ukuran file (Max 4.5 MB sesuai batas Vercel Function payload)
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File terlalu besar. Maksimal ukuran file adalah 4.5 MB untuk serverless processing.",
        )

    stem = Path(original_name).stem
    output_filename = f"{stem}_8d.mp3"

    # 3. Proses di temporary directory (writable di Vercel /tmp)
    # Semua file (input, intermediate WAV, output MP3) otomatis dibersihkan saat blok selesai.
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        input_path = temp_dir_path / f"input{ext}"
        input_path.write_bytes(content)

        output_path = temp_dir_path / f"{stem}_8d"

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, process_audio, input_path, output_path)
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Pemrosesan audio gagal: {str(exc)}",
            )

        final_mp3 = output_path.with_suffix(".mp3")
        if not final_mp3.exists():
            raise HTTPException(
                status_code=500,
                detail="Pemrosesan selesai namun file output tidak ditemukan.",
            )

        mp3_bytes = final_mp3.read_bytes()

    # 4. Return one-shot response langsung sebagai audio/mpeg
    return Response(
        content=mp3_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"',
            "X-Filename": output_filename,
            "X-Original-Filename": original_name,
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Access-Control-Expose-Headers": "Content-Disposition, X-Filename, X-Original-Filename",
        },
    )


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Fallback endpoint untuk kompatibilitas.
    Pada arsitektur one-shot, file audio sudah langsung berada di browser client.
    """
    return JSONResponse(
        status_code=200,
        content={
            "message": "File audio sudah di-stream langsung ke browser saat pemrosesan selesai."
        },
    )


@app.post("/api/cleanup/{filename}")
async def manual_cleanup(filename: str):
    """
    Fallback cleanup endpoint untuk kompatibilitas.
    Pada arsitektur one-shot, disk server sudah langsung bersih via TemporaryDirectory.
    """
    return {"success": True, "message": f"Cleaned up {filename}"}
