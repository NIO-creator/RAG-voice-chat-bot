#!/usr/bin/env python3
"""Phase 2 — FastAPI wrapper around the unchanged Phase 1 graph.

    uvicorn server:app --host 127.0.0.1 --port 8000
    # or simply:  python server.py

Exposes POST /chat {"message": "..."} -> {"answer": "..."}. The voice client
(voice_chat.py) is one consumer; the same endpoint serves any text client. The
grounding guarantee is entirely inside the graph — this layer adds nothing and
removes nothing, it only transports text.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

from chatbot import config
from chatbot.graph import answer, build_graph

# Built once at startup; reused across requests (the graph is stateless per turn).
_graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _graph
    _graph = build_graph()
    yield


app = FastAPI(title="Commerzbank Chatbot", version="2.0", lifespan=lifespan)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's question.")


class ChatResponse(BaseModel):
    answer: str


@app.get("/health")
def health() -> dict:
    """Liveness probe — confirms the graph is built and identifies this service."""
    return {
        "service": config.HEALTH_MARKER,
        "status": "ok",
        "model": config.OLLAMA_MODEL,
        "graph_ready": _graph is not None,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    """Run one grounded turn through the Phase 1 graph and return the answer."""
    return ChatResponse(answer=answer(_graph, req.message))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.API_HOST, port=config.API_PORT)
