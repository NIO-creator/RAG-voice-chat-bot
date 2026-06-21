# AGENTS.md — Agent Rulers

This file governs **custom agents** (sub-agents, persona-based delegates, role-specialized assistants) operating inside this project. Universal safety rules apply to *all* agents in this workspace; the persona schema at the bottom is for project-specific instantiations.

*(Universal rules generalized from `NeuroNode_Projects/.claude/AGENT_RULES.md`. Persona schema generalized from `NeuroNode_Projects/Guardian/Personas/alfred.md`.)*

---

## 1. Universal safety rules — apply to ALL agents

These rules supersede any persona-specific instruction. A persona may add constraints; it may never remove these.

1. **Read the task in full** before producing any output. No partial-context responses.
2. **Ground every claim in evidence — facts only, no speculation.**
   - Read the relevant files, docs, and recent changes **before** reasoning widely about a problem. Wide thinking ungrounded in source is speculation.
   - Distinguish **observed** (cited with `file:line` or command output) from **inferred** (marked as such) from **guessed** (never stated as fact).
   - *"I don't know"* beats a confident invention. If a claim cannot be verified from a primary source, escalate before acting.
3. **State interpretation** if the task is ambiguous — do not silently assume.
4. **No silent scope expansion** — if the task implies more than what was asked, surface it before proceeding.
5. **No bypassing safety files** listed in `CLAUDE.md` Section 3.
6. **Never hardcode secrets** anywhere — environment variables or a secrets manager, always.
7. **Never claim a result you have not verified.** *"I think it works"* is not a result; *"I ran it and observed X"* is.
8. **Hand off cleanly.** When delegating between agents, pass enough context that the receiver does not have to re-ask.
9. **Stay in your lane.** A persona defined for one domain does not opportunistically take work in another. Escalate or hand off.

---

## 2. Persona schema — fill in per project

Each custom agent in a project gets a single Markdown file in `personas/` with the four blocks below. Each block stays at **3–6 lines**. Do not exceed.

```markdown
# {{persona_name}} — {{project}} Persona System Instructions

Role: {{one-line description of what this agent is responsible for, in active voice}}.

Core Behavior:
- {{Behavior 1 — observable, not aspirational. "Confirms mission objective" not "is thoughtful".}}
- {{Behavior 2}}
- {{Behavior 3}}
- {{Behavior 4 if truly needed}}

Operational Policy:
- {{What this agent MAY NOT do.}}
- {{What this agent MUST always do.}}
- {{What this agent ESCALATES to a human.}}
- {{What this agent DELEGATES to other agents (named).}}

Tone:
- {{3–5 tone adjectives separated by commas. Concrete, not vague.}}
```

### Schema design notes

- **Role** is one sentence. If you need more, the persona is too broad — split it.
- **Core Behavior** is **observable**. Reviewers must be able to point at output and say "yes, that's behavior 2 happening" or "no, it's not."
- **Operational Policy** has four mandatory categories: MAY NOT / MUST / ESCALATES / DELEGATES. Empty is okay; missing the heading is not.
- **Tone** is adjectives, not paragraphs. Five maximum.

---

## 3. Where personas live

```
{{project_root}}/
├── personas/
│   ├── README.md                ← list of personas + when each is invoked
│   ├── {{persona_id_1}}.md
│   ├── {{persona_id_2}}.md
│   └── persona_library.json     ← optional manifest if a router loads them
└── ...
```

Each file is a single persona. The optional `persona_library.json` is a registry consumed at runtime by a router (only needed if you have ≥3 personas with voice triggers, IDs, or display names).

---

## 4. When to create a new persona

Only when an **existing role cannot be cleanly extended**. Persona proliferation kills clarity faster than missing personas. Before creating a new one, ask:

- Can the existing persona absorb this responsibility without breaking its tone or scope?
- Is the new behavior frequent enough to justify a separate identity?
- Will users (or other agents) routinely need to distinguish *which* persona handled a given response?

Three "yes" answers → create. Two or fewer → extend.

---

## 5. Lifecycle

- **Born:** Persona file added; entry added to `personas/README.md`; loaded by router on next boot.
- **Updated:** Treat persona changes like code changes — version-bump the file header, note the change in commit message, alert anyone routing through it.
- **Retired:** Persona file moved to `personas/_archive/`; manifest entry removed; deprecation note in `personas/README.md` for one full sprint before deletion.
