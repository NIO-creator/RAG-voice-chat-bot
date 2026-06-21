"""Speech-to-text via faster-whisper (local, no cloud).

The model loads once and is reused. Transcription takes a float32 numpy array
(16 kHz mono) so we never shell out to ffmpeg for audio decoding.
"""

from functools import lru_cache
from pathlib import Path

import numpy as np

from .. import config
from . import audio


@lru_cache(maxsize=1)
def _model():
    """Load the Whisper model once (cached). Downloads on first use."""
    from faster_whisper import WhisperModel

    return WhisperModel(
        config.WHISPER_MODEL,
        device="cpu",
        compute_type=config.WHISPER_COMPUTE_TYPE,
    )


def transcribe_array(audio_f32: np.ndarray) -> str:
    """Transcribe a 16 kHz mono float32 array to text."""
    segments, _info = _model().transcribe(audio_f32, language="en", beam_size=1)
    return "".join(seg.text for seg in segments).strip()


def transcribe_wav(wav_path: str | Path) -> str:
    """Transcribe a 16 kHz mono 16-bit WAV file to text."""
    return transcribe_array(audio.wav_to_float32(wav_path))
