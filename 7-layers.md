# 7 Layers — Commerzbank Chatbot (grounded, local LangGraph)

> Filled artifact from the Plan-Mode session, derived from `BUILD_BRIEF_commerzbank_chatbot.md`.
> Project: `Commerzbank-chatbot`. Owner: AI Product Builder. Plan-Mode date: 2026-06-21.
> This document is the **source of truth** for scope. A scope change updates this doc first, then `roadmap.md`/`stack.md`/code follow.

---

## Layer 1 — Hypothesis

**The single hypothesis being tested:**

> *A local LangGraph agent can answer bank-account questions strictly from a local SQLite database, with a grounding node guaranteeing that no answer is sourced from the model's training data — so every delivered fact traces back to a row that was actually queried, and any question the DB cannot answer is safely refused.*

**Success metric (one, named):** **Grounded-answer pass rate** on the four Phase 1 acceptance probes — three in-DB questions answered correctly *from queried rows* and one off-DB question safely refused. All four must pass:

| Probe | Expected |
|---|---|
| "What's the monthly fee for the Premium account?" | 12 EUR (from `accounts`) |
| "Which account earns the most interest?" | Savings, 2.10% AER (from `accounts`) |
| "What can a 22-year-old open?" | eligibility-filtered list (from `accounts`) |
| "What's the weather?" | safe fallback — refuses (not in DB) |

**Kill criterion:** If, after the graph is built, any delivered answer contains a fact **not** present in the rows the toolbox returned (i.e. the grounding node lets training-data content through), or the off-DB probe is answered instead of refused, the grounding design has failed its one job — stop and redesign the grounding node before any further feature work. A model that "sounds right" but is ungrounded is a kill, not a pass.

**Stakeholder who judges success:** The project owner (Build Brief author) signs off against the four-probe table above.

---

## Layer 2 — User & moment

**Primary user:** a retail-bank prospect or customer evaluating account products, interacting from a **terminal prompt** in Phase 1 (and by **voice** in Phase 2). They want a factual answer about fees, interest, eligibility, or general account FAQs without reading a tariff PDF or waiting for an agent.

**Moment in the flow:** the user has a concrete, answerable question ("what does the Premium account cost per month?", "which account pays the most interest?", "what can my 22-year-old open?") and types it. They expect a direct, correct answer — or an honest "I don't have that" — not a plausible-sounding guess.

**Pre-feature frustration:** general-purpose chatbots answer banking questions from training data — confidently, and sometimes wrong (hallucinated fees, outdated rates). For a bank, a confidently-wrong number is worse than no answer. The feature relieves this by **refusing to answer from anything but the bank's own current data**.

**Where the feature appears:** Phase 1 — a terminal REPL (`python chat.py`). Phase 2 — the same graph behind a FastAPI `/chat` endpoint, with local STT on the way in and local TTS on the way out. The voice layer only wraps I/O; the graph is untouched.

---

## Layer 3 — Scope

### In (Phase 1 — text-to-text, build fully first)

| In scope | Notes |
|---|---|
| LangGraph graph: LLM node + toolbox node + grounding node | The three real nodes from the brief; framework handles routing |
| Local Ollama LLM as the brain | Model is a config constant, swappable (see Layer 5) |
| Toolbox node querying `data/accounts.db` | Parameterized SQL only, via built-in `sqlite3` |
| Query patterns from `data/README.md` | lookup-by-name, comparison, eligibility filter, FAQ-by-topic |
| Grounding-check node | Hard gate (no rows → fallback) + claim-support check; one retry then fallback |
| Conditional edges + max-iteration cap | Loop cannot run away |
| Terminal REPL driver | stdin → graph → stdout, in a loop |
| The four acceptance probes (Layer 1) | All must pass before Phase 2 |
| Deterministic unit tests for db + grounding gate | Run without the model |

### Out (deferred — each has a named phase)

