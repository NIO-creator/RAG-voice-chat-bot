"""Microphone capture and speaker playback via the ALSA CLI.

Uses `arecord`/`aplay` directly so the project needs no PortAudio binding. Push-
to-talk recording: start capturing, return control, stop on demand — the caller
decides when the user is done speaking (e.g. pressing Enter).

All audio is 16 kHz mono S16_LE, which is what Whisper expects and what Piper
emits, so no resampling is needed anywhere in the pipeline.
"""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

from .. import config


class Recorder:
    """Push-to-talk recorder wrapping an `arecord` subprocess."""

    def __init__(self, device: str | None = None, sample_rate: int | None = None):
        self.device = device or config.AUDIO_INPUT_DEVICE
        self.sample_rate = sample_rate or config.AUDIO_SAMPLE_RATE
        self._proc: subprocess.Popen | None = None
        self._wav_path: Path | None = None

    def start(self) -> None:
        """Begin capturing to a temporary WAV file."""
        fd, name = tempfile.mkstemp(suffix=".wav", prefix="cbk_in_")
        Path(name).unlink(missing_ok=True)  # arecord will (re)create it
        self._wav_path = Path(name)
        self._proc = subprocess.Popen(
            [
                "arecord", "-q",
                "-D", self.device,
                "-f", "S16_LE",
                "-r", str(self.sample_rate),
                "-c", "1",
                str(self._wav_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )

    def stop(self) -> Path:
        """Stop capture and return the path to the recorded WAV."""
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None
        assert self._wav_path is not None
        return self._wav_path


def record_fixed(seconds: int, device: str | None = None,
                 sample_rate: int | None = None) -> Path:
    """Record a fixed whole number of seconds to a WAV file (non-interactive/tests).

    `arecord -d` takes an integer number of seconds, so `seconds` is truncated.
    """
    fd, name = tempfile.mkstemp(suffix=".wav", prefix="cbk_in_")
    Path(name).unlink(missing_ok=True)
    out = Path(name)
    subprocess.run(
        [
            "arecord", "-q",
            "-D", device or config.AUDIO_INPUT_DEVICE,
            "-f", "S16_LE",
            "-r", str(sample_rate or config.AUDIO_SAMPLE_RATE),
            "-c", "1",
            "-d", str(int(seconds)),
            str(out),
        ],
        check=True,
        stderr=subprocess.PIPE,
    )
    return out


def play(wav_path: str | Path, device: str | None = None) -> None:
    """Play a WAV file through the configured output device."""
    subprocess.run(
        ["aplay", "-q", "-D", device or config.AUDIO_OUTPUT_DEVICE, str(wav_path)],
        check=True,
        stderr=subprocess.PIPE,
    )


def wav_to_float32(wav_path: str | Path) -> np.ndarray:
    """Load a mono 16-bit PCM WAV into a float32 array in [-1, 1] for Whisper.

    Uses the stdlib `wave` module — no ffmpeg dependency.
    """
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.readframes(wf.getnframes())
        sampwidth = wf.getsampwidth()
    if sampwidth != 2:
        raise ValueError(f"expected 16-bit PCM, got sample width {sampwidth}")
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return audio
