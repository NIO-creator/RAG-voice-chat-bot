"""Database access — the only module that touches accounts.db.

Every query is parameterized (`?` placeholders); no string-concatenated SQL ever
reaches sqlite3. These four functions mirror the query patterns documented in
data/README.md: lookup-by-name, comparison, eligibility filter, FAQ-by-topic.
"""

import sqlite3
from typing import Any

from . import config


def _connect() -> sqlite3.Connection:
    """Open a read-only-style connection with dict-like rows."""
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _rows_to_dicts(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [dict(r) for r in rows]


def get_account(name: str) -> list[dict[str, Any]]:
    """Look up one account product by name (case-insensitive exact match).

    Mirrors README pattern: SELECT * FROM accounts WHERE name = ?.
    """
    con = _connect()
    try:
        rows = con.execute(
            "SELECT * FROM accounts WHERE LOWER(name) = LOWER(?)",
            (name.strip(),),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        con.close()


def list_accounts() -> list[dict[str, Any]]:
    """Return all accounts with their headline figures, for overview/comparison."""
    con = _connect()
    try:
        rows = con.execute(
            "SELECT name, monthly_fee_eur, min_opening_eur, interest_rate_aer, "
            "overdraft_eur, overdraft_apr, debit_card, min_age, max_age, summary "
            "FROM accounts ORDER BY name"
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        con.close()


def accounts_by_interest() -> list[dict[str, Any]]:
    """Interest-bearing accounts, highest AER first (the 'most interest' query).

    Mirrors README pattern: ... WHERE interest_rate_aer > 0 ORDER BY ... DESC.
    """
    con = _connect()
    try:
        rows = con.execute(
            "SELECT name, interest_rate_aer FROM accounts "
            "WHERE interest_rate_aer > 0 ORDER BY interest_rate_aer DESC"
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        con.close()


def eligible_accounts(age: int) -> list[dict[str, Any]]:
    """Accounts a person of the given age can open (eligibility filter).

    Mirrors README pattern: ... WHERE min_age <= ? AND (max_age IS NULL OR max_age >= ?).
    """
    con = _connect()
    try:
        rows = con.execute(
            "SELECT name, min_age, max_age, summary FROM accounts "
            "WHERE min_age <= ? AND (max_age IS NULL OR max_age >= ?) "
            "ORDER BY name",
            (age, age),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        con.close()


def answer_faq(topic: str) -> list[dict[str, Any]]:
    """Fetch FAQ entries for a topic (opening, interest, branches, cards)."""
    con = _connect()
    try:
        rows = con.execute(
            "SELECT question, answer, topic FROM faqs WHERE LOWER(topic) = LOWER(?)",
            (topic.strip(),),
        ).fetchall()
        return _rows_to_dicts(rows)
    finally:
        con.close()
