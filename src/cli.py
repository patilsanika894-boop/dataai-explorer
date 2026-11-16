"""Command-line interface.

With an OpenAI key:   python -m src.cli "Which 5 products earned the most revenue?"
Without a key:        python -m src.cli      (demo mode: pick a curated example)
"""
import json
import sys

from src.config import EXAMPLES_FILE, llm_available
from src.db import run_select
from src.nl2sql import generate_sql


def _print_table(columns, rows) -> None:
    widths = [len(c) for c in columns]
    for row in rows:
        for i, value in enumerate(row):
            widths[i] = max(widths[i], len(str(value)))
    line = " | ".join(c.ljust(widths[i]) for i, c in enumerate(columns))
    print(line)
    print("-+-".join("-" * w for w in widths))
    for row in rows[:50]:
        print(" | ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)))
    print(f"\n({len(rows)} rows)")


def _run(sql: str) -> None:
    print(f"\nSQL: {sql}\n")
    columns, rows = run_select(sql)
    _print_table(columns, rows)


def _ask(question: str) -> None:
    _run(generate_sql(question))


def _demo() -> None:
    examples = json.loads(EXAMPLES_FILE.read_text(encoding="utf-8"))
    print("No OpenAI key set, running in demo mode. Example questions:\n")
    for i, e in enumerate(examples, 1):
        print(f"  {i}. {e['question']}")
    choice = input("\nPick a number: ").strip()
    example = examples[int(choice) - 1]
    print(f"\nQ: {example['question']}")
    _run(example["sql"])


def main() -> None:
    if not llm_available():
        _demo()
        return
    if len(sys.argv) > 1:
        _ask(" ".join(sys.argv[1:]))
        return
    print("Text-to-SQL Assistant. Ask a question (Ctrl-C to exit).")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        try:
            _ask(question)
        except Exception as exc:  # noqa: BLE001
            print("Error:", exc)


if __name__ == "__main__":
    main()
