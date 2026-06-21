"""Central configuration — every tunable lives here, nothing hardcoded downstream.

The model name is a single swappable constant (Build Brief constraint): change
OLLAMA_MODEL to any installed Ollama instruct model and the graph picks it up.
"""

from pathlib import Path

# --- Model (the "brain"; also serves as the grounding judge) -----------------
# Must be an instruct model already pulled in Ollama (`ollama list`).
# qwen2.5:7b chosen for reliable native tool-calling — see decision-log.md D-01.
OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_TEMPERATURE = 0.0  # deterministic: this is a lookup bot, not a creative one

# --- Database (the single source of truth) -----------------------------------
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "accounts.db"

# --- Graph guards ------------------------------------------------------------
# Hard cap on the LLM <-> toolbox loop so it can never run away.
MAX_ITERATIONS = 4
# How many times the grounding node may bounce an unsupported answer back to the
# LLM before giving up and returning the safe fallback.
MAX_GROUNDING_RETRIES = 1

# --- The safe fallback (Build Brief, verbatim intent) ------------------------
FALLBACK_ANSWER = (
    "I don't have that information; I can help with account details and fees."
)

# --- Phase 2: FastAPI /chat wrapper ------------------------------------------
# Port 8000 is used by other local services (e.g. the Guardian Headless API),
# so this chatbot binds 8077 to avoid collisions.
API_HOST = "127.0.0.1"
API_PORT = 8077
API_URL = f"http://{API_HOST}:{API_PORT}/chat"  # voice client posts here
HEALTH_MARKER = "commerzbank-chatbot"            # identifies OUR server in /health

# --- Phase 2: voice I/O (all local; no cloud) --------------------------------
# Speech-to-text: faster-whisper. Model is a swappable constant.
WHISPER_MODEL = "base.en"          # tiny.en | base.en | small.en | ...
WHISPER_COMPUTE_TYPE = "int8"      # int8 is fast + low-memory on CPU

# Text-to-speech: Piper. Voice files live under models/ (see scripts/get_piper_voice.sh).
PIPER_VOICE = "en_US-lessac-medium"
PIPER_VOICE_DIR = Path(__file__).resolve().parent.parent / "models" / "piper"
PIPER_VOICE_ONNX = PIPER_VOICE_DIR / f"{PIPER_VOICE}.onnx"

# Audio capture/playback via ALSA CLI (arecord/aplay) — no PortAudio needed.
# Asymmetric setup on this host:
#   INPUT  -> wired mic in the motherboard pink jack = ALC897 analog = plughw:2,0
#            (direct ALSA, bypasses Bluetooth; the Marshall Emberton III is a
#             speaker with no real microphone).
#   OUTPUT -> ALSA `default` PCM bridges to PipeWire and follows its default
#            sink — the Bluetooth "EMBERTON III" (Marshall). Set the Marshall to
#            "High Fidelity Playback" in GNOME Sound settings for best quality.
# Use the `plughw:` prefix (not raw `hw:`) so ALSA converts rate/format/channels.
# List devices with `arecord -l` / `aplay -l` (cards) and `arecord -L` (PCMs).
AUDIO_INPUT_DEVICE = "plughw:2,0"   # wired mic -> ALC897 analog capture
AUDIO_OUTPUT_DEVICE = "default"     # speaker -> PipeWire default sink (Marshall)
AUDIO_SAMPLE_RATE = 16000           # 16 kHz mono — what Whisper expects

# --- System prompt for the brain ---------------------------------------------
# The grounding contract, stated to the model up front. The grounding node
# enforces it regardless, but a clear prompt reduces retries.
SYSTEM_PROMPT = (
    "You are a retail-bank account assistant. You answer ONLY using facts "
    "returned by your database tools. Follow these rules without exception:\n"
    "1. To answer any question about accounts, fees, interest, eligibility, or "
    "general banking FAQs, you MUST call a tool to fetch the data first.\n"
    "2. Never use prior knowledge or invent numbers. Every fee, rate, age, or "
    "fact in your answer must come from a tool result in this conversation.\n"
    "3. If the tools return nothing relevant, or the question is outside banking "
    "account topics (e.g. weather, sports, general trivia), reply exactly: "
    f"\"{FALLBACK_ANSWER}\"\n"
    "4. Keep answers short and factual. State the figures from the data plainly."
)