| Out of scope | Revisit when |
|---|---|
| Voice (local Whisper STT, Piper/Coqui TTS) | **Phase 2 — only after all 4 Phase 1 probes pass** |
| FastAPI `/chat` wrapper | Phase 2 (arrives with voice; not before) |
| Any cloud LLM / API keys | Out indefinitely — all-local is a hard constraint |
| Vector search / embeddings | Out for v1 — structured lookups need no embeddings (see `decision-log.md`) |
| Write operations (opening accounts, transactions) | Out indefinitely — read-only knowledge bot |
| Multi-turn account-application flows | Not on this roadmap |
| Authentication / per-user data | Out — the DB is public product info only |
| Web UI | Out — terminal in P1, voice in P2 |
| Multilingual | Out for v1 (English) |

### Timeline

| Milestone | Date |
|---|---|
| Plan-Mode complete (this doc) | 2026-06-21 |
| Phase 1 graph passing all 4 probes | 2026-06-21 |
| Phase 2 (voice) kickoff | gated on Phase 1 sign-off |

---

## Layer 4 — Data

### Inputs

| Data | Source | Freshness | Volume |
|---|---|---|---|
| Account products | `data/accounts.db` → `accounts` table | Read at query time; DB rebuilt via `data/build_db.py` | 5 rows |
| General FAQs | `data/accounts.db` → `faqs` table | Read at query time | 6 rows |
| User message | terminal stdin (Phase 1); mic→STT text (Phase 2) | live | one turn |

`accounts` columns: `name, monthly_fee_eur, min_opening_eur, interest_rate_aer, overdraft_eur, overdraft_apr, debit_card, min_age, max_age, summary`.
`faqs` columns: `question, answer, topic` (topics: `opening, interest, branches, cards`).

### New data produced

| Output | Storage | Notes |
|---|---|---|
| Final answer text | stdout (P1) / HTTP response + TTS audio (P2) | Not persisted in v1 |
| Retrieved-row context | in-memory graph state (per turn) | The grounding node's evidence; discarded after the turn |

### Backfill

None. The DB is already built and provided. `data/build_db.py` regenerates it idempotently (delete `.db`, re-run). No embedding/index backfill — there is no vector store.

---

## Layer 5 — Model & runtime

| Decision | Choice | Justification vs alternatives |
|---|---|---|
| **Brain model** | `qwen2.5:7b` (Ollama, local) | Already installed; strong, reliable **native tool-calling** in Ollama (needed for the LLM→toolbox decision); capable instruct model; fast on local hardware. Held as a config constant `OLLAMA_MODEL` so it is swappable. |
| **Why not qwen3:14b / deepseek-coder-v2:16b / llava:7b** | — | qwen3:14b: more capable but slower and its thinking mode complicates tool-call parsing; deepseek-coder-v2: coding-specialized, not ideal for conversational grounding; llava: vision model, irrelevant. qwen2.5:7b is the best fit-for-purpose already on disk. |
| **Grounding judge** | Same `qwen2.5:7b`, separate prompt | One installed model serves both roles; the grounding call is a constrained SUPPORTED/UNSUPPORTED judgment over the retrieved rows. |
| **Hosting** | **Self-hosted, local Ollama** (`http://localhost:11434`) | Hard constraint: all-local, no cloud APIs, no keys. |
| **Capabilities required** | Tool/function calling, instruction following. No vision, no streaming (v1), English only. | All native to qwen2.5:7b via Ollama. |
| **Latency budget** | Best-effort local; no SLA in v1. Typical turn = 1 LLM decision + ≤1 tool round-trip + 1 grounding judge → a few seconds on local GPU/CPU. | Terminal/voice POC; correctness over latency. |
| **Cost per call** | ~$0 (local compute / electricity only) | No API spend. |

---

## Layer 6 — Integration & architecture

### Where it runs

Single local Python process. Package `chatbot/` holds the graph; `chat.py` is the Phase 1 terminal entry point. Ollama runs as a local service. SQLite is a single file read in-process.

### Architecture diagram

