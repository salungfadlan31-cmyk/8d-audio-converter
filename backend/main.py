import sys
import os
import uuid
import shutil
import asyncio
from pathlib import Path
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

# ---------------------------------------------------------------------------
# App configuration
# ---------------------------------------------------------------------------
app = FastAPI(title="8D Audio Converter API", version="1.0.0")

BASE_DIR   = Path(__file__).resolve().parent
UPLOADS    = BASE_DIR / "uploads"
OUTPUTS    = BASE_DIR / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".mp3", ".wav"}
MAX_FILE_SIZE      = 50 * 1024 * 1024  # 50 MB

# ---------------------------------------------------------------------------
# CORS – allow Next.js dev server and production origin
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve processed audio files as static content
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS)), name="outputs")


# ---------------------------------------------------------------------------
# Helper: run the 8D processing pipeline
# ---------------------------------------------------------------------------
def process_audio(input_path: Path, output_path: Path) -> None:
    """
    Runs the full 8D + slow + reverb pipeline using the existing engine.

    We import the engine modules *inside* this function so that each call
    gets a fresh import context (important when settings are monkey-patched).
    """
    import importlib

    # ------------------------------------------------------------------
    # Temporarily override settings so the engine reads/writes OUR files
    # instead of the hard-coded "music" / "music8d" filenames.
    # ------------------------------------------------------------------
    import settings as _settings
    original_input  = _settings.inputFile
    original_output = _settings.outputFile

    # Strip extension from paths – the engine appends .mp3 / .wav itself
    _settings.inputFile  = str(input_path.with_suffix(""))
    _settings.outputFile = str(output_path.with_suffix(""))

    try:
        # Force-reload modules that cache settings at import time
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

        # --- Pipeline (identical to original main.py) ---
        sound                              = loadSound()
        sound8d                            = effect8d(sound)
        sound8dAndSlowedDown               = effectSlowedDown(sound8d)
        sound8dSlowedDownReverbed, sr      = effectReverb(sound8dAndSlowedDown)
        saveSound(sound8dSlowedDownReverbed, sr)

    finally:
        # Always restore original settings
        _settings.inputFile  = original_input
        _settings.outputFile = original_output


def cleanup_files(*paths: Path) -> None:
    """Remove temporary files silently."""
    for p in paths:
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass


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
    # --- Validate extension ---
    original_name = file.filename or "audio"
    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Only MP3 and WAV are accepted.",
        )

    # --- Read & validate size ---
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large. Maximum allowed size is 50 MB.",
        )

    # --- Save upload with a unique name ---
    job_id     = uuid.uuid4().hex
    input_path = UPLOADS / f"{job_id}{ext}"
    input_path.write_bytes(content)

    # Output will always be MP3 (engine converts internally)
    stem        = Path(original_name).stem
    output_path = OUTPUTS / f"{job_id}_{stem}_8d"  # engine appends .mp3

    try:
        # Run synchronously in a thread pool so we don't block the event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, process_audio, input_path, output_path)
    except Exception as exc:
        cleanup_files(input_path)
        raise HTTPException(
            status_code=500,
            detail=f"Audio processing failed: {str(exc)}",
        )

    final_mp3 = output_path.with_suffix(".mp3")
    if not final_mp3.exists():
        cleanup_files(input_path)
        raise HTTPException(status_code=500, detail="Processing completed but output file not found.")

    # Schedule cleanup of the temporary upload (output is kept for download)
    background_tasks.add_task(cleanup_files, input_path)

    file_url = f"/outputs/{final_mp3.name}"
    return JSONResponse({
        "success":   True,
        "file_url":  file_url,
        "file_name": final_mp3.name,
        "original":  original_name,
    })
