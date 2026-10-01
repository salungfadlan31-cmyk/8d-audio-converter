import sys
import os
import asyncio
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware


# ---------------------------------------------------------------------------
# Path setup
#
# Project structure:
#
# 8d-slow-reverb-main/
# ├── backend/
# │   └── main.py
# ├── effects/
# ├── utils/
# └── settings.py
#
# main.py berada di backend/, jadi parent.parent adalah project root.
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# FFmpeg configuration
#
# FastAPI Cloud tidak menyediakan FFmpeg/ffprobe sebagai system executable.
#
# imageio-ffmpeg menyediakan binary FFmpeg yang bisa digunakan langsung
# oleh aplikasi Python.
#
# IMPORTANT:
# - Kita menggunakan FFmpeg dari imageio-ffmpeg.
# - Kita TIDAK membuat ffprobe palsu.
# - Pemrosesan input/output akan kita sesuaikan agar tidak membutuhkan
#   executable ffprobe.
# ---------------------------------------------------------------------------

from pydub import AudioSegment

try:
    import imageio_ffmpeg

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    # Beri tahu Pydub lokasi FFmpeg yang benar.
    AudioSegment.converter = ffmpeg_exe

    # Tambahkan folder FFmpeg ke PATH supaya library lain yang
    # menjalankan "ffmpeg" dapat menemukannya.
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)

    current_path = os.environ.get("PATH", "")

    if ffmpeg_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = (
            f"{ffmpeg_dir}{os.pathsep}{current_path}"
            if current_path
            else ffmpeg_dir
        )

    print(f"[FFmpeg] Configured binary: {ffmpeg_exe}")
    print(f"[FFmpeg] Directory: {ffmpeg_dir}")

except Exception as exc:
    print(
        f"[FFmpeg] WARNING: Could not initialize imageio-ffmpeg: {exc}"
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = {
    ".mp3",
    ".wav",
}

# Vercel/serverless request payload limit yang digunakan oleh aplikasi.
MAX_FILE_SIZE = int(4.5 * 1024 * 1024)


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="8D Audio Converter API",
    version="1.2.0",
)


# ---------------------------------------------------------------------------
# CORS
#
# Diperlukan untuk local development dan production frontend.
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
# Helper: process audio
#
# Menjalankan pipeline asli:
#
# input
#   ↓
# loadSound()
#   ↓
# effect8d()
#   ↓
# effectSlowedDown()
#   ↓
# effectReverb()
#   ↓
# saveSound()
#
# Algoritma audio tidak diubah di sini.
# ---------------------------------------------------------------------------

def process_audio(input_path: Path, output_path: Path) -> None:
    """
    Runs the existing 8D + slow + reverb audio pipeline.

    All input/output files are stored in a temporary directory.
    """

    import importlib
    import settings as _settings

    # Simpan settings asli supaya setelah request selesai,
    # konfigurasi global dikembalikan seperti semula.
    original_input = _settings.inputFile
    original_output = _settings.outputFile

    # Engine lama menggunakan settings.inputFile/outputFile
    # tanpa extension karena masing-masing utility menambahkan
    # .mp3 / .wav sendiri.
    _settings.inputFile = str(input_path.with_suffix(""))
    _settings.outputFile = str(output_path.with_suffix(""))

    try:
        # Import modules yang digunakan oleh engine.
        import utils.loadSound as _loadSound
        import effects.effect8d as _effect8d
        import effects.slow as _slow
        import effects.reverb as _reverb
        import utils.saveSound as _saveSound

        # Reload agar perubahan settings.inputFile/outputFile
        # digunakan oleh module yang sudah pernah di-import.
        importlib.reload(_loadSound)
        importlib.reload(_effect8d)
        importlib.reload(_slow)
        importlib.reload(_reverb)
        importlib.reload(_saveSound)

        from utils.loadSound import loadSound
        from effects.effect8d import effect8d
        from effects.slow import effectSlowedDown
        from effects.reverb import effectReverb
        from utils.saveSound import saveSound

        # ---------------------------------------------------------------
        # ORIGINAL AUDIO PIPELINE
        # ---------------------------------------------------------------

        sound = loadSound()

        sound8d = effect8d(sound)

        sound8dAndSlowedDown = effectSlowedDown(sound8d)

        sound8dSlowedDownReverbed, sample_rate = effectReverb(
            sound8dAndSlowedDown
        )

        saveSound(
            sound8dSlowedDownReverbed,
            sample_rate,
        )

    finally:
        # Selalu kembalikan settings asli.
        _settings.inputFile = original_input
        _settings.outputFile = original_output


