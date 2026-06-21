#!/usr/bin/env python3
"""Self-paced speech-to-text check — records a phrase and prints the transcript.

Use this to confirm the mic + Whisper transcribe your voice correctly before
running the full voice_chat.py. The peak-level meter (mic_check.py) can flag
transient clipping that doesn't actually hurt transcription — this is the test
that matters.

    python stt_check.py            # 5-second window (default)
    python stt_check.py 7          # 7-second window

Press Enter, then speak a sentence (e.g. "What is the monthly fee for the
Premium account?"). The recognized text prints when the window ends.
"""

import sys

from chatbot import config
from chatbot.voice import audio, stt


def main() -> None:
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    print(f"Mic: {config.AUDIO_INPUT_DEVICE}.  Loading Whisper...")
    stt._model()  # warm the model so recording starts promptly
    input(f"Press Enter, then speak for ~{seconds}s > ")
    print("recording... speak now")
    wav = audio.record_fixed(seconds)
    text = stt.transcribe_wav(wav)
    print(f"\nWhisper heard: {text!r}")
    if not text.strip():
        print("(empty — check mic level with `python mic_check.py`)")


if __name__ == "__main__":
    main()
