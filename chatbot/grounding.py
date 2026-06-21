"""Grounding — the node that guarantees answers come from data, not training.

Two layers, both must pass for an answer to be delivered:

1. Evidence gate (deterministic): if zero rows were retrieved this turn, no
   substantive answer is allowed — the turn returns the safe fallback. This
   alone guarantees the off-DB refusal case (e.g. "weather").

2. Claim verification (deterministic): every concrete claim in the answer must
   trace back to the retrieved rows —
     * every number stated (fee, rate, age, count) must appear in a retrieved
       row value, in text inside a retrieved row, or be a figure echoed from the
       user's own question; and
     * every real account product named in the answer must be one whose row was
       actually retrieved (the model may not cite an account from memory).
   A number or account the rows don't support means the answer leaned on
   training data -> reject -> retry once -> fallback.

Both checks are deterministic and unit-tested. An earlier LLM-judge design was
reversed when it false-rejected a fully grounded answer (see decision-log D-04).
"""

import re
from typing import Any

# Matches integers and decimals: 12, 2.1, 2.10, 1000
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
_TOLERANCE = 1e-9

# Columns whose values are NOT user-facing figures (a boolean flag stored as
# 0/1, a surrogate id). Excluded from the supported-number pool so a coincidental
# flag value can't vouch for a fabricated figure in the answer.
NON_FIGURE_COLUMNS = {"id", "debit_card"}


def has_evidence(retrieved_rows: list[dict[str, Any]]) -> bool:
    """True iff at least one row was retrieved from the DB this turn."""
    return len(retrieved_rows) > 0


def _numbers_in(text: str) -> set[float]:
    return {float(m) for m in _NUMBER_RE.findall(text or "")}


def _supported_number_pool(retrieved_rows: list[dict[str, Any]], question: str) -> set[float]:
    """All numbers the answer is allowed to state: those in the retrieved rows
    (scalar values and numbers embedded in text cells) plus figures echoed from
    the user's question (e.g. an age the user supplied)."""
    pool: set[float] = set()
    for row in retrieved_rows:
        for key, value in row.items():
            if key in NON_FIGURE_COLUMNS:
                continue  # flags / ids are not claimable figures
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                pool.add(float(value))
            elif isinstance(value, str):
                pool |= _numbers_in(value)
    pool |= _numbers_in(question)
    return pool


def _row_text(retrieved_rows: list[dict[str, Any]]) -> str:
    """All retrieved cell values flattened to one lowercase string."""
    return " ".join(str(v) for row in retrieved_rows for v in row.values()).lower()


def _names_unsupported(answer: str, retrieved_rows: list[dict[str, Any]],
                       known_account_names: list[str]) -> bool:
    """True if the answer names a real account product that appears NOWHERE in the
    retrieved rows — i.e. the model cited an account from memory. A name counts as
    supported whether it surfaced as an account row or inside FAQ answer text."""
    answer_low = answer.lower()
    retrieved_text = _row_text(retrieved_rows)
    for name in known_account_names:
        nl = name.lower()
        mentioned = re.search(rf"\b{re.escape(nl)}\b", answer_low) is not None
        if mentioned and nl not in retrieved_text:
            return True
    return False


def is_grounded(answer: str, retrieved_rows: list[dict[str, Any]], question: str,
                known_account_names: list[str]) -> bool:
    """Deterministic verdict: is every concrete claim in the answer supported?"""
    if not has_evidence(retrieved_rows):
        return False
    if _names_unsupported(answer, retrieved_rows, known_account_names):
        return False
    pool = _supported_number_pool(retrieved_rows, question)
    for n in _numbers_in(answer):
        if not any(abs(n - p) < _TOLERANCE for p in pool):
            return False
    return True
