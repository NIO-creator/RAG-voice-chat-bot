# Commerzbank Chatbot — Tech Stack

> Filled from `7-layers.md` Layers 5 (Model & runtime) and 6 (Integration & architecture).
> Locked at kickoff. The whole stack is **local — no cloud, no API keys** (hard constraint).

---

## Languages & runtimes

| Layer | Choice | Why |
|---|---|---|
| Backend / graph | Python 3.12 | LangGraph + Ollama ecosystem; built-in `sqlite3` |
| Executor / framework | LangGraph 1.2.6 | State machine + conditional routing for the 3-node graph |
| Phase 1 interface | Terminal REPL (`chat.py`) | Pure text-to-text |
| Phase 2 interface | FastAPI `/chat` (`server.py`) + voice client (`voice_chat.py`) | Wraps the unchanged graph for voice I/O |
| Voice I/O (Phase 2) | `arecord`/`aplay` (ALSA CLI) | No PortAudio on host; CLI needs no Python audio binding. See decision-log D-07. |
| Scripts & tooling | Python | `data/build_db.py`, `acceptance.py`, `acceptance_voice.py` |

---

## Models

| Use case | Model | Hosted where | Why |
|---|---|---|---|
| Brain (decide tool vs answer; phrase answer) | `qwen2.5:7b` | Local Ollama (`localhost:11434`) | Already installed; reliable native tool-calling; fast; capable instruct. **Swappable** via `OLLAMA_MODEL` in `chatbot/config.py`. See decision-log D-01. |
| Grounding | **none — deterministic code** | n/a | Claim verification is deterministic (`chatbot/grounding.py`), not an LLM judge. An LLM judge was tried and reversed — see decision-log D-04. |
| Embeddings / vectors | **none** | n/a | Structured lookups over 5+6 rows need no embeddings. See decision-log D-02. |
| Speech-to-text (Phase 2) | `faster-whisper` `base.en` (int8, CPU) | Local | Fast, accepts numpy directly (no ffmpeg). Swappable via `WHISPER_MODEL`. See decision-log D-06. |
| Text-to-speech (Phase 2) | Piper `en_US-lessac-medium` | Local (ONNX) | Lightweight, fast on CPU, no GPU; chosen over Coqui. Swappable via `PIPER_VOICE`. See decision-log D-06. |

---

## Storage

| Data | Storage | Why |
|---|---|---|
| Account products + FAQs | SQLite file `data/accounts.db` | Single source of truth; already built; read in-process with built-in `sqlite3`. No DB server. |
| Vectors | none | No semantic search in v1 (see decision-log D-02) |
| Object storage | none | No files/images |
| Cache | none | 11 rows; every query is sub-millisecond |
| Session state | none (stateless per turn) | Each user line is an independent graph invocation in v1 |
| Logs & telemetry | stdout (dev) | POC scale; no log store in v1 |

---

## Messaging & integration

| Boundary | Protocol | Wire format | Auth |
|---|---|---|---|
| User → app (Phase 1) | stdin / stdout | text | none (local) |
| App → Ollama | HTTP (localhost) | JSON | none (local) |
| App → SQLite | in-process `sqlite3` | parameterized SQL (`?`) | none (local file) |
| Voice client → app (Phase 2) | REST `POST /chat` over HTTP `127.0.0.1:8077` | JSON `{message}`/`{answer}` | none (local) |
| Mic (Phase 2) | ALSA `arecord` on `plughw:2,0` (wired mic, ALC897) | 16-bit PCM WAV | none (local) |
| Speakers (Phase 2) | ALSA `aplay` on `default` → PipeWire → Bluetooth Marshall | 16-bit PCM WAV | none (local) |

---

## Deployment

| Aspect | Choice |
|---|---|
| Container | none in v1 — runs as a local Python process in a venv |
| Orchestration | none (single process) |
| CI/CD | local `pytest` gate (`tests/`) |
| Image registry | n/a |
| Secrets | none — there are no secrets (fully local, no keys) |
| GPU | optional — Ollama uses local GPU if present, else CPU |

---

## Observability

| Concern | Tool | Where it lands |
|---|---|---|
| Application logs | stdout | session only (v1) |
| Metrics | manual — acceptance pass rate, grounding-reject rate, loop-cap hits | `PROGRESS.md` |
| Tracing | none in v1 | — |
| Product analytics | none | — |
| Errors | stderr / fail-loud preflight in `chat.py` | terminal |
| Cost monitoring | n/a | $0 — local only |

---

## Cost guard

| Item | Expected monthly cost | Alert threshold | Owner |
|---|---|---|---|
| Local Ollama inference | $0 (electricity only) | n/a | owner |
| SQLite / storage | $0 | n/a | owner |
| **Total monthly cap** | **$0 — no cloud, no API keys** | **n/a** | owner |

---

## Kill switches

| Feature | Disable mechanism | Disable latency |
|---|---|---|
| The whole chatbot | `Ctrl-C` (local process) | <1 second |
| Swap the brain model | edit `OLLAMA_MODEL` in `chatbot/config.py` | next launch |

---

## Decisions deliberately deferred

| Decision | Why deferred | Trigger to decide |
|---|---|---|
| Vector search / embeddings | Structured lookups suffice at current scale | Free-text questions the 5 query patterns can't answer, or DB grows to many free-text docs |
| Voice activity detection / auto-stop (vs manual push-to-talk) | Push-to-talk is enough for the POC | Hands-free use required |
| Conversation memory across turns | v1 is single-turn stateless | A probe needs multi-turn follow-up |
| Larger / different brain model (e.g. qwen3:14b) | qwen2.5:7b passes all probes | Probe failures traced to model capability |
| Persistent logging / metrics store | POC scale | Pre-production hardening |
