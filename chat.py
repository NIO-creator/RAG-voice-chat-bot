#!/usr/bin/env python3
"""Phase 1 terminal interface — run the grounded chatbot in a stdin/stdout loop.

    python chat.py

Type a question; the graph answers strictly from data/accounts.db. Type
'exit', 'quit', or Ctrl-D to leave.
"""

import sys
import urllib.error
import urllib.request

from chatbot import config
from chatbot.graph import answer, build_graph


def _preflight() -> None:
    """Fail loud and early if the local DB or Ollama model is unavailable."""
    if not config.DB_PATH.exists():
        sys.exit(
            f"Database not found at {config.DB_PATH}.\n"
            "Build it with:  python data/build_db.py"
        )
    try:
        with urllib.request.urlopen(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5) as r:
            tags = r.read().decode()
    except (urllib.error.URLError, OSError) as exc:
        sys.exit(
            f"Cannot reach Ollama at {config.OLLAMA_BASE_URL} ({exc}).\n"
            "Start it with:  ollama serve"
        )
    model_base = config.OLLAMA_MODEL.split(":")[0]
    if config.OLLAMA_MODEL not in tags and model_base not in tags:
        sys.exit(
            f"Model '{config.OLLAMA_MODEL}' is not installed in Ollama.\n"
            f"Pull it with:  ollama pull {config.OLLAMA_MODEL}\n"
            "(or change OLLAMA_MODEL in chatbot/config.py to an installed model)."
        )


def main() -> None:
    _preflight()
    print(f"Commerzbank account assistant (local, grounded — model: {config.OLLAMA_MODEL})")
    print("Ask about accounts, fees, interest, eligibility, or FAQs. Type 'exit' to quit.\n")
    graph = build_graph()
    while True:
        try:
            user = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return
        if not user:
            continue
        if user.lower() in {"exit", "quit"}:
            print("bye")
            return
        reply = answer(graph, user)
        print(f"bot> {reply}\n")


if __name__ == "__main__":
    main()
