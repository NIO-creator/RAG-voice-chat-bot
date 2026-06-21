"""LangChain tools the brain can call — the toolbox surface.

Each tool is a thin, well-described wrapper over a parameterized query in db.py.
Descriptions matter: the LLM routes on them, so they state exactly when to use
each tool. Tools return JSON strings so the result is unambiguous to the model
and easy for the grounding node to scan.
"""

import json

from langchain_core.tools import tool

from . import db


@tool
def get_account(name: str) -> str:
    """Look up ONE account product by its exact name to get its fees, interest
    rate, overdraft, debit card, age eligibility and summary.
    Valid names: Current, Savings, Student, Premium, Business Starter.
    Use this for questions about a specific named account (e.g. "what is the
    monthly fee for the Premium account")."""
    return json.dumps(db.get_account(name))


@tool
def list_accounts() -> str:
    """List ALL account products with their headline figures (fee, interest,
    overdraft, eligibility, summary). Use this for broad or comparison questions
    that are not about interest specifically (e.g. "what accounts do you offer",
    "which is cheapest", "compare the accounts")."""
    return json.dumps(db.list_accounts())


@tool
def accounts_by_interest() -> str:
    """List interest-bearing accounts ordered by interest rate, highest first.
    Use this for any question about which account earns the most/best interest
    or to rank accounts by interest rate."""
    return json.dumps(db.accounts_by_interest())


@tool
def eligible_accounts(age: int) -> str:
    """List the accounts a person of the given age is eligible to open.
    Use this whenever the question mentions a person's age (e.g. "what can a
    22-year-old open"). Pass the age as an integer."""
    return json.dumps(db.eligible_accounts(age))


@tool
def answer_faq(topic: str) -> str:
    """Fetch general banking FAQ answers for a topic. Valid topics:
    'opening' (how to open an account, multiple accounts),
    'interest' (how interest is paid, what AER means),
    'branches' (opening hours),
    'cards' (lost or stolen card).
    Use this for general how-to questions rather than product figures."""
    return json.dumps(db.answer_faq(topic))


# Registry consumed by the graph: bound to the LLM and executed by the toolbox node.
TOOLS = [get_account, list_accounts, accounts_by_interest, eligible_accounts, answer_faq]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
