# Commerzbank Chatbot — Decision Log

Running ledger of architectural choices made **during the build**. The upfront,
locked choices live in `7-layers.md` and `stack.md`; this file captures what was
decided (and corrected) while constructing the graph.

---

## Validation legend

- ✅ **validated** — verified in the running system, with evidence linked
- ❓ **assumed** — not yet validated; flagged for follow-up
- ❌ **wrong** — turned out to be incorrect; see the corresponding reversal entry

---

## Phase 1 — Grounded text chatbot

### D-01. Brain model = `qwen2.5:7b` (Ollama, local), held as a config constant
- **Date:** 2026-06-21
- **Decision:** Use `qwen2.5:7b` as the brain (and previously the grounding judge), via `OLLAMA_MODEL` in `chatbot/config.py`.
- **Rationale:** Already installed (`ollama list`); reliable **native tool-calling** in Ollama — required for the LLM→toolbox decision; capable instruct model; fast on local hardware. Kept as a single swappable constant per the Build Brief.
- **Alternatives considered:** `qwen3:14b` (more capable but slower; thinking mode complicates tool-call parsing); `deepseek-coder-v2:16b` (coding-specialised, not conversational); `llava:7b` (vision model, irrelevant); `nomic-embed-text` (embeddings only).
- **Invalidated if:** probe failures trace to model capability, or tool-calling proves unreliable across questions.
- **Refs:** 7-layers.md §5; stack.md "Models".
- **Validation:** ✅ All 4 acceptance probes answered with correct tool calls — `python acceptance.py` → 4/4.

### D-02. SQLite + parameterized SQL, NOT a vector store
- **Date:** 2026-06-21
- **Decision:** The toolbox queries `data/accounts.db` with built-in `sqlite3` via five parameterized query functions (`chatbot/db.py`); no embeddings, no vector DB.
- **Rationale:** The knowledge base is 5 account rows + 6 FAQ rows of structured fields. The four real query patterns (lookup-by-name, comparison, eligibility filter, FAQ-by-topic) are exact structured lookups — embeddings add cost and a hallucination surface for zero benefit at this scale.
- **Alternatives considered:** pgvector / Qdrant + nomic-embed-text (rejected — over-engineered for 11 structured rows; semantic match is unnecessary and weakens the grounding guarantee).
- **Invalidated if:** free-text questions arrive that the structured patterns can't serve, or the corpus grows to many free-text documents.
- **Refs:** 7-layers.md §4; stack.md "Storage"; data/README.md.
- **Validation:** ✅ `tests/test_db.py` (9 tests) pins every query pattern against the real DB — 9/9 pass.

### D-03. Toolbox exposes five intent tools, not raw free-form SQL from the LLM
- **Date:** 2026-06-21
- **Decision:** Give the brain five typed tools (`get_account`, `list_accounts`, `accounts_by_interest`, `eligible_accounts`, `answer_faq`) that each run one parameterized query — rather than letting the LLM emit arbitrary SQL.
- **Rationale:** Guarantees "parameterized SQL only" (Build Brief constraint) structurally — the LLM never composes SQL, so injection and malformed-query classes are impossible. Tool descriptions also give the model clean routing signals.
- **Alternatives considered:** a single `run_sql(query)` tool (rejected — reintroduces injection risk and lets the model invent column names / hallucinate schema).
- **Invalidated if:** a needed query can't be expressed as one of the fixed intents (would add a new typed tool, not free SQL).
- **Refs:** 7-layers.md §6; chatbot/tools.py.
- **Validation:** ✅ Live runs show the model selecting the correct tool per question (traced).

### D-05. Pure-terminal in Phase 1; FastAPI only arrives with voice (Phase 2)
- **Date:** 2026-06-21
- **Decision:** Phase 1 is a stdin/stdout REPL (`chat.py`). No web server until Phase 2 wraps the unchanged graph for voice.
- **Rationale:** Build Brief sequencing — prove the grounded graph end-to-end in the simplest possible harness before adding a server or speech I/O. Keeps the Phase 1 surface tiny and the graph reusable verbatim under FastAPI later.
- **Alternatives considered:** build FastAPI now (rejected — premature; nothing in Phase 1 needs HTTP).
- **Invalidated if:** a Phase 1 requirement needs concurrent or remote access.
- **Refs:** 7-layers.md §3; roadmap.md Phase 2.
- **Validation:** ✅ `chat.py` REPL drives the graph; preflight checks DB + Ollama before the loop.

---

## Phase 1 — reversal