```
                         Phase 1: terminal (stdin/stdout)
                         Phase 2: FastAPI /chat  ──  Whisper STT (in) / Piper|Coqui TTS (out)
                                          │
                                          ▼
                         ┌──────────────────────────────────────┐
                         │            LangGraph StateGraph        │
                         │                                        │
   START ──► [ LLM node (brain) ] ──tool_calls?──► [ Toolbox node ]
                         │  ▲                              │  (parameterized SQL,
                         │  └───────── rows (ToolMessage) ─┘   sqlite3 → accounts.db)
                         │
              final answer (no tool_calls)
                         │
                         ▼
                 [ Grounding node ]
                  ├─ no rows retrieved ───────────────► FALLBACK ─► END
                  ├─ claims supported by rows ────────► DELIVER  ─► END
                  └─ unsupported & retries left ──────► back to LLM node
                            (else, after retry) ──────► FALLBACK ─► END

   Guard: max-iteration cap on the LLM⇄Toolbox loop (config constant) → forces grounding/fallback.
```

### External dependencies

| Dependency | Role | Auth |
|---|---|---|
| Ollama (`localhost:11434`) | Serves `qwen2.5:7b` for the brain + grounding judge | none (local) |
| SQLite file `data/accounts.db` | Source of truth; queried by toolbox node | none (local file) |
| `langgraph` | State + node routing | — |
| `langchain-ollama` (`ChatOllama`) | Ollama client with `.bind_tools` | — |
| `langchain-core` | Message/tool types | — |

### Concurrency & state

- **Concurrency:** single-request, synchronous per turn in Phase 1 (REPL). Phase 2 FastAPI adds request-level concurrency around an unchanged graph.
- **State:** per-turn graph state — `messages`, `iterations`, accumulated `retrieved_rows`, and the final answer. Stateless across turns in v1 (each user line is an independent invocation); no DB writes, no session store.

### Protocols at each boundary

| Boundary | Protocol |
|---|---|
| User → app (P1) | stdin / stdout |
| App → Ollama | HTTP (localhost) |
| App → SQLite | in-process `sqlite3` (parameterized) |
| User → app (P2) | HTTP/JSON to FastAPI `/chat`; audio in/out via local STT/TTS |

---

## Layer 7 — Safety, observability, cost

### Failure modes + mitigations

| Failure mode | Mitigation |
|---|---|
| Model answers from training data (hallucinated fee/rate) | **Grounding node** — hard gate: if no rows were retrieved this turn, the answer is forced to the fallback; claim-support check rejects answers whose facts aren't in the rows |
| Off-DB question (e.g. "weather") answered anyway | No relevant tool returns rows → no-rows hard gate → fallback refusal |
| SQL injection via crafted account/topic name | Parameterized SQL only (`?` placeholders); no string-concatenated queries |
| LLM⇄toolbox loop never terminates | `MAX_ITERATIONS` cap in state → routes to grounding/fallback |
| Grounding judge wrongly rejects a correct answer | One retry with a nudge before falling back; the no-rows gate is deterministic, so the critical refusal case never depends on the judge |
| Ollama not running / model missing | Startup check; clear error telling the user to `ollama serve` / `ollama pull` |

### Output filters (what must NEVER be returned)

- Any factual claim not supported by rows retrieved this turn.
- Any answer when zero rows were retrieved (must be the fallback instead).
- Raw SQL, stack traces, or DB internals to the end user.

### Logging

| Field | Where | Retention |
|---|---|---|
| User message, tool calls + args, retrieved rows, grounding verdict, final answer | stdout / app log (dev) | session only in v1 |

### Metrics / alarms

POC scale — no pager. Watched manually: (1) acceptance-probe pass rate (must be 4/4), (2) grounding-reject rate, (3) loop hitting the iteration cap (signals a prompt/tool problem).

### Cost

| Item | Cost |
|---|---|
| Local Ollama inference | ~$0 (electricity) |
| SQLite / storage | negligible |
| **Total** | **$0 — no cloud, no API keys** |

### Kill switch

It's a local process — `Ctrl-C` stops it instantly. No deployed surface in v1.

---

## After all 7 layers — what's next

1. **Fill `stack.md`** from Layers 5 + 6. ✅
2. **Initialize `roadmap.md`** — Phase 1 (text) → Phase 2 (voice), deferred table mirrors `stack.md`. ✅
3. **Initialize `PROGRESS.md`** — Phase 0 (Plan Mode) entry + SYSTEM STATE. ✅
4. **`decision-log.md`** — captures choices made during the build (model pick, SQLite-over-vector, terminal-before-FastAPI). ✅
5. **Build Phase 1** against this doc; gate Phase 2 on the four probes passing.
