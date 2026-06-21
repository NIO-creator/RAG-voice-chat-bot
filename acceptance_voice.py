#!/usr/bin/env python3
"""Phase 2 acceptance — proves the voice wrapper without needing a human mic.

Two checks:
  1. The four Phase 1 probes still pass *through the FastAPI /chat endpoint*
     (grounding is unchanged; the HTTP layer only transports text).
  2. The local voice loopback works: Piper speaks a sentence to a WAV, Whisper
     transcribes it back, and the meaning survives.

Needs Ollama up and the local speech models available. Run:
    python acceptance_voice.py
"""

import re
import sys

from fastapi.testclient import TestClient

from chatbot import config
from chatbot.voice import stt, tts

# --- 1. /chat endpoint: the four probes through HTTP -------------------------

PROBES = [
    ("What's the monthly fee for the Premium account?", lambda a: "12" in a, "12 EUR"),
    ("Which account earns the most interest?",
     lambda a: "savings" in a and ("2.1" in a or "2.10" in a), "Savings 2.10% AER"),
    ("What can a 22-year-old open?",
     lambda a: "student" in a and config.FALLBACK_ANSWER.lower() not in a, "eligibility list"),
    ("What's the weather?",
     lambda a: config.FALLBACK_ANSWER.lower() in a, "safe fallback"),
]

# --- 2. voice loopback: Piper -> Whisper -------------------------------------
# Assert on stable content words only. Whisper normalizes numbers/currency
# nondeterministically ("twelve euros" -> "12 euros" or "€12"), so checking
# currency/number tokens is brittle; the meaning-bearing nouns are stable.

LOOPBACK = [
    ("The monthly fee for the Premium account is twelve euros.", ["monthly", "premium"]),
    ("The Savings account earns the most interest.", ["savings", "interest"]),
]


def run_api_probes() -> list[tuple]:
    from server import app  # imports trigger graph build via lifespan

    results = []
    with TestClient(app) as client:  # lifespan builds the graph
        for question, predicate, expectation in PROBES:
            answer = client.post("/chat", json={"message": question}).json()["answer"]
            ok = predicate(re.sub(r"\s+", " ", answer.lower()))
            results.append(("API", ok, question, expectation, answer))
    return results


def run_voice_loopback() -> list[tuple]:
    results = []
    for phrase, must_contain in LOOPBACK:
        wav = tts.synthesize_to_wav(phrase)
        heard = stt.transcribe_wav(wav).lower()
        ok = all(token in heard for token in must_contain)
        results.append(("VOICE", ok, phrase, f"heard contains {must_contain}", heard))
    return results


def main() -> None:
    print("Running /chat endpoint probes (through FastAPI)...")
    results = run_api_probes()
    print("Running Piper -> Whisper voice loopback...")
    results += run_voice_loopback()

    print("\n=== Phase 2 acceptance ===\n")
    for kind, ok, src, expectation, got in results:
        print(f"[{'PASS' if ok else 'FAIL'}] ({kind}) {src}")
        print(f"       expect: {expectation}")
        print(f"       got:    {got}\n")

    passed = sum(1 for r in results if r[1])
    print(f"{passed}/{len(results)} checks passed")
    sys.exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    main()
