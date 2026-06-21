"""Deterministic tests for the parameterized DB layer — no model required.

These pin the query patterns from data/README.md against the real accounts.db,
and double as the data-side proof for the four acceptance probes.
"""

from chatbot import db


def test_get_account_premium_fee():
    rows = db.get_account("Premium")
    assert len(rows) == 1
    assert rows[0]["monthly_fee_eur"] == 12.0


def test_get_account_is_case_insensitive():
    assert db.get_account("premium")[0]["name"] == "Premium"


def test_get_account_unknown_returns_empty():
    assert db.get_account("Platinum") == []


def test_accounts_by_interest_savings_is_highest():
    rows = db.accounts_by_interest()
    assert rows[0]["name"] == "Savings"
    assert rows[0]["interest_rate_aer"] == 2.10
    # ordered strictly descending
    rates = [r["interest_rate_aer"] for r in rows]
    assert rates == sorted(rates, reverse=True)
    # zero-interest accounts (Current, Business Starter) are excluded
    assert all(r["interest_rate_aer"] > 0 for r in rows)


def test_eligible_accounts_age_22():
    names = {r["name"] for r in db.eligible_accounts(22)}
    # 22 is within Student's 18-25 range and above every min_age of 18
    assert names == {"Current", "Savings", "Student", "Premium", "Business Starter"}


def test_eligible_accounts_age_30_excludes_student():
    names = {r["name"] for r in db.eligible_accounts(30)}
    assert "Student" not in names  # Student max_age is 25
    assert "Current" in names


def test_eligible_accounts_age_16_none():
    assert db.eligible_accounts(16) == []  # every account has min_age 18


def test_answer_faq_interest_topic():
    rows = db.answer_faq("interest")
    assert len(rows) == 2
    assert all(r["topic"] == "interest" for r in rows)


def test_answer_faq_unknown_topic_empty():
    assert db.answer_faq("crypto") == []
