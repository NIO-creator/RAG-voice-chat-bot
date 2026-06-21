# Commerzbank Chatbot — Roadmap

> **Living document.** Updated when a milestone slips, a phase opens/closes, scope changes, or a deferred item moves.
> Created at the close of the `7-layers.md` Plan-Mode session.

---

**Owner:** AI Product Builder
**Phase:** DONE — Phase 1 + Phase 2 complete, live-validated
**Last updated:** 2026-06-21
**Version:** 0.4

---

## Changelog

- **v0.4 (2026-06-21)** — Live voice round-trip owner-confirmed ("liftoff"). Bring-up fixes: server moved to port 8077 (8000 held by Guardian API), asymmetric audio (wired mic in / Marshall out), mic gain tuned. Project complete.
- **v0.3 (2026-06-21)** — Phase 2 built: FastAPI `/chat` wrapper (graph untouched), local Whisper STT + Piper TTS, ALSA I/O. 23 unit tests, 6/6 Phase 2 acceptance (API + voice loopback). Only the live human voice round-trip remained.
- **v0.2 (2026-06-21)** — Phase 1 closed: graph built, all 4 acceptance probes green, 20 unit tests passing. Grounding reworked from LLM judge to deterministic (decision-log D-04). Phase 2 gate now open.
- **v0.1 (2026-06-21)** — Initial roadmap from the 7-layers Plan-Mode session. Phase 1 (text) → Phase 2 (voice) drafted; deferred table mirrors `stack.md`.

---

## Where we are now

| Field | Value |
|---|---|
| Current phase | **DONE** — Phase 1 + Phase 2 complete, live-validated |
| Last milestone hit | Live spoken round-trip owner-confirmed on 2026-06-21 |
| Next milestone | Optional: commit/tag; productionization (handoff) per `decision-log.md` O-02..O-05 |
| Open risks (top 3) | 1. STT accuracy on other accents/mics (swap to `small.en`) · 2. Local model drift across Ollama updates · 3. Mic gain not persisted across reboot (run `scripts/set_mic_level.sh`) |

---

## Phases

### Phase 1 — Text-to-text (grounded LangGraph chatbot)

| Field | Value |
|---|---|
| Window | 2026-06-21 → 2026-06-21 |
| Status | **done** |
| Goal | Prove a local LangGraph agent answers bank-account questions strictly from `data/accounts.db`, with a grounding node guaranteeing no answer comes from training data. |
| Refs | `7-layers.md §3` (Scope); `stack.md` Models/Storage; `decision-log.md` D-01..D-05 |

**Deliverables:**
- [x] `chatbot/config.py` — swappable `OLLAMA_MODEL`, DB path, guards, fallback, system prompt
- [x] `chatbot/db.py` — five parameterized query functions (README patterns)
- [x] `chatbot/tools.py` — five intent tools bound to the brain
- [x] `chatbot/graph.py` — LLM node + toolbox node + grounding node, conditional edges, iteration cap
- [x] `chatbot/grounding.py` — deterministic evidence gate + claim verification
- [x] `chat.py` — terminal REPL with fail-loud preflight
- [x] `tests/` — 20 deterministic unit tests (db + grounding)
- [x] `acceptance.py` — the four-probe runner

**Exit criteria — phase is done when:**
- [x] "What's the monthly fee for the Premium account?" → 12 EUR — *evidence: acceptance PASS*
- [x] "Which account earns the most interest?" → Savings, 2.10% AER — *evidence: acceptance PASS*
- [x] "What can a 22-year-old open?" → eligibility list — *evidence: acceptance PASS*
- [x] "What's the weather?" → safe fallback — *evidence: acceptance PASS*
- [x] `pytest` green — *evidence: 20/20*

### Phase 2 — Voice

| Field | Value |
|---|---|
| Window | 2026-06-21 → 2026-06-21 |
| Status | **done** (live-validated) |
| Goal | Wrap the **unchanged** Phase 1 graph with local speech: Whisper STT on the way in, Piper TTS on the way out, behind a FastAPI `/chat` endpoint. |
| Refs | `7-layers.md §5` (Phase 2); `decision-log.md` D-06..D-08; `stack.md` "Models"/"Phase 2 audio" |

**Deliverables:**
- [x] FastAPI `/chat` endpoint calling `chatbot.graph.answer` verbatim (`server.py`)
- [x] Local Whisper STT: mic audio → text → graph (`chatbot/voice/stt.py`)
- [x] Local Piper TTS: final answer text → speech (`chatbot/voice/tts.py`)
- [x] Push-to-talk voice client (`voice_chat.py`) + ALSA I/O (`chatbot/voice/audio.py`)
- [x] Voice acceptance: 4 probes through `/chat` + Piper→Whisper loopback (`acceptance_voice.py`)

**Exit criteria — phase is done when:**
- [x] The four Phase 1 probes pass through the FastAPI `/chat` endpoint — evidence: `acceptance_voice.py` 4/4 API checks
- [x] Local STT+TTS round-trips with meaning intact — evidence: `acceptance_voice.py` voice loopback
- [x] Phase 1 graph untouched — evidence: `chatbot/graph.py` unchanged; `acceptance.py` still 4/4
- [x] Live: the user asked questions by voice and heard the grounded answers + a spoken refusal — owner-confirmed 2026-06-21

---

## Now / Next / Later

| Now | Next | Later |
|---|---|---|
| Phase 1 done; ready for sign-off | Phase 2 — FastAPI wrapper + Whisper STT + Piper/Coqui TTS | Conversation memory; vector search; larger model; persistent logging |

---

## Deferred / Out of scope

Mirrors `stack.md` "Decisions deliberately deferred".

| Item | Why deferred | Trigger to add to roadmap |
|---|---|---|
| Voice + FastAPI `/chat` | Phase 1 text had to pass first | Phase 1 probes green (met) → Phase 2 |
| Vector search / embeddings | Structured lookups suffice | Free-text questions the 5 patterns can't serve |
| Conversation memory | v1 single-turn stateless | A probe needs multi-turn follow-up |
| Larger/different brain model | qwen2.5:7b passes all probes | Probe failures traced to model capability |
| Persistent logging/metrics | POC scale | Pre-production hardening |

---

## Relationship to other artifacts

- `7-layers.md` — what we said we'd do (Day 0)
- `stack.md` — what we'd build it with (Day 0, locked)
- **`roadmap.md` (this file) — when we plan to do it (living)**
- `decision-log.md` — why we chose what we chose during the build
- `PROGRESS.md` — what actually happened, when