# ---------------------------------------------------------------------------
# Root endpoint
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {
        "message": "8D Audio Converter API is running"
    }


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok"
    }


# ---------------------------------------------------------------------------
# Main processing endpoint
# ---------------------------------------------------------------------------

@app.post("/api/process")
async def process(file: UploadFile = File(...)):
    """
    One-shot audio processing endpoint.

    Receives MP3/WAV,
    processes 8D + slow + reverb,
    then returns the generated MP3 directly.

    No persistent upload/output directory is required.
    """

    # ---------------------------------------------------------------
    # 1. Validate filename / extension
    # ---------------------------------------------------------------

    original_name = file.filename or "audio"

    ext = Path(original_name).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Tipe file '{ext}' tidak didukung. "
                "Hanya MP3 dan WAV yang diperbolehkan."
            ),
        )

    # ---------------------------------------------------------------
    # 2. Read uploaded file
    # ---------------------------------------------------------------

    content = await file.read()

    # ---------------------------------------------------------------
    # 3. Validate file size
    # ---------------------------------------------------------------

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=(
                "File terlalu besar. "
                "Maksimal ukuran file adalah 4.5 MB."
            ),
        )

    stem = Path(original_name).stem

    output_filename = f"{stem}_8d.mp3"

    # ---------------------------------------------------------------
    # 4. Temporary processing directory
    # ---------------------------------------------------------------

    with tempfile.TemporaryDirectory() as temp_dir:

        temp_dir_path = Path(temp_dir)

        input_path = temp_dir_path / f"input{ext}"

        output_path = temp_dir_path / f"{stem}_8d"

        # Tulis file upload ke temporary directory.
        input_path.write_bytes(content)

        try:
            # Jalankan audio processing di thread terpisah
            # agar event loop FastAPI tidak terblokir.
            loop = asyncio.get_running_loop()

            await loop.run_in_executor(
                None,
                process_audio,
                input_path,
                output_path,
            )

        except Exception as exc:
            # Log error lengkap ke server untuk debugging.
            print(
                f"[PROCESS ERROR] "
                f"{type(exc).__name__}: {exc}"
            )

            raise HTTPException(
                status_code=500,
                detail=f"Pemrosesan audio gagal: {exc}",
            )

        # -----------------------------------------------------------
        # 5. Verify output
        # -----------------------------------------------------------

        final_mp3 = output_path.with_suffix(".mp3")

        if not final_mp3.exists():
            raise HTTPException(
                status_code=500,
                detail=(
                    "Pemrosesan selesai namun "
                    "file output tidak ditemukan."
                ),
            )

        # Baca MP3 sebelum TemporaryDirectory dihapus.
        mp3_bytes = final_mp3.read_bytes()

    # ---------------------------------------------------------------
    # 6. Return generated MP3
    # ---------------------------------------------------------------

    return Response(
        content=mp3_bytes,
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": (
                f'attachment; filename="{output_filename}"'
            ),
            "X-Filename": output_filename,
            "X-Original-Filename": original_name,
            "Cache-Control": (
                "no-store, no-cache, must-revalidate"
            ),
            "Access-Control-Expose-Headers": (
                "Content-Disposition, "
                "X-Filename, "
                "X-Original-Filename"
            ),
        },
    )


# ---------------------------------------------------------------------------
# Legacy download endpoint
# ---------------------------------------------------------------------------

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """
    Compatibility endpoint.

    Audio is already returned directly by /api/process,
    so there is no persistent output file to download.
    """

    return JSONResponse(
        status_code=200,
        content={
            "message": (
                "File audio sudah di-stream langsung "
                "ke browser saat pemrosesan selesai."
            )
        },
    )


# ---------------------------------------------------------------------------
# Legacy cleanup endpoint
# ---------------------------------------------------------------------------

@app.post("/api/cleanup/{filename}")
async def manual_cleanup(filename: str):
    """
    Compatibility endpoint.

    TemporaryDirectory automatically removes temporary files
    after processing is finished.
    """

    return {
        "success": True,
        "message": f"Cleaned up {filename}",
    }