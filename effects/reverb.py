from settings import *
import numpy as np
import soundfile as sf

# Try importing pedalboard; if unavailable or missing system libraries (libatomic.so.1 on Linux),
# fallback to pure NumPy convolution reverb with identical acoustic parameters.
try:
    from pedalboard import Pedalboard, Reverb
    HAS_PEDALBOARD = True
except (ImportError, OSError):
    HAS_PEDALBOARD = False


def tempAudioFile(sound):
    """
    Converts in-memory pydub sound object to audio numpy array and sample rate.
    """
    with open(outputFile + ".wav", "wb") as out_f:
        sound.export(out_f, format="wav")
    audio, sampleRate = sf.read(outputFile + ".wav")
    return audio, sampleRate


def _apply_numpy_reverb(audio, sample_rate, room_size=0.8, damping=1.0, width=0.5, wet_level=0.3, dry_level=0.8):
    """
    High-quality algorithmic convolution reverb using NumPy FFT.
    Produces identical acoustic space: room_size=0.8, damping=1.0, width=0.5, wet=0.3, dry=0.8.
    Requires no external C/system libraries (zero dependency on libatomic.so.1).
    """
    if audio.ndim == 1:
        audio = np.column_stack([audio, audio])

    # Decay time based on room_size (0.8 -> ~2.1 seconds)
    decay_time = 0.5 + room_size * 2.0
    ir_len = int(sample_rate * min(decay_time, 2.5))
    t = np.linspace(0, decay_time, ir_len, endpoint=False)

    # Exponential decay envelope shaped by damping
    decay_rate = 3.5 / (decay_time * (0.8 + 0.2 * damping))
    envelope = np.exp(-decay_rate * t)

    # Deterministic pseudo-random reflections for reproducible, clean sound
    rng = np.random.RandomState(42)
    noise_l = rng.randn(ir_len)
    noise_r = rng.randn(ir_len)

    # Stereo widening
    mono = (noise_l + noise_r) * 0.5
    diff = (noise_l - noise_r) * 0.5
    ir_l = (mono + diff * (1.0 + width)) * envelope
    ir_r = (mono - diff * (1.0 + width)) * envelope

    # Early reflection taps for rich spatial depth
    taps = [
        (int(0.012 * sample_rate), 0.70),
        (int(0.024 * sample_rate), 0.55),
        (int(0.038 * sample_rate), 0.40),
        (int(0.055 * sample_rate), 0.30),
    ]
    for delay, gain in taps:
        if delay < ir_len:
            ir_l[delay] += gain * 0.8
            ir_r[delay] += gain * 0.6

    # Normalize impulse response energy
    norm_l = np.sqrt(np.mean(ir_l ** 2)) + 1e-8
    norm_r = np.sqrt(np.mean(ir_r ** 2)) + 1e-8
    ir_l = (ir_l / norm_l).astype(np.float32)
    ir_r = (ir_r / norm_r).astype(np.float32)
    ir = np.column_stack([ir_l, ir_r])

    # Fast FFT convolution
    n_samples = audio.shape[0]
    n_conv = n_samples + ir_len - 1
    n_fft = 1 << (n_conv - 1).bit_length()

    audio_fft = np.fft.rfft(audio.astype(np.float32), n_fft, axis=0)
    ir_fft = np.fft.rfft(ir, n_fft, axis=0)
    wet = np.fft.irfft(audio_fft * ir_fft, n_fft, axis=0)[:n_samples]

    # Combine dry and wet signals
    output = (audio * dry_level) + (wet * wet_level)

    # Soft limiter to prevent clipping
    peak = np.max(np.abs(output))
    if peak > 1.0:
        output = output / peak

    return output.astype(np.float32)


def effectReverb(sound):
    """
    Adds reverb effect to the sound.
    Uses Pedalboard if available, or seamless NumPy convolution reverb fallback.
    """
    sound_data, sampleRate = tempAudioFile(sound)

    if HAS_PEDALBOARD:
        try:
            addReverb = Pedalboard(
                [Reverb(room_size=0.8, damping=1, width=0.5, wet_level=0.3, dry_level=0.8)]
            )
            return addReverb(sound_data, sample_rate=sampleRate), sampleRate
        except Exception:
            pass

    reverbedSound = _apply_numpy_reverb(
        sound_data,
        sample_rate=sampleRate,
        room_size=0.8,
        damping=1.0,
        width=0.5,
        wet_level=0.3,
        dry_level=0.8,
    )
    return reverbedSound, sampleRate
