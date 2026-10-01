import os
import subprocess
import tempfile
from os.path import isfile

from pydub import AudioSegment
from settings import *

try:
    import imageio_ffmpeg

    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()

    # Beri tahu Pydub executable FFmpeg yang harus digunakan.
    AudioSegment.converter = FFMPEG_EXE

    # Tambahkan folder FFmpeg ke PATH agar subprocess juga bisa menemukannya.
    ffmpeg_dir = os.path.dirname(FFMPEG_EXE)
    current_path = os.environ.get("PATH", "")

    if ffmpeg_dir not in current_path.split(os.pathsep):
        os.environ["PATH"] = f"{ffmpeg_dir}{os.pathsep}{current_path}"

except Exception as e:
    print(f"[FFmpeg] Gagal menyiapkan imageio-ffmpeg: {e}")
    FFMPEG_EXE = "ffmpeg"


def loadSound():
    """
    Membaca file input MP3/WAV.

    Untuk MP3:
    MP3 -> FFmpeg -> WAV -> Pydub

    Cara ini menghindari kebutuhan ffprobe dari
    AudioSegment.from_mp3().
    """

    mp3_file = inputFile + ".mp3"
    wav_file = inputFile + ".wav"

    # ---------------------------------------------------------
    # WAV langsung
    # ---------------------------------------------------------
    if isfile(wav_file):
        print(f"[Audio] Loading WAV: {wav_file}")
        return AudioSegment.from_wav(wav_file)

    # ---------------------------------------------------------
    # MP3 -> WAV menggunakan FFmpeg
    # ---------------------------------------------------------
    if isfile(mp3_file):
        print(f"[Audio] Loading MP3: {mp3_file}")
        print(f"[FFmpeg] Using: {FFMPEG_EXE}")

        # Buat file WAV sementara.
        temp_wav = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )

        temp_wav_path = temp_wav.name
        temp_wav.close()

        try:
            command = [
                FFMPEG_EXE,
                "-y",
                "-i",
                mp3_file,
                "-vn",
                "-acodec",
                "pcm_s16le",
                temp_wav_path,
            ]

            print("[FFmpeg] Decoding MP3 to WAV...")

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
                    f"FFmpeg gagal membaca file MP3. "
                    f"Exit code: {result.returncode}"
                )

            if not isfile(temp_wav_path):
                raise RuntimeError(
                    "FFmpeg selesai tetapi file WAV hasil decode tidak ditemukan."
                )

            print("[Audio] WAV decode berhasil.")

            # Sekarang baca WAV.
            # Tidak menggunakan from_mp3(), sehingga ffprobe
            # tidak diperlukan untuk proses MP3 ini.
            sound = AudioSegment.from_wav(temp_wav_path)

            return sound

        finally:
            # Hapus file WAV sementara.
            try:
                if isfile(temp_wav_path):
                    os.remove(temp_wav_path)
            except Exception as cleanup_error:
                print(
                    f"[Audio] Warning: gagal menghapus temporary WAV: "
                    f"{cleanup_error}"
                )

    # ---------------------------------------------------------
    # File tidak ditemukan
    # ---------------------------------------------------------
    print("Source music file not found!")
    raise FileNotFoundError(
        f"File input tidak ditemukan: {mp3_file} atau {wav_file}"
    )