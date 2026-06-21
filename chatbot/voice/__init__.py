"""Phase 2 voice layer — STT (Whisper) and TTS (Piper) wrapped around the
unchanged Phase 1 graph. Audio I/O goes through the ALSA CLI (arecord/aplay),
so no PortAudio/ffmpeg is required on the host.
"""
