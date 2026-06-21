# Commerzbank Chatbot — PROGRESS

> **Living document.** One section per phase; one entry per significant work session.
> Started at the close of the `7-layers.md` Plan-Mode session.

---

**Owner:** AI Product Builder
**Project start:** 2026-06-21
**Last updated:** 2026-06-21

---

## SYSTEM STATE (current)

| Field | Value |
|---|---|
| Release tag | (un-tagged working tree) |
| Phase | **DONE** — Phase 1 + Phase 2 complete and validated live (Phase 1 graph untouched by Phase 2) |
| Tests | **23/23** unit (`pytest`); **4/4** Phase 1 probes (`acceptance.py`); **6/6** Phase 2 checks (`acceptance_voice.py`); **live voice round-trip owner-confirmed** |
| Last deploy | n/a — local: `python server.py` (port 8077) + `python voice_chat.py` (or `python chat.py` for text) |
| Open blockers | none |
| Models | brain `qwen2.5:7b` (Ollama); STT `faster-whisper base.en`; TTS Piper `en_US-lessac-medium` — all local, all swappable in `chatbot/config.py` |
| Audio | IN: wired mic `plughw:2,0` (ALC897); OUT: `default` → PipeWire → Marshall "EMBERTON III". Mic gain tuned (`scripts/set_mic_level.sh`). |
| API port | 8077 (8000 is held by the Guardian Headless API — see decision-log D-09) |

---

## Phase 0 — Plan Mode — CLOSED 2026-06-21

### Completed work

| ID | Description | Track |
|---|---|---|
| PM-000 | 7-layers Plan-Mode session, derived from `BUILD_BRIEF_commerzbank_chatbot.md` | DOCS |

### Exit criteria validation

- [x] `7-layers.md` written and signed off — evidence: filled artifact, all 7 layers answered against the Build Brief
- [x] `stack.md` written from Layers 5+6 — evidence: `stack.md` (models, storage, deferred table)
- [x] `roadmap.md` and `PROGRESS.md` initialised — evidence: this file + `roadmap.md` v0.1→v0.2

---

## Phase 1 — Text-to-text — opened 2026-06-21 · closed 2026-06-21

### Completed work

| ID | Description | Track | Refs |
|---|---|---|---|
| P1-001 | venv + deps (langgraph 1.2.6, langchain-ollama 1.1.0, langchain-core 1.4.8, pytest) | INFRA | requirements.txt |
| P1-002 | `chatbot/config.py` — swappable model constant, DB path, guards, fallback, system prompt | FEATURE | D-01 |
| P1-003 | `chatbot/db.py` — five parameterized queries mirroring data/README.md | FEATURE | D-02, D-03 |
| P1-004 | `chatbot/tools.py` — five intent tools bound to the brain | FEATURE | D-03 |
| P1-005 | `chatbot/graph.py` — 3-node graph, conditional edges, iteration cap | FEATURE | D-05 |
| P1-006 | `chatbot/grounding.py` — deterministic evidence gate + claim verification | FEATURE | D-04 |
| P1-007 | `chat.py` — terminal REPL + fail-loud preflight | FEATURE | D-05 |
| P1-008 | `tests/` (test_db, test_grounding) — 20 deterministic unit tests | TEST | — |
| P1-009 | `acceptance.py` — four-probe live runner | TEST | — |

### Commit trail

```
(working tree — not yet committed; awaiting owner go-ahead per CLAUDE.md §7)
```

### Notes / observations (honest)

- **Grounding was the crux.** First pass used an LLM judge (`qwen2.5:7b` → SUPPORTED/UNSUPPORTED). It false-rejected the *correct, fully grounded* eligibility answer twice, dropping acceptance to 3/4. Switched to deterministic claim verification (decision-log D-04) — every number in an answer must trace to a retrieved row value / row text / the user's question, and every named account must appear in the retrieved rows. This is both more reliable and a real *guarantee*, which is what the hypothesis demanded.
- **Two grounding bugs found and fixed via live tracing, then pinned with tests:** (a) the `debit_card` 0/1 flag polluting the number pool → excluded non-figure columns; (b) the entity check only inspected a `name` column, so FAQ answers mentioning "Current"/"Savings" (no `name` field) were wrongly rejected → now checks the whole retrieved-row text.
- **Tool-calling on qwen2.5:7b was reliable** — it picked the right tool for every probe and for FAQ/eligibility/unknown-account cases.
- **The no-evidence hard gate is the load-bearing guarantee** for refusals: "weather", "CEO of Commerzbank", and the unknown "Gold account" all refuse deterministically, independent of model behaviour.

### Exit criteria validation

- [x] Premium monthly fee → "12 EUR" — evidence: `acceptance.py` PASS
- [x] Most interest → "Savings … 2.1% AER" — evidence: `acceptance.py` PASS
- [x] 22-year-old eligibility → lists 5 accounts incl. Student — evidence: `acceptance.py` PASS
- [x] "What's the weather?" → safe fallback — evidence: `acceptance.py` PASS
- [x] Unit gate green — evidence: `pytest` 20/20

---

## Phase 2 — Voice — opened 2026-06-21 · closed 2026-06-21

### Completed work

