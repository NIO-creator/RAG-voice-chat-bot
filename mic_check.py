#!/usr/bin/env python3
"""Quick mic level check — confirms the input device captures real signal.

Records a few seconds from AUDIO_INPUT_DEVICE and reports peak/RMS so you can
verify the mic is live and at a usable gain before running voice_chat.py.

    python mic_check.py            # 3 seconds (default)
    python mic_check.py 5          # 5 seconds

Speak normally while it records. Rough guide for peak:
    < 0.01   silence / mic not capturing (check the jack, unmute/raise input)
    0.05-0.6 good speaking level
    > 0.95   clipping (lower the input gain)
"""

import sys

import numpy as np

from chatbot import config
from chatbot.voice import audio


def main() -> None:
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    print(f"Recording {seconds}s from {config.AUDIO_INPUT_DEVICE} @ {config.AUDIO_SAMPLE_RATE} Hz — speak now...")
    try:
        wav = audio.record_fixed(seconds)
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Capture failed on {config.AUDIO_INPUT_DEVICE}: {exc}\n"
                 "List devices with `arecord -l` and adjust AUDIO_INPUT_DEVICE in chatbot/config.py.")
    arr = audio.wav_to_float32(wav)
    peak = float(np.abs(arr).max()) if arr.size else 0.0
    rms = float(np.sqrt(np.mean(arr ** 2))) if arr.size else 0.0
    print(f"samples={arr.size}  peak={peak:.4f}  rms={rms:.4f}")
    if peak < 0.01:
        print("=> Near silence. Mic likely not capturing: check the pink jack, and raise/unmute")
        print("   the input in GNOME Sound settings (Input tab) or `alsamixer` (F4 = capture).")
    elif peak > 0.95:
        print("=> Clipping. Lower the input gain a little.")
    else:
        print("=> Looks good. You're ready for voice_chat.py.")


if __name__ == "__main__":
    main()
