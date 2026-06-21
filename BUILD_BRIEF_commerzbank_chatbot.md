# Build Brief — Commerzbank Chatbot (LangGraph, local, grounded)

## For the receiving Claude Code / Opus session

Build a grounded text chatbot as a LangGraph application that answers **only**
from a local SQLite database, running entirely on local models (Ollama). No
cloud APIs, no keys. Phase 1 is text-to-text from the terminal. Phase 2 wraps
it with local speech (STT in, TTS out) — do NOT build Phase 2 until Phase 1
works end to end.

Scaffold the project first with the `foundation-init` skill, then build against
the docs it produces. Everything here is real — there are no mocked components.

---

## Stack (locked — do not substitute)

| Layer | Choice |
|---|---|
| Language | Python 3 |
| Framework / executor | LangGraph |
| LLM (brain) | Local Ollama. **Pick a model from those already installed** — run `ollama list`, choose a capable instruct model (e.g. a Qwen or Llama variant), and record the choice in `decision-log.md`. Make it a config constant so it's swappable. |
| Toolbox | A LangGraph tool node that runs SQL against the local DB |
| DB | `data/accounts.db` (SQLite, already built — see below). Read with Python's built-in `sqlite3`. |
| Grounding | A custom validation node (checks the answer is supported by the query result; falls back otherwise) |
| Phase 1 interface | Terminal script (run the graph in a loop, read stdin, print stdout) |
| Phase 2 (later) | STT = local Whisper; TTS = local Piper or Coqui; FastAPI `/chat` wrapper |

Pure-terminal in Phase 1 — no web server until voice arrives.

---

## The database (already built — place, don't recreate)

Three files are provided; put them in `data/`:
- `data/accounts.db` — SQLite DB, the source of truth
- `data/build_db.py` — regenerates the DB (delete `.db` and re-run)
- `data/README.md` — schema + the SQL query patterns to use

Schema summary:
- `accounts` (5 rows): `name, monthly_fee_eur, min_opening_eur, interest_rate_aer, overdraft_eur, overdraft_apr, debit_card, min_age, max_age, summary`
- `faqs` (6 rows): `question, answer, topic`

Read `data/README.md` for the exact query patterns (lookup by name, comparison,
eligibility filter, FAQ by topic). The toolbox node uses these.

---

## The graph — three real nodes + framework routing

LangGraph holds state and routes; the three nodes do the work.

1. **LLM node (brain, Ollama).** Receives the user message + system prompt +
   the conversation state. Decides whether to call the toolbox (and with what
   query intent) or to produce a final answer. The system prompt instructs it:
   *answer only from database results; never use prior knowledge; if the toolbox
   returns nothing, say you don't have that information.*

2. **Toolbox node.** Runs SQL against `data/accounts.db` based on the LLM's
   request, returns the rows as structured context. Contains the DB access. Keep
   the queries parameterized (no string-concatenated SQL).

3. **Grounding-check node.** Takes the candidate answer + the rows the toolbox
   returned. Confirms the answer's claims are supported by those rows. If
   supported → deliver. If not (or no rows) → return the safe fallback
   ("I don't have that information; I can help with account details and fees.").

**Edges (conditional):**
- START → LLM node
- LLM node → toolbox (if it wants data) → back to LLM node (with rows)
- LLM node → grounding check (when it has a final answer)
- grounding check → END (pass) OR → LLM node (fail, one retry, then fallback)

Add a max-iteration cap so the loop can't run away.

---

## Phases

**Phase 1 — text-to-text (build this fully first).**
Graph with the three nodes and edges, reading from `data/accounts.db`, driven by
a terminal loop. Done when these all work from the command line:
- "What's the monthly fee for the Premium account?" → 12 EUR (from DB)
- "Which account earns the most interest?" → Savings, 2.10% AER
- "What can a 22-year-old open?" → eligibility query result
- "What's the weather?" → safe fallback (not in DB, must refuse)

**Phase 2 — voice (only after Phase 1 passes).**
- STT: local Whisper turns mic audio into text, fed into the same graph.
- TTS: local Piper/Coqui speaks the final text answer.
- Wrap the graph behind a FastAPI `/chat` endpoint; voice I/O sits around it.
- The Phase 1 graph is untouched — voice only wraps input and output.

---

## Foundation docs to fill

After `foundation-init`, fill against this build:
- `7-layers.md` — hypothesis: *a local LangGraph agent can answer bank-account
  questions strictly from a local SQLite DB, with a grounding node guaranteeing
  no answer comes from model training data.*
- `stack.md` — the locked stack above.
- `decision-log.md` — log: chosen Ollama model; SQLite-over-vector decision
  (simple structured lookups, no embeddings needed for v1); pure-terminal-before-FastAPI.
- `roadmap.md` — Phase 1 (text) → Phase 2 (voice).
- `PROGRESS.md` — track Phase 1 acceptance tests above.

---

## Constraints / stop conditions

- All local. No cloud LLM APIs, no API keys.
- Do not build Phase 2 until the four Phase 1 acceptance tests pass.
- Parameterized SQL only.
- If `ollama list` shows no suitable model, stop and tell the user which to pull.
- Keep the model name a config constant, not hardcoded throughout.
- `.gitignore`: add `__pycache__/`, `*.pyc`.
