"""Deterministic tests for the grounding evidence gate and claim verification.

No Ollama needed — these pin the guarantee that every delivered fact traces back
to a retrieved row (or a figure echoed from the user's question).
"""

from chatbot import grounding

KNOWN = ["Current", "Savings", "Student", "Premium", "Business Starter"]


def test_has_evidence_false_on_empty():
    assert grounding.has_evidence([]) is False


def test_has_evidence_true_when_rows_present():
    assert grounding.has_evidence([{"name": "Premium"}]) is True


def test_no_rows_is_never_grounded():
    # The off-DB refusal guarantee (e.g. "what's the weather").
    assert grounding.is_grounded("It is sunny.", [], "weather?", KNOWN) is False


def test_supported_fee_is_grounded():
    rows = [{"name": "Premium", "monthly_fee_eur": 12.0}]
    assert grounding.is_grounded(
        "The Premium account costs 12 EUR per month.", rows,
        "monthly fee for Premium?", KNOWN) is True


def test_supported_interest_decimal_normalisation():
    rows = [{"name": "Savings", "interest_rate_aer": 2.1}]
    # answer says "2.10%", row stores 2.1 — must normalise to equal.
    assert grounding.is_grounded(
        "Savings earns the most at 2.10% AER.", rows,
        "which earns most interest?", KNOWN) is True


def test_hallucinated_number_is_rejected():
    rows = [{"name": "Premium", "monthly_fee_eur": 12.0}]
    assert grounding.is_grounded(
        "The Premium account costs 15 EUR per month.", rows,
        "monthly fee for Premium?", KNOWN) is False


def test_age_echoed_from_question_is_allowed():
    rows = [
        {"name": "Student", "min_age": 18, "max_age": 25,
         "summary": "Fee-free with an interest-free overdraft for students."},
        {"name": "Current", "min_age": 18, "max_age": None,
         "summary": "Everyday account."},
    ]
    answer = "A 22-year-old can open the Student and Current accounts."
    assert grounding.is_grounded(answer, rows, "What can a 22-year-old open?", KNOWN) is True


def test_number_in_row_text_cell_is_supported():
    rows = [{"name": "Business Starter", "min_age": 18, "max_age": None,
             "summary": "Free banking for the first 18 months for new sole traders."}]
    answer = "Business Starter gives free banking for the first 18 months."
    assert grounding.is_grounded(answer, rows, "tell me about Business Starter", KNOWN) is True


def test_account_named_but_not_retrieved_is_rejected():
    # Model cites Premium from memory, but only the Savings row was retrieved.
    rows = [{"name": "Savings", "interest_rate_aer": 2.1}]
    answer = "The Premium account is the best for you."
    assert grounding.is_grounded(answer, rows, "best account?", KNOWN) is False


def test_account_name_inside_faq_text_is_supported():
    # FAQ rows have no 'name' column; account names appear inside answer text.
    rows = [{"question": "Can I have more than one account?",
             "answer": "Most customers hold a Current account alongside a Savings account.",
             "topic": "opening"}]
    answer = "Yes — most customers hold a Current account alongside a Savings account."
    assert grounding.is_grounded(answer, rows, "can I have two accounts?", KNOWN) is True


def test_debit_card_flag_not_treated_as_supported_number():
    # debit_card is a 0/1 flag; an answer claiming a "1 EUR" fee must NOT pass
    # just because a flag value happens to be 1.
    rows = [{"name": "Savings", "monthly_fee_eur": 0.0, "debit_card": 1}]
    answer = "The Savings account has a 1 EUR monthly fee."
    assert grounding.is_grounded(answer, rows, "savings fee?", KNOWN) is False
