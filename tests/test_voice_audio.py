"""Deterministic tests for the voice audio helpers — no models, no hardware.

The model-dependent voice pipeline (Piper TTS -> Whisper STT) and the FastAPI
/chat path are exercised by `acceptance_voice.py` (they need Ollama + the local
speech models), kept out of the fast unit gate.
"""

import wave

import numpy as np

from chatbot import config
from chatbot.voice import audio


def test_wav_to_float32_roundtrips_known_samples(tmp_path):
    # Write a known 16-bit mono WAV, then confirm it loads to the expected floats.
    samples = np.array([0, 16384, -16384, 32767, -32768], dtype=np.int16)
    path = tmp_path / "tone.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(config.AUDIO_SAMPLE_RATE)
        wf.writeframes(samples.tobytes())

    out = audio.wav_to_float32(path)
    assert out.dtype == np.float32
    assert out.shape == (5,)
    np.testing.assert_allclose(out, samples.astype(np.float32) / 32768.0, atol=1e-7)
    assert out.min() >= -1.0 and out.max() <= 1.0


def test_wav_to_float32_rejects_non_16bit(tmp_path):
    path = tmp_path / "wide.wav"
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(4)  # 32-bit — unsupported
        wf.setframerate(config.AUDIO_SAMPLE_RATE)
        wf.writeframes(np.zeros(4, dtype=np.int32).tobytes())
    try:
        audio.wav_to_float32(path)
        assert False, "expected ValueError for non-16-bit PCM"
    except ValueError:
        pass


def test_recorder_defaults_from_config():
    rec = audio.Recorder()
    assert rec.device == config.AUDIO_INPUT_DEVICE
    assert rec.sample_rate == config.AUDIO_SAMPLE_RATE
