"""The LangGraph graph — three real nodes + framework routing.

    START -> LLM node (brain)
    LLM node --tool_calls--> toolbox node --rows--> LLM node
    LLM node --final answer--> grounding node
    grounding node --pass--> END
    grounding node --fail (retry budget left)--> LLM node
    grounding node --fail (budget spent) / no evidence--> FALLBACK -> END

A max-iteration cap on the LLM<->toolbox loop guarantees termination.
"""

import json
import operator
from typing import Annotated, Any, Optional, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph

from . import config, db, grounding
from .tools import TOOLS, TOOLS_BY_NAME


class ChatState(TypedDict):
    """State threaded through the graph for a single user turn."""
    messages: Annotated[list, operator.add]
    retrieved_rows: Annotated[list, operator.add]  # accumulated across tool calls
    question: str  # the original user message, for grounding's question-echo pool
    iterations: int
    grounding_retries: int
    final_answer: Optional[str]


def _make_brain() -> Any:
    """Build the brain LLM (tools bound), using the swappable OLLAMA_MODEL."""
    base = ChatOllama(
        model=config.OLLAMA_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=config.OLLAMA_TEMPERATURE,
    )
    return base.bind_tools(TOOLS)


# Built once at import; the graph nodes close over these.
_BRAIN = _make_brain()
# The catalog of real account names — used by grounding to reject any account
# the model cites from memory rather than from a retrieved row.
_KNOWN_ACCOUNT_NAMES = [r["name"] for r in db.list_accounts()]


# --- Nodes -------------------------------------------------------------------

def llm_node(state: ChatState) -> dict:
    """The brain: decide to call a tool or to produce a final answer."""
    response = _BRAIN.invoke(state["messages"])
    return {"messages": [response], "iterations": state["iterations"] + 1}


def toolbox_node(state: ChatState) -> dict:
    """Execute every tool call on the last AI message; return rows + ToolMessages."""
    last = state["messages"][-1]
    tool_messages: list = []
    new_rows: list = []
    for call in last.tool_calls:
        tool = TOOLS_BY_NAME.get(call["name"])
        if tool is None:
            result = "[]"
        else:
            result = tool.invoke(call["args"])
        tool_messages.append(ToolMessage(content=result, tool_call_id=call["id"]))
        try:
            parsed = json.loads(result)
            if isinstance(parsed, list):
                new_rows.extend(parsed)
        except (ValueError, TypeError):
            pass
    return {"messages": tool_messages, "retrieved_rows": new_rows}


def grounding_node(state: ChatState) -> dict:
    """Validate the candidate answer against the retrieved rows.

    Sets final_answer when the turn is terminal (delivered answer or fallback);
    leaves it None to signal a retry back to the brain.
    """
    candidate = state["messages"][-1].content or ""
    rows = state["retrieved_rows"]

    # Layer 1 — evidence gate: no rows retrieved -> safe fallback.
    if not grounding.has_evidence(rows):
        return {"final_answer": config.FALLBACK_ANSWER}

    # Layer 2 — deterministic claim verification against the retrieved rows.
    if grounding.is_grounded(candidate, rows, state["question"], _KNOWN_ACCOUNT_NAMES):
        return {"final_answer": candidate}

    # Unsupported: retry once, then fall back.
    if state["grounding_retries"] < config.MAX_GROUNDING_RETRIES:
        nudge = HumanMessage(
            content=(
                "Your previous answer was not fully supported by the database "
                "results. Re-answer using ONLY the figures returned by the tools "
                f"in this conversation. If they don't cover the question, reply "
                f"exactly: \"{config.FALLBACK_ANSWER}\""
            )
        )
        return {"messages": [nudge], "grounding_retries": state["grounding_retries"] + 1}

    return {"final_answer": config.FALLBACK_ANSWER}


# --- Routing -----------------------------------------------------------------

def route_after_llm(state: ChatState) -> str:
    """Tool calls (within the iteration cap) -> toolbox; otherwise -> grounding."""
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None) and state["iterations"] < config.MAX_ITERATIONS:
        return "toolbox"
    return "grounding"


def route_after_grounding(state: ChatState) -> str:
    """Terminal once final_answer is set; otherwise loop back to the brain."""
    return END if state["final_answer"] is not None else "llm"


# --- Assembly ----------------------------------------------------------------

def build_graph():
    """Construct and compile the chat graph."""
    g = StateGraph(ChatState)
    g.add_node("llm", llm_node)
    g.add_node("toolbox", toolbox_node)
    g.add_node("grounding", grounding_node)

    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", route_after_llm, {"toolbox": "toolbox", "grounding": "grounding"})
    g.add_edge("toolbox", "llm")
    g.add_conditional_edges("grounding", route_after_grounding, {"llm": "llm", END: END})

    return g.compile()


def answer(graph, user_message: str) -> str:
    """Run one user turn through the graph and return the grounded final answer."""
    initial: ChatState = {
        "messages": [
            SystemMessage(content=config.SYSTEM_PROMPT),
            HumanMessage(content=user_message),
        ],
        "retrieved_rows": [],
        "question": user_message,
        "iterations": 0,
        "grounding_retries": 0,
        "final_answer": None,
    }
    result = graph.invoke(initial)
    return result["final_answer"] or config.FALLBACK_ANSWER