| ID | Description | Track | Refs |
|---|---|---|---|
| P2-001 | Phase 2 deps (faster-whisper, piper-tts, fastapi, uvicorn, httpx) + Piper voice download | INFRA | requirements.txt |
| P2-002 | `server.py` — FastAPI `POST /chat` wrapping `chatbot.graph.answer` verbatim | FEATURE | D-06 |
| P2-003 | `chatbot/voice/stt.py` — faster-whisper STT (numpy in, no ffmpeg) | FEATURE | D-06 |
| P2-004 | `chatbot/voice/tts.py` — Piper TTS to WAV | FEATURE | D-06 |
| P2-005 | `chatbot/voice/audio.py` — arecord/aplay capture+playback, push-to-talk | FEATURE | D-07, D-08 |
| P2-006 | `voice_chat.py` — push-to-talk client: record → STT → /chat → TTS → play | FEATURE | D-06 |
| P2-007 | `tests/test_voice_audio.py` (3) + `acceptance_voice.py` (API + voice loopback) | TEST | — |

### Notes / observations (honest)

- **The Phase 1 graph is byte-for-byte untouched.** `server.py` imports and calls `chatbot.graph.answer`; voice only wraps text in and text out. Grounding still runs entirely inside the graph.
- **Voice loopback proves the pipeline without a human mic:** Piper synthesizes a sentence → Whisper transcribes it back with meaning intact (`acceptance_voice.py`). Whisper even normalizes "twelve" → "12".
- **Two hardware gotchas, both fixed and documented (D-08):** (a) the ALC897 only accepts stereo/48kHz on raw `hw:` → switched to `plughw:2,0` so ALSA converts to mono/16kHz (and resamples Piper's 22kHz on playback); (b) `arecord -d` needs an integer duration, not `1.0`.
- **No PortAudio on this host**, so audio goes through the ALSA CLI (`arecord`/`aplay`) instead of `sounddevice`/`pyaudio` (D-07).
- **Live bring-up surfaced three real-world issues, all fixed (see decision-log D-08/D-09/D-10):**
  1. **Port collision** — 8000 was held by the Guardian Headless API (which also serves `/health`, so preflight false-passed → `/chat` 404). Moved to 8077; `/health` now carries a service marker the client verifies.
  2. **No mic on the Marshall** — the Emberton III is a speaker; its HFP "mic" captures silence. Split audio: wired mic in (`plughw:2,0`), Marshall out (`default`).
  3. **Mic clipping** — default +30 dB capture +20 dB boost overdrove the input; tuned to boost-off / ~19% capture (`scripts/set_mic_level.sh`).
- **Owner confirmed the live spoken round-trip** ("liftoff"): student-eligibility and Premium-fee answered correctly aloud; "what is the weather?" refused aloud.

### Exit criteria validation

- [x] FastAPI `/chat` returns grounded answers for all 4 Phase 1 probes — evidence: `acceptance_voice.py` API checks PASS
- [x] Local STT+TTS loopback preserves meaning — evidence: `acceptance_voice.py` VOICE checks PASS
- [x] Phase 1 graph unchanged — evidence: `chatbot/graph.py` not modified in Phase 2; Phase 1 `acceptance.py` still 4/4
- [x] **Live human voice round-trip** — evidence: owner spoke questions and heard grounded answers + a spoken refusal on 2026-06-21

---

## TD Register (across all phases)

| ID | Description | Phase | Status |
|---|---|---|---|
| P1-006 | Deterministic grounding (replaced LLM judge) | 1 | ✅ |
| P2-002 | FastAPI `/chat` wrapper (graph untouched) | 2 | ✅ |
| P2-005 | Voice I/O via ALSA CLI on `plughw:2,0` | 2 | ✅ |
| O-01 | Phase 2 TTS engine choice (Piper vs Coqui) | 2 | ✅ (Piper) |
| O-02 | Grounding number-pool may need per-schema tuning if tables/columns added | 1 | ⬜ |
| O-03 | Multi-turn memory (currently stateless) | 2+ | ⬜ |
| O-04 | Voice activity detection / auto-stop (currently manual push-to-talk) | 2+ | ⬜ |

Legend: ✅ done · 🟡 in progress · ⬜ not started · ❌ blocked · 🔄 reopened

---

## Handoff snapshot

- **State:** POC complete, both phases validated end-to-end on 2026-06-21. Working tree un-tagged (not yet committed).
- **All phases closed:**
  - Phase 0 (Plan Mode) — 7-layers + the four artifacts.
  - Phase 1 (text) — 4/4 acceptance probes, 23/23 unit tests. Grounding deterministic (D-04).
  - Phase 2 (voice) — `/chat` wrapper (port 8077) + Whisper STT + Piper TTS; 6/6 voice checks; live owner-confirmed round-trip.
- **How to run:** `python chat.py` (text); `python server.py` + `python voice_chat.py` (voice). Validate: `pytest -q`, `python acceptance.py`, `python acceptance_voice.py`.
- **Open items the receiving team owns:** O-02..O-05 in `decision-log.md` (none block the POC; O-05 = persist mic gain via `scripts/set_mic_level.sh`).
- **Safety-critical files** (`CLAUDE.md §3`): `chatbot/grounding.py`, `chatbot/db.py`, `data/accounts.db`, `data/build_db.py`.
- **Everything is fully local** — no cloud, no API keys, $0 running cost.
- **Receiving owner / date / walkthrough:** _to be assigned at formal handoff._

---

## Relationship to other artifacts

- `7-layers.md` — what we said we'd do (Day 0)
- `roadmap.md` — when we plan to do it (living)
- `stack.md` — what we'd build it with (Day 0, locked)
- `decision-log.md` — why we chose what we chose during the build
- **`PROGRESS.md` (this file) — what actually happened, when**
