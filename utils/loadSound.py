import os
import subprocess
import tempfile
import wave
from os.path import isfile

from pydub import AudioSegment
from settings import *


try:
    import imageio_ffmpeg

    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

    ffmpeg_dir = os.path.dirname(FFMPEG_EXE)
    current_path = os.environ.get("PATH", "")

    if ffmpeg_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}"

    print(f"[FFmpeg] Using: {FFMPEG_EXE}")

except Exception as e:
    print(f"[FFmpeg] Failed to initialize imageio-ffmpeg: {e}")
    FFMPEG_EXE = "ffmpeg"


def wav_to_audio_segment(wav_path):
    """
    Membaca WAV secara langsung menggunakan modul wave Python.

    Tidak menggunakan:
        AudioSegment.from_wav()

    karena Pydub dapat mencoba mencari ffprobe.
    """

    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        frames = wav_file.readframes(wav_file.getnframes())

    return AudioSegment(
        data=frames,
        sample_width=sample_width,
        frame_rate=sample_rate,
        channels=channels,
    )


def decode_mp3_to_wav(mp3_path, wav_path):
    """
    Decode MP3 menjadi WAV menggunakan FFmpeg secara langsung.

    Tidak menggunakan ffprobe.
    """

    command = [
        FFMPEG_EXE,
        "-y",
        "-i",
        str(mp3_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        str(wav_path),
    ]

    print("[FFmpeg] Decoding MP3 -> WAV...")

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        print("[FFmpeg] Error:")
        print(result.stderr)

        raise RuntimeError(
            f"FFmpeg gagal melakukan decode MP3. "
            f"Exit code: {result.returncode}"
        )

    if not isfile(wav_path):
        raise RuntimeError(
            "FFmpeg selesai tetapi file WAV tidak ditemukan."
        )

    print("[FFmpeg] MP3 berhasil diubah menjadi WAV.")


def loadSound():
    """
    Load audio dari MP3 atau WAV.

    MP3:
        MP3 -> FFmpeg -> WAV -> wave -> AudioSegment

    WAV:
        WAV -> wave -> AudioSegment

    Tidak menggunakan ffprobe.
    """

    mp3_file = inputFile + ".mp3"
    wav_file = inputFile + ".wav"

    # =========================================================
    # WAV
    # =========================================================

    if isfile(wav_file):
        print(f"[Audio] Loading WAV: {wav_file}")

        return wav_to_audio_segment(wav_file)

    # =========================================================
    # MP3
    # =========================================================

    if isfile(mp3_file):
        print(f"[Audio] Loading MP3: {mp3_file}")

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        ) as temp_file:

            temp_wav = temp_file.name

        try:
            decode_mp3_to_wav(
                mp3_file,
                temp_wav,
            )

            sound = wav_to_audio_segment(temp_wav)

            print(
                "[Audio] AudioSegment berhasil dibuat "
                "tanpa menggunakan ffprobe."
            )

            return sound

        finally:
            try:
                if isfile(temp_wav):
                    os.remove(temp_wav)
            except Exception as cleanup_error:
                print(
                    "[Audio] Warning: gagal menghapus "
                    f"temporary WAV: {cleanup_error}"
                )

    # =========================================================
    # File tidak ditemukan
    # =========================================================

    raise FileNotFoundError(
        f"Source music file not found: "
        f"{mp3_file} atau {wav_file}"
    )