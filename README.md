# Chatbot — grounded, local, LangGraph

A text chatbot that answers retail bank-account questions **only** from a local
SQLite database, running entirely on local models (Ollama). No cloud APIs, no
keys. A grounding node guarantees that every delivered fact traces back to a row
that was actually queried — nothing comes from the model's training data.

> **Phase 1 — text-to-text terminal — COMPLETE.**
> **Phase 2 — voice (Whisper STT + Piper TTS behind FastAPI `/chat`) — COMPLETE.**
> Voice only wraps text in and text out; the Phase 1 graph is untouched. See `roadmap.md`.

## Quickstart

```bash
# 1. Ollama must be running with the brain model installed
ollama serve &              # if not already running
ollama pull qwen2.5:7b      # the default model (swappable in chatbot/config.py)

# 2. Python env
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# 3. (Optional) rebuild the DB from scratch
python data/build_db.py

# 4a. Phase 1 — text
python chat.py              # interactive terminal REPL
python acceptance.py        # the four Phase 1 acceptance probes
python -m pytest -q         # 23 deterministic unit tests (no model needed)
```

Example text session:

```
you> What's the monthly fee for the Premium account?
bot> The monthly fee for the Premium account is 12 EUR.
you> What's the weather?
bot> I don't have that information; I can help with account details and fees.
```

### 4b. Phase 2 — voice

The voice path needs the local speech models (`pip install -r requirements.txt`
pulls faster-whisper + Piper; download the Piper voice once):

```bash
python -m piper.download_voices en_US-lessac-medium --download-dir models/piper
```

Run the server in one terminal, the voice client in another:

```bash
# terminal 1 — the FastAPI /chat wrapper around the graph (binds port 8077)
python server.py

# terminal 2 — push-to-talk: speak a question, hear the grounded answer
python voice_chat.py
```

In `voice_chat.py`: press **Enter** to start speaking, **Enter** again to stop;
your speech is transcribed locally (Whisper), sent to `/chat`, and the grounded
answer is spoken back (Piper). Type `q` to quit.

Before the first conversation, sanity-check the mic:

```bash
python mic_check.py     # records a few seconds, reports the input level
python stt_check.py     # records a phrase and prints what Whisper heard
```

Validate the whole voice pipeline without a mic (Piper→Whisper loopback + the 4
probes through `/chat`):

```bash
python acceptance_voice.py
```

**Audio devices (host-specific — set in `chatbot/config.py`):**
- **Server port:** `8077` (port 8000 was already taken on the build host).
- **Mic in:** `plughw:2,0` (wired mic on the motherboard analog jack). List with
  `arecord -l`; use the `plughw:` prefix (not raw `hw:`) so ALSA converts
  rate/format/channels.
- **Speaker out:** `default` → PipeWire default sink (a Bluetooth Marshall on the
  build host). A Bluetooth *speaker* has no mic, so input and output are
  deliberately different devices.
- **Mic gain** isn't persisted across reboot; re-apply the tuned level with
  `bash scripts/set_mic_level.sh` (or raise/lower it in GNOME Sound → Input).

## How it works

A LangGraph graph with three real nodes (the framework handles routing):

```
START → LLM node (brain, Ollama) ──tool_calls──► Toolbox node (parameterized SQL)
                 ▲                                         │
                 └───────────── retrieved rows ────────────┘
                 │
        final answer
                 ▼
          Grounding node ── no rows / unsupported claim ─► safe fallback
                         └─ every claim supported by rows ─► deliver
```

- **LLM node** (`chatbot/graph.py`) — local `qwen2.5:7b`; decides whether to call a tool or answer.
- **Toolbox node** — runs one of five parameterized queries (`chatbot/db.py`, `chatbot/tools.py`) against `data/accounts.db`.
- **Grounding node** (`chatbot/grounding.py`) — **deterministic**: an answer is delivered only if rows were retrieved *and* every number/account in it traces to those rows (or a figure echoed from the question); otherwise the safe fallback. One retry, then fallback. A max-iteration cap bounds the loop.

The brain model is a single swappable constant: `OLLAMA_MODEL` in `chatbot/config.py`.

## Layout

```
chatbot/         config.py · db.py · tools.py · grounding.py · graph.py
  voice/         audio.py (arecord/aplay) · stt.py (Whisper) · tts.py (Piper)
chat.py          Phase 1 terminal entry point
server.py        Phase 2 FastAPI /chat wrapper (graph untouched; port 8077)
voice_chat.py    Phase 2 push-to-talk voice client
mic_check.py     mic input-level meter
stt_check.py     speak a phrase, see what Whisper heard
acceptance.py        the four Phase 1 acceptance probes
acceptance_voice.py  Phase 2 checks (/chat probes + Piper→Whisper loopback)
scripts/         set_mic_level.sh (re-apply tuned mic gain after reboot)
tests/           deterministic unit tests (db + grounding + audio helpers)
data/            accounts.db · build_db.py · README.md (schema + query patterns)
models/piper/    Piper voice (downloaded; gitignored)
```

## Foundation / project docs

This project was scaffolded with the AI-product-builder foundation. The operating
docs are the source of truth for scope, decisions, and status:

- `7-layers.md` — the architectural plan (hypothesis → safety)
- `stack.md` — locked tech stack
- `roadmap.md` — phases, exit criteria, deferred items
- `decision-log.md` — choices made during the build (incl. the grounding reversal, D-04)
- `PROGRESS.md` — what happened, when, with evidence
- `CLAUDE.md` / `AGENTS.md` — operating rules for agents in this repo