### DECISION-04. Grounding switched from an LLM judge to deterministic claim verification
- **Date:** 2026-06-21
- **Phase:** 1
- **Problem (symptom):** With an LLM grounding judge (`qwen2.5:7b` prompted to reply SUPPORTED/UNSUPPORTED), the eligibility probe ("What can a 22-year-old open?") was **false-rejected**: the model produced a fully grounded answer listing the five retrieved accounts, the judge said UNSUPPORTED twice, and the turn fell back. Acceptance was 3/4.
- **Root cause:** The free-form LLM judge is unreliable for this verdict — it could not confirm that an eligibility-filtered list "supported" the claim, even though every account and figure came from the retrieved rows. A probabilistic judge cannot provide the *guarantee* the hypothesis demands.
- **Fix:** Replaced the judge with deterministic checks in `chatbot/grounding.py`: (1) **evidence gate** — zero retrieved rows ⇒ fallback; (2) **claim verification** — every number in the answer must appear in a retrieved row value, in text inside a retrieved row, or be echoed from the user's question (flag/id columns excluded); and every real account named must appear somewhere in the retrieved row text. A failure retries once, then falls back.
- **Resolves:** D-04 (the original LLM-judge grounding design — marked ❌).
- **Accountability:** Added deterministic unit tests (`tests/test_grounding.py`, 11 tests) covering supported/hallucinated numbers, decimal normalisation (2.1 vs 2.10), question-echoed ages, numbers inside FAQ text, accounts named-but-not-retrieved, and flag-column exclusion — so this class of grounding error is caught without the model in the loop.
- **Validation:** ✅ `python acceptance.py` → 4/4 probes; `pytest` → 20/20. The off-DB ("weather"), unknown-account ("Gold"), and trivia ("CEO of Commerzbank") cases all refuse via the deterministic gate.

---

## Phase 2 — Voice (STT in, TTS out, FastAPI wrapper)

