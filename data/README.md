# Bank accounts database — `accounts.db`

The local knowledge base for the Commerzbank chatbot MVP. The LangGraph
**toolbox node** queries this SQLite file with simple SQL. No database server
needed — SQLite is a single file, read directly with Python's built-in
`sqlite3`.

## Files

- `accounts.db` — the SQLite database (the thing the toolbox queries)
- `build_db.py` — regenerates `accounts.db` from scratch (delete the `.db` and re-run)
- `README.md` — this file

## Schema

### `accounts` — one row per product (5 rows)
| column | meaning |
|---|---|
| `name` | account name (Current, Savings, Student, Premium, Business Starter) |
| `monthly_fee_eur` | monthly fee in EUR |
| `min_opening_eur` | minimum opening deposit |
| `interest_rate_aer` | interest rate, % AER (0 = none) |
| `overdraft_eur` | arranged overdraft limit |
| `overdraft_apr` | % APR on the overdraft (0 = none) |
| `debit_card` | 1 = included, 0 = not |
| `min_age` / `max_age` | eligibility age range (`max_age` NULL = no upper limit) |
| `summary` | one-line "best for" description |

### `faqs` — one row per general question (6 rows)
| column | meaning |
|---|---|
| `question` | the FAQ question |
| `answer` | the answer text |
| `topic` | grouping tag (opening, interest, branches, cards) |

## Query patterns the toolbox node will use

Look up one account by name:
```sql
SELECT * FROM accounts WHERE name = 'Savings';
```

Compare accounts (e.g. highest interest):
```sql
SELECT name, interest_rate_aer FROM accounts
WHERE interest_rate_aer > 0 ORDER BY interest_rate_aer DESC;
```

Eligibility filter (e.g. accounts a 22-year-old can open):
```sql
SELECT name FROM accounts
WHERE min_age <= 22 AND (max_age IS NULL OR max_age >= 22);
```

Answer a general question:
```sql
SELECT answer FROM faqs WHERE topic = 'interest';
```

## Grounding note

Because every answer comes from a row in this DB, the **grounding-check node**
has a clean job: confirm the chatbot's reply matches what the query returned,
and fall back to "I don't have that information" when no row matches. The DB is
the single source of truth — nothing is answered from the model's training data.
