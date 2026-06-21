# CLAUDE.md — Project Operating Rules

> These rules apply to every task executed in this workspace.
> Read this file before executing any task. No exceptions.

*(Generalized from `NeuroNode_Projects/.claude/AGENT_RULES.md` v1.2.0 — strip the per-project specifics here and replace `{{...}}` placeholders at project init.)*

---

## 1. Identity & context

You are executing tasks for **Commerzbank-chatbot** — a grounded, all-local LangGraph chatbot that answers retail bank-account questions strictly from a local SQLite DB (`data/accounts.db`), guaranteeing no answer is sourced from model training data.

- Target environment: Linux; local-only; offline-first (no cloud, no API keys).
- Languages at runtime: Python 3.12; LangGraph; local Ollama (`qwen2.5:7b`); built-in `sqlite3`.
- Operating principle: **grounded-or-refuse** — every delivered fact traces to a queried row, else return the safe fallback.
- Hard constraints: never add a cloud LLM/API dependency; never introduce string-concatenated SQL (parameterized only); never let an answer through that the retrieved rows don't support; keep the model name a config constant (`OLLAMA_MODEL`); don't build Phase 2 (voice) until the 4 Phase 1 probes pass.

---

## 2. Ground first — facts before reasoning

> **The most expensive bug is the one Claude invented to fill a knowledge gap.**
> Avoid it by grounding every reasoning step in evidence before the reasoning happens.

### 2.1 Read before reasoning

1. **Read the task prompt in full** before touching any file.
2. **Identify every file the task will modify.**
3. **Read each file in full** before modifying it.
4. **Read the relevant docs** — `PROGRESS.md`, `ARCHITECTURE.md`, ADRs, prior PR descriptions — **before** reasoning widely about the problem. Wide thinking ungrounded in source is speculation.
5. **State your interpretation** if the task is ambiguous — do not silently assume.
6. **Stop if scope expands** — if the task would touch a file not listed in the prompt, report it before proceeding.

### 2.2 Facts only — no speculation

Every non-trivial claim you make falls into one of three states. Mark it.

| State | Definition | Required citation |
|---|---|---|
| **Observed** | Verified by reading the file, running the code, or checking output. | `file:line`, command + output, test name |
| **Inferred** | Logically derived from one or more observed facts. | "Inferred from X" |
| **Guessed** | No evidence. | **Do not state.** Find the evidence, or say "I don't know." |

Additional rules:

- **"I don't know" is a valid answer.** Inventing one is not.
- **If a claim cannot be verified** from a primary source inside the project or its referenced docs, **escalate before acting on it**.
- **Never claim a result you have not verified.** *"I think it works"* is not a result; *"I ran X and observed Y"* is.

### 2.3 Work in phases

7. **Sprints and tasks are executed in sequential Phases.** Each Phase produces one focused deliverable. Do not proceed to the next Phase without explicit confirmation. Never combine Phases or run ahead of instruction.

---

## 3. Code quality rules

### General
- Prefer explicit over implicit. Prefer clear over clever.
- Never hardcode secrets, passwords, or API keys.
- Never use `git add .` — stage specific files only.
- All new public methods get a docstring.
- New runtime dependencies require approval (note in the PR description).
- Match the existing style of the file you are editing. Do not impose your own.

### Safety-critical files
List the files at project init. Modifying any of them requires:
- Never remove existing safety checks.
- Never change public method signatures without explicit instruction.
- Never bypass guard calls or skip validation.

```
chatbot/grounding.py   # the grounding guarantee — never weaken the evidence gate or claim checks
chatbot/db.py          # parameterized SQL only — never concatenate query strings
data/accounts.db       # source of truth — regenerate via data/build_db.py, never hand-edit
data/build_db.py       # the DB's reproducible definition
```

If a safety-critical file is touched, the test gate (Section 6) must pass and the diff must be reviewed by a human before commit.

---

## 4. Response style

- Default to brevity. One sentence beats a paragraph.
- State results and decisions directly. Do not narrate deliberation.
- When uncertain, ask one specific clarifying question instead of guessing.
- No emojis unless explicitly requested.
- Code references use `path/to/file.py:42` format so they are clickable in the IDE.

---

## 5. Escalation rules — stop and ask the human when

- Scope expands beyond the original task description.
- The work would touch a file listed in Section 3 (safety-critical).
- Test failures cannot be explained or reproduced after one good-faith attempt.
- The user's intent is genuinely ambiguous after re-reading the prompt.
- A new runtime dependency is needed.
- A destructive operation is about to happen (rm, force-push, drop table, delete branch).

The cost of pausing to confirm is low. The cost of an unwanted destructive action is high.

---

## 6. Test gate — mandatory

The test suite must pass before every commit. No exceptions.

```bash
. .venv/bin/activate && python -m pytest -q          # deterministic unit gate (no model needed)
. .venv/bin/activate && python acceptance.py         # Phase 1: live 4-probe acceptance (needs Ollama)
. .venv/bin/activate && python acceptance_voice.py   # Phase 2: /chat probes + Piper→Whisper loopback (needs Ollama + speech models)
```

### Rules:
- If **0 tests fail** → proceed to git operations.
- If **any test fails** → STOP. Do not commit. Report:
  - Which test failed
  - The failure message
  - Your hypothesis for the cause
  - The proposed fix (do not apply it without confirmation)

---

## 7. Git discipline

- Stage specific files only. `git add path/to/file` — never `git add .`.
- Commits are NEW commits, not amends, unless the human explicitly asks for an amend.
- Never `--no-verify`. Hooks exist for a reason. If a hook fails, fix the underlying issue.
- Never `git push --force` to a shared branch (main, develop, release).
- One logical change per commit. If the diff covers two unrelated things, split them.

---

## 8. When in doubt

Re-read this file. Then re-read the task. Then ask one question. Acting fast on a wrong interpretation costs more than asking for ten seconds of clarification.
