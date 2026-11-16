# 🗄️ Text-to-SQL Assistant

Ask a question in plain English and get an answer from a database. The app turns the
question into a **read-only SQL query**, runs it against a sample e-commerce database,
and shows the SQL it generated alongside the results.

**It runs free with no API key** thanks to a built-in demo mode (curated example
questions). Add an OpenAI key to ask your own questions in natural language.

> I built this to show a safe, practical LLM-over-data pattern: schema-aware SQL
> generation, a read-only safety guard, and both a CLI and a web UI.

---

## What it does

```
   question (English)
        │     (+ database schema as context)
        ▼
   LLM  ─►  SQL (SELECT only)  ─►  safety check  ─►  run on SQLite  ─►  results table
                                   (rejects anything that isn't a single SELECT)
```

In **demo mode** (no key) the LLM step is replaced by a set of curated example
questions with known SQL, so the full "SQL → run → results" flow still works for free.

## Features

- **Read-only by design** — a safety guard (`src/db.py`) rejects anything that is not a
  single `SELECT`, so a generated query can never modify the database.
- **Schema-aware** — the database schema is given to the model as context, so queries
  use the real tables and columns.
- **Runs free** — a demo mode with curated examples means no API key is needed to try it.
- **Two interfaces** — a CLI (`src/cli.py`) and a Streamlit web UI (`src/app.py`) that
  shows the generated SQL and the results.
- **Self-contained data** — a small, deterministic SQLite e-commerce database
  (customers, products, orders, order_items) built by a script.

## Tech stack

Python · SQLite · LangChain + OpenAI (optional, for natural-language questions) · Streamlit

## Quickstart (free, no API key)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1. build the sample database
python -m src.build_db

# 2a. demo mode in the terminal (pick an example)
python -m src.cli

# 2b. or launch the web UI
streamlit run src/app.py
```

**Optional — ask your own questions.** Add `OPENAI_API_KEY=sk-...` to `.env`
(`cp .env.example .env`). With a key, type any question and the model writes the SQL:

```bash
python -m src.cli "Who are the top 3 customers by total spend?"
```

## The sample database

```
customers(id, name, city, country, signup_date)
products(id, name, category, price)
orders(id, customer_id, order_date, status)
order_items(id, order_id, product_id, quantity)
```

Example questions it can answer: *"Which 5 products earned the most revenue?"*,
*"Total revenue by category"*, *"Top 3 customers by spend"*, *"Orders per status"*.

## Project structure

```
text-to-sql-assistant/
├── data/                  # generated SQLite database (build with src.build_db)
├── examples/
│   └── examples.json      # curated question -> SQL pairs (demo mode)
├── src/
│   ├── config.py          # env-driven configuration
│   ├── build_db.py        # create the sample database
│   ├── db.py              # schema + read-only SELECT execution (safety guard)
│   ├── nl2sql.py          # LLM: question + schema -> SQL
│   ├── cli.py             # command-line interface
│   └── app.py             # Streamlit UI
├── requirements.txt
├── .env.example
└── Makefile               # make install | build | ask | app
```

## Design notes & possible extensions

- **Why read-only?** Text-to-SQL on a live database is risky; constraining generation to
  a single `SELECT` and validating it before execution is the safety baseline.
- **Next steps I'd add:** return-row limits and query timeouts, an "explain this query"
  mode, few-shot examples to improve hard joins, and support for Postgres.

## License

MIT — see [LICENSE](LICENSE).
