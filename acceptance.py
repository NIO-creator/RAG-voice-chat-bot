#!/usr/bin/env python3
"""Phase 1 acceptance runner — the four probes from the Build Brief / 7-layers L1.

Runs each probe through the live graph (needs Ollama up) and checks the grounded
answer. Prints a PASS/FAIL table and exits non-zero if any probe fails.

    python acceptance.py
"""

import re
import sys

from chatbot import config
from chatbot.graph import answer, build_graph

# (question, predicate over the lowercased answer, human-readable expectation)
PROBES = [
    (
        "What's the monthly fee for the Premium account?",
        lambda a: "12" in a,
        "states 12 EUR",
    ),
    (
        "Which account earns the most interest?",
        lambda a: "savings" in a and ("2.1" in a or "2.10" in a),
        "names Savings at 2.10% AER",
    ),
    (
        "What can a 22-year-old open?",
        # eligibility list — at minimum it must surface the Student account,
        # which is the age-gated one, and must not be the refusal.
        lambda a: "student" in a and config.FALLBACK_ANSWER.lower() not in a,
        "lists eligible accounts incl. Student",
    ),
    (
        "What's the weather?",
        lambda a: config.FALLBACK_ANSWER.lower() in a or "don't have that information" in a,
        "safely refuses (fallback)",
    ),
]


def main() -> None:
    graph = build_graph()
    results = []
    for question, predicate, expectation in PROBES:
        reply = answer(graph, question)
        ok = predicate(re.sub(r"\s+", " ", reply.lower()))
        results.append((ok, question, expectation, reply))

    print("\n=== Phase 1 acceptance ===\n")
    for ok, question, expectation, reply in results:
        mark = "PASS" if ok else "FAIL"
        print(f"[{mark}] {question}")
        print(f"       expect: {expectation}")
        print(f"       got:    {reply}\n")

    passed = sum(1 for r in results if r[0])
    print(f"{passed}/{len(results)} probes passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
