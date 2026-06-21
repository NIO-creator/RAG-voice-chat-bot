#!/usr/bin/env python3
"""Phase 2 — talk to the chatbot.

Push-to-talk voice client. Records your question from the mic, transcribes it
locally (Whisper), sends the text to the FastAPI /chat endpoint (the unchanged
Phase 1 graph), then speaks the grounded answer back (Piper).

Run the server first, in another terminal:
    . .venv/bin/activate && python server.py

Then run this client:
    . .venv/bin/activate && python voice_chat.py
"""

import sys

import httpx

from chatbot import config
from chatbot.voice import audio, stt, tts


def _preflight() -> None:
    if not config.PIPER_VOICE_ONNX.exists():
        sys.exit(
            f"Piper voice missing at {config.PIPER_VOICE_ONNX}.\n"
            f"Download:  python -m piper.download_voices {config.PIPER_VOICE} "
            f"--download-dir {config.PIPER_VOICE_DIR}"
        )
    try:
        r = httpx.get(f"http://{config.API_HOST}:{config.API_PORT}/health", timeout=5)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001 - surface any connect error to the user
        sys.exit(
            f"Cannot reach the chat server at {config.API_URL} ({exc}).\n"
            "Start it first:  python server.py"
        )
    # Confirm it's actually OUR server — port could be held by another service.
    if r.json().get("service") != config.HEALTH_MARKER:
        sys.exit(
            f"Port {config.API_PORT} is answering, but it is NOT the chatbot server "
            f"(got service={r.json().get('service')!r}).\n"
            "Another app is using that port. Change API_PORT in chatbot/config.py "
            "or stop the other service, then start:  python server.py"
        )
    print("Loading local speech models (first run downloads Whisper)...")
    stt._model()   # warm the Whisper model
    tts._voice()   # warm the Piper voice


def _ask_server(message: str) -> str:
    resp = httpx.post(config.API_URL, json={"message": message}, timeout=120)
    resp.raise_for_status()
    return resp.json()["answer"]


def main() -> None:
    _preflight()
    print("\nVoice assistant ready (local STT + grounded graph + local TTS).")
    print(f"Mic: {config.AUDIO_INPUT_DEVICE}   Speaker: {config.AUDIO_OUTPUT_DEVICE}")
    print("Press Enter to start speaking; press Enter again to stop. Type 'q' then Enter to quit.\n")

    recorder = audio.Recorder()
    while True:
        cmd = input("[Enter]=talk  q=quit > ").strip().lower()
        if cmd == "q":
            print("bye")
            return

        print("recording... (press Enter to stop)")
        recorder.start()
        input()
        wav_path = recorder.stop()

        text = stt.transcribe_wav(wav_path)
        if not text:
            print("(heard nothing — try again)\n")
            continue
        print(f"you (heard)> {text}")

        try:
            answer = _ask_server(text)
        except Exception as exc:  # noqa: BLE001
            print(f"(server error: {exc})\n")
            continue
        print(f"bot> {answer}\n")

        wav_out = tts.synthesize_to_wav(answer)
        audio.play(wav_out)


if __name__ == "__main__":
    main()
