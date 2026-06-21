"""Text-to-speech via Piper (local, no cloud).

Loads the ONNX voice once and synthesizes answer text to a 16-bit mono WAV file,
ready for `aplay`. Output sample rate is whatever the voice model defines (the
lessac-medium voice is 22.05 kHz); playback via aplay reads it from the WAV
header, so no manual rate handling is needed.
"""

import tempfile
import wave
from functools import lru_cache
from pathlib import Path

from .. import config


@lru_cache(maxsize=1)
def _voice():
    """Load the Piper voice once (cached)."""
    from piper import PiperVoice

    if not config.PIPER_VOICE_ONNX.exists():
        raise FileNotFoundError(
            f"Piper voice not found at {config.PIPER_VOICE_ONNX}.\n"
            f"Download it with:  python -m piper.download_voices {config.PIPER_VOICE} "
            f"--download-dir {config.PIPER_VOICE_DIR}"
        )
    return PiperVoice.load(config.PIPER_VOICE_ONNX)


def synthesize_to_wav(text: str, out_path: str | Path | None = None) -> Path:
    """Synthesize `text` to a WAV file and return its path."""
    if out_path is None:
        fd, name = tempfile.mkstemp(suffix=".wav", prefix="cbk_out_")
        out_path = Path(name)
    out_path = Path(out_path)
    with wave.open(str(out_path), "wb") as wf:
        _voice().synthesize_wav(text, wf)
    return out_path
