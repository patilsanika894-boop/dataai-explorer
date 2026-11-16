
"""Local RAG retrieval for the Text-to-SQL assistant."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_FILE = ROOT / "examples" / "examples.json"

# Common words that do not usually describe the user's query intent.
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been",
    "to", "of", "in", "on", "at", "for", "from", "by", "with",
    "and", "or", "me", "my", "all", "show", "find", "get", "give",
    "what", "which", "who", "how", "many", "much", "please",
    "i", "we", "you", "it", "this", "that", "has", "have",
}

# Similar meanings are grouped to improve simple keyword retrieval.
SYNONYMS = {
    "highest": {"highest", "maximum", "max", "top", "largest", "most"},
    "maximum": {"highest", "maximum", "max", "top", "largest", "most"},
    "max": {"highest", "maximum", "max", "top", "largest", "most"},
    "largest": {"highest", "maximum", "max", "top", "largest", "most"},
    "most": {"highest", "maximum", "max", "top", "largest", "most"},
    "lowest": {"lowest", "minimum", "min", "smallest", "least"},
    "minimum": {"lowest", "minimum", "min", "smallest", "least"},
    "cheapest": {"cheapest", "lowest", "minimum", "min", "price"},
    "expensive": {"expensive", "highest", "maximum", "price"},
    "price": {"price", "cost", "expensive", "cheapest"},
    "cost": {"price", "cost", "expensive", "cheapest"},
    "sales": {"sales", "sold", "sell", "selling", "orders"},
    "sold": {"sales", "sold", "sell", "selling", "orders"},
    "sells": {"sales", "sold", "sell", "selling", "orders"},
    "revenue": {"revenue", "income", "earnings", "sales"},
    "earnings": {"revenue", "income", "earnings", "sales"},
    "student": {"student", "students", "marks", "score", "scores"},
    "students": {"student", "students", "marks", "score", "scores"},
    "marks": {"student", "students", "marks", "score", "scores", "grade"},
    "score": {"student", "students", "marks", "score", "scores", "grade"},
    "customer": {"customer", "customers", "buyer", "buyers"},
    "customers": {"customer", "customers", "buyer", "buyers"},
}


def tokenize(text: str) -> set[str]:
    """Convert text into searchable lowercase keywords."""
    words = re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*", text.lower())
    return {
        word for word in words
        if len(word) > 1 and word not in STOP_WORDS
    }


def expand_words(words: set[str]) -> set[str]:
    """Expand keywords using the synonym groups."""
    expanded = set(words)

    for word in words:
        expanded.update(SYNONYMS.get(word, {word}))

    return expanded


def extract_tables(sql: str) -> set[str]:
    """Extract table names following FROM and JOIN."""
    return {
        match.lower()
        for match in re.findall(
            r"\b(?:FROM|JOIN)\s+[\"`]?([A-Za-z_][A-Za-z_0-9]*)",
            sql,
            flags=re.IGNORECASE,
        )
    }


def retrieve_examples(
    question: str,
    table_name: str,
    top_k: int = 3,
) -> list[dict]:
    """Retrieve the most relevant examples for the selected table."""
    if not EXAMPLES_FILE.exists() or top_k <= 0:
        return []

    try:
        examples = json.loads(EXAMPLES_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(examples, list):
        return []

    question_words = tokenize(question)
    expanded_question = expand_words(question_words)
    table = table_name.lower()
    ranked = []

    for example in examples:
        if not isinstance(example, dict):
            continue

        example_question = str(example.get("question", "")).strip()
        example_sql = str(example.get("sql", "")).strip()

        if not example_question or not example_sql:
            continue

        sql_tables = extract_tables(example_sql)

        # Require the example to use the selected table.
        if table not in sql_tables:
            continue

        # Rank mainly by the natural-language question, not SQL boilerplate.
        example_words = tokenize(example_question)
        expanded_example = expand_words(example_words)

        
        if not question_words:
            continue

        direct_overlap = question_words & example_words
        semantic_overlap = expanded_question & expanded_example

        direct_score = len(direct_overlap) / len(question_words)
        semantic_score = len(semantic_overlap) / max(1, len(expanded_question))

        # Prefer examples that share actual words with the question.
        score = 0.75 * direct_score + 0.25 * semantic_score

        # Ignore weak matches.
        if score >= 0.20:
            ranked.append((score, example))


    # Stable sort preserves file order when scores tie.
    ranked.sort(key=lambda item: item[0], reverse=True)

    return [example for _, example in ranked[:top_k]]


def build_rag_context(
    question: str,
    table_name: str,
    schema: str,
) -> str:
    """Build schema and relevant example context for the LLM."""
    examples = retrieve_examples(question, table_name)

    sections = [
        f"Selected table: {table_name}",
        "Database schema:",
        schema,
        (
            "Use the selected table as the main source. "
            "Use other tables only when a relevant JOIN is needed."
        ),
    ]

    if examples:
        sections.append("Relevant example questions and SQL:")
        for number, example in enumerate(examples, start=1):
            sections.append(
                f"Example {number}\n"
                f"Question: {example['question']}\n"
                f"SQL: {example['sql']}"
            )
    else:
        sections.append(
            "No relevant examples were found. "
            "Generate SQL from the supplied schema and user question."
        )

    return "\n\n".join(sections)