### D-06. STT = faster-whisper `base.en`; TTS = Piper `en_US-lessac-medium`
- **Date:** 2026-06-21
- **Decision:** Speech-to-text via `faster-whisper` (model `base.en`, int8 CPU); text-to-speech via Piper (`en_US-lessac-medium`). Both are swappable constants in `chatbot/config.py` (`WHISPER_MODEL`, `PIPER_VOICE`).
- **Rationale:** Both run fully local on CPU with no GPU. faster-whisper is fast and accepts a numpy array directly (avoids ffmpeg, which isn't installed). Piper is lightweight ONNX, ~60MB voice, reliable and fast — chosen over Coqui (heavier deps, slower on CPU, less maintained). Resolves open item O-01. base.en balances accuracy and latency for clear speech.
- **Alternatives considered:** openai-whisper (needs ffmpeg for decoding — rejected); Coqui TTS (heavier, slower — rejected); `small.en` (more accurate, larger/slower — deferred, swap the constant if accuracy needed).
- **Invalidated if:** transcription accuracy is poor on the user's accent/mic (→ `small.en`), or a more natural voice is required (→ different Piper voice or Coqui).
- **Refs:** 7-layers.md §5 (Phase 2 row); stack.md "Models".
- **Validation:** ✅ `acceptance_voice.py` voice loopback — Piper speaks → Whisper transcribes back with meaning intact ("twelve euros" → "12 euros"); 6/6 Phase 2 checks pass.

### D-07. Audio I/O through the ALSA CLI (`arecord`/`aplay`), not a PortAudio binding
- **Date:** 2026-06-21
- **Decision:** Capture and playback shell out to `arecord`/`aplay` rather than using `sounddevice`/`pyaudio`. Recording is push-to-talk (start an `arecord` subprocess, terminate it when the user stops).
- **Rationale:** This host has no `libportaudio` (and no sudo assumed), so `sounddevice`/`pyaudio` can't be installed. `arecord`/`aplay` are already present and need no Python audio binding. Keeps Phase 2 install-light.
- **Alternatives considered:** sounddevice/pyaudio (rejected — require PortAudio system lib that's absent).
- **Invalidated if:** the project moves to a host/OS without ALSA (would swap the I/O backend behind `chatbot/voice/audio.py`).
- **Refs:** stack.md "Phase 2 audio"; chatbot/voice/audio.py.
- **Validation:** ✅ 1s mic capture (16k mono) and Piper playback both succeed on this host.

### D-08. ALSA device = `plughw:2,0` (the plug layer), not raw `hw:2,0`
- **Date:** 2026-06-21
- **Phase:** 2
- **Problem (symptom):** `arecord -D hw:2,0 -f S16_LE -r 16000 -c 1` failed with "Channels count non available"; mono/16kHz capture was rejected.
- **Root cause:** The ALC897 hardware only accepts its native format (stereo, 48kHz). Raw `hw:` gives direct hardware access with no conversion, so mono/16kHz is refused. Piper's 22kHz output would likewise be refused by raw `hw:` on playback.
- **Fix:** Use `plughw:2,0` for both input and output (ALSA's plug layer transparently converts rate/format/channels). `AUDIO_INPUT_DEVICE`/`AUDIO_OUTPUT_DEVICE` in config set to `plughw:2,0`.
- **Accountability:** Documented the device-discovery step (`arecord -l`/`aplay -l`) and the plug-vs-raw distinction in config comments and README so another host can be configured quickly.
- **Validation:** ✅ Mic capture and Piper playback both succeed via `plughw:2,0`. (Separately fixed `record_fixed` to pass an integer to `arecord -d`.)

### D-09. Server binds port 8077, not 8000; `/health` carries a service marker
- **Date:** 2026-06-21
- **Phase:** 2
- **Problem (symptom):** Voice client returned `404 Not Found` for `/chat` even though `voice_chat.py`'s preflight `/health` check passed. Starting `server.py` had earlier failed with "address already in use" on 8000.
- **Root cause:** Port 8000 is held by another local service on this host — the **Guardian Headless API 2.5** — which coincidentally also serves `/health` (so preflight false-passed) but has no `/chat`. Our chatbot server never actually bound the port.
- **Fix:** Bind `API_PORT = 8077` (verified free). Add `service: "commerzbank-chatbot"` to our `/health` payload and have `voice_chat.py` assert that marker, so a future port collision fails loudly with a clear message instead of silently 404-ing.
- **Accountability:** The preflight now validates service identity, not just reachability — checking "is something there" is not the same as "is it the right thing."
- **Refs:** chatbot/config.py (`API_PORT`, `HEALTH_MARKER`); server.py; voice_chat.py.
- **Validation:** ✅ `curl POST :8077/chat` returns a grounded answer; live voice round-trip works end-to-end.

### D-10. Asymmetric audio: wired mic in (ALC897) + Bluetooth Marshall out (PipeWire)
- **Date:** 2026-06-21
- **Phase:** 2
- **Decision:** Input from the wired mic on the motherboard pink jack (`plughw:2,0`, ALC897 analog); output to the Bluetooth "EMBERTON III" (Marshall) via the ALSA `default` PCM (PipeWire default sink).
- **Rationale:** The Marshall Emberton III is a speaker with **no microphone** — PipeWire exposes an HFP (`headset-head-unit`) source that captures silence and, when active, forces the speaker into mono phone-quality. So the Marshall can only serve output. A wired mic on the ALC897 gives clean 16 kHz capture and lets the Marshall stay on hi-fi A2DP for output.
- **Tuning:** The mic was clipping at the default +30 dB capture +20 dB rear-mic boost. Set Rear Mic Boost = 0 and Capture ≈ 19% (−8.25 dB) for a clean speaking level (`scripts/set_mic_level.sh` re-applies it after reboot).
- **Alternatives considered:** Marshall as mic via HFP (rejected — no real mic, silence, degrades output); PipeWire `default` for input (rejected — its default source was the Emberton).
- **Refs:** chatbot/config.py (`AUDIO_INPUT_DEVICE`/`AUDIO_OUTPUT_DEVICE`); decision-log D-07, D-08; scripts/set_mic_level.sh.
- **Validation:** ✅ `stt_check.py` transcribed live speech accurately; full `voice_chat.py` conversation confirmed by the owner (grounded answers + spoken refusal).

---

## Open architectural items

| # | Item | Needs answer before |
|---|---|---|
| O-02 | Whether grounding's number-pool needs per-schema tuning if new tables/columns are added | Adding any table beyond `accounts`/`faqs` |
| O-03 | Multi-turn memory (currently stateless) | A requirement needing follow-up questions |
| O-04 | Voice activity detection / auto-stop recording (currently manual push-to-talk) | If hands-free use is required |
| O-05 | ALSA mixer state (mic gain) is not persisted across reboot | Productionizing on this host (run `scripts/set_mic_level.sh` or `alsactl store` as root) |

_O-01 (Piper vs Coqui) — RESOLVED in D-06 (Piper)._

---

## Closing note (handoff)

As of 2026-06-21 the POC is **complete and validated end-to-end, both phases**:

- **Phase 1 (text):** grounded LangGraph chatbot — 4/4 acceptance probes, 23/23 unit tests. Grounding is deterministic (D-04), guaranteeing every delivered fact traces to a queried row; off-DB questions refuse.
- **Phase 2 (voice):** the unchanged graph behind FastAPI `/chat` (port 8077), local Whisper STT + Piper TTS, ALSA I/O (wired mic in, Marshall out). 6/6 voice acceptance checks; the owner confirmed a live spoken round-trip.

Everything runs **fully local — no cloud, no API keys**. Items the receiving team owns: O-02..O-05 above (none block the POC). The grounding node (`chatbot/grounding.py`), `chatbot/db.py`, and `data/accounts.db` are the safety-critical files (see `CLAUDE.md §3`).

---

## Closing note (filled at handoff)

_To be filled at handoff._
