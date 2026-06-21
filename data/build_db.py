"""
build_db.py — creates accounts.db, a small SQLite knowledge base for the
Commerzbank chatbot MVP.

Reproducible: delete accounts.db and re-run to rebuild from scratch.
The toolbox node in the LangGraph chatbot queries this with simple SQL,
e.g.  SELECT * FROM accounts WHERE name = 'Savings';

Tables:
  accounts  — one row per account product (the structured records)
  faqs      — one row per general question/answer (simple lookups)
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "accounts.db"

# Wipe and rebuild so the script is idempotent.
if DB_PATH.exists():
    DB_PATH.unlink()

con = sqlite3.connect(DB_PATH)
cur = con.cursor()

cur.executescript(
    """
    CREATE TABLE accounts (
        id                INTEGER PRIMARY KEY,
        name              TEXT    NOT NULL UNIQUE,
        monthly_fee_eur   REAL    NOT NULL,
        min_opening_eur   REAL    NOT NULL,
        interest_rate_aer REAL    NOT NULL,   -- annual equivalent rate, %
        overdraft_eur     REAL    NOT NULL,   -- arranged overdraft limit
        overdraft_apr     REAL    NOT NULL,   -- % APR on the overdraft, 0 if none
        debit_card        INTEGER NOT NULL,   -- 1 = included, 0 = not
        min_age           INTEGER NOT NULL,
        max_age           INTEGER,            -- NULL = no upper limit
        summary           TEXT    NOT NULL    -- one-line "best for" description
    );

    CREATE TABLE faqs (
        id       INTEGER PRIMARY KEY,
        question TEXT NOT NULL,
        answer   TEXT NOT NULL,
        topic    TEXT NOT NULL
    );
    """
)

accounts = [
    # name, fee, min_open, aer, od_limit, od_apr, card, min_age, max_age, summary
    ("Current",          3.0,   0.0,  0.00,  500.0,  9.9, 1, 18, None,
     "Everyday account for salary, bills, and card payments."),
    ("Savings",          0.0, 100.0,  2.10,    0.0,  0.0, 0, 18, None,
     "Earns interest; for building an emergency fund or saving toward a goal."),
    ("Student",          0.0,   0.0,  0.50, 1000.0,  0.0, 1, 18, 25,
     "Fee-free with an interest-free overdraft for students."),
    ("Premium",         12.0,   0.0,  0.25, 2000.0,  7.9, 1, 18, None,
     "Bundles travel and phone insurance plus lounge access for frequent travelers."),
    ("Business Starter", 0.0,   0.0,  0.00,    0.0,  0.0, 1, 18, None,
     "Free banking for the first 18 months for new sole traders and small businesses."),
]

cur.executemany(
    """INSERT INTO accounts
       (name, monthly_fee_eur, min_opening_eur, interest_rate_aer,
        overdraft_eur, overdraft_apr, debit_card, min_age, max_age, summary)
       VALUES (?,?,?,?,?,?,?,?,?,?)""",
    accounts,
)

faqs = [
    ("How do I open an account?",
     "You can open any personal account online at acmebank.example or in any "
     "branch. Bring photo ID and proof of address.",
     "opening"),
    ("Can I have more than one account?",
     "Yes. Most customers hold a Current account alongside a Savings account. "
     "A Savings account requires an existing Current account.",
     "opening"),
    ("How is interest paid?",
     "Interest is calculated daily and paid on the first day of each month "
     "into the same account.",
     "interest"),
    ("What is AER?",
     "AER stands for Annual Equivalent Rate. It shows what the interest rate "
     "would be if interest were paid and compounded once per year, so accounts "
     "can be compared fairly.",
     "interest"),
    ("What are your branch opening hours?",
     "Branches are open Monday to Friday 9:00-17:00 and Saturday 9:00-13:00. "
     "They are closed on Sundays.",
     "branches"),
    ("How do I report a lost or stolen card?",
     "Call the 24/7 card line immediately to freeze the card, then request a "
     "replacement in the app or in any branch.",
     "cards"),
]

cur.executemany(
    "INSERT INTO faqs (question, answer, topic) VALUES (?,?,?)",
    faqs,
)

con.commit()

# Quick self-check / summary
n_acc = cur.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
n_faq = cur.execute("SELECT COUNT(*) FROM faqs").fetchone()[0]
print(f"Built {DB_PATH.name}: {n_acc} accounts, {n_faq} faqs")
print("\nSample query — accounts with interest, best first:")
for row in cur.execute(
    "SELECT name, interest_rate_aer FROM accounts "
    "WHERE interest_rate_aer > 0 ORDER BY interest_rate_aer DESC"
):
    print(f"  {row[0]:<16} {row[1]:.2f}% AER")

con.close()
