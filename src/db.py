
"""Read-only database access with CSV import support."""

import re
import sqlite3

import pandas as pd

from src.config import DB_PATH


# SQL statements that must never modify the database.
_FORBIDDEN = {
    "insert", "update", "delete", "drop", "alter", "create",
    "replace", "truncate", "attach", "detach", "pragma", "vacuum",
}


def get_connection() -> sqlite3.Connection:
    """Create a connection to the SQLite database."""
    return sqlite3.connect(DB_PATH)


def get_schema() -> str:
    """Return CREATE TABLE statements for all user tables."""
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND sql IS NOT NULL
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
    finally:
        con.close()

    return ";\n\n".join(row[0] for row in rows) + ";" if rows else ""


def get_table_names() -> list[str]:
    """Return available user tables in SQLite."""
    con = get_connection()
    try:
        rows = con.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()
        return [row[0] for row in rows]
    finally:
        con.close()


def is_safe_select(sql: str) -> bool:
    """Allow a single SELECT or WITH query, rejecting obvious unsafe SQL."""
    if not isinstance(sql, str) or not sql.strip():
        return False

    stripped = sql.strip()

    # Allow one optional trailing semicolon, but no multiple statements.
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()

    if not stripped or ";" in stripped:
        return False

    # Only SELECT and WITH queries are permitted.
    if not re.match(r"^(SELECT|WITH)\b", stripped, re.IGNORECASE):
        return False

    # Reject forbidden SQL keywords, including those inside CTEs.
    # This is an initial check; SQLite's authorizer below adds protection.
    tokens = set(
        re.findall(r"[A-Za-z_][A-Za-z_0-9]*", stripped.lower())
    )

    if tokens & _FORBIDDEN:
        return False

    return True


def _read_only_authorizer(action, arg1, arg2, database, source):
    """Prevent database changes and dangerous operations during queries."""
    forbidden_names = (
        "SQLITE_INSERT",
        "SQLITE_UPDATE",
        "SQLITE_DELETE",
        "SQLITE_CREATE_INDEX",
        "SQLITE_CREATE_TABLE",
        "SQLITE_CREATE_TEMP_INDEX",
        "SQLITE_CREATE_TEMP_TABLE",
        "SQLITE_CREATE_TEMP_TRIGGER",
        "SQLITE_CREATE_TEMP_VIEW",
        "SQLITE_CREATE_TRIGGER",
        "SQLITE_CREATE_VIEW",
        "SQLITE_CREATE_VTABLE",
        "SQLITE_DROP_INDEX",
        "SQLITE_DROP_TABLE",
        "SQLITE_DROP_TEMP_INDEX",
        "SQLITE_DROP_TEMP_TABLE",
        "SQLITE_DROP_TEMP_TRIGGER",
        "SQLITE_DROP_TEMP_VIEW",
        "SQLITE_DROP_TRIGGER",
        "SQLITE_DROP_VIEW",
        "SQLITE_DROP_VTABLE",
        "SQLITE_ALTER_TABLE",
        "SQLITE_ATTACH",
        "SQLITE_DETACH",
        "SQLITE_PRAGMA",
        "SQLITE_REINDEX",
        "SQLITE_ANALYZE",
    )

    forbidden_actions = {
        getattr(sqlite3, name)
        for name in forbidden_names
        if hasattr(sqlite3, name)
    }

    if action in forbidden_actions:
        return sqlite3.SQLITE_DENY

    return sqlite3.SQLITE_OK


def run_select(sql: str):
    """Execute a read-only query and return (column_names, rows)."""
    if not is_safe_select(sql):
        raise ValueError(
            "Only a single read-only SELECT or WITH query is allowed."
        )

    con = get_connection()
    try:
        # SQLite-level protection against database changes.
        con.execute("PRAGMA query_only = ON")
        con.set_authorizer(_read_only_authorizer)

        cursor = con.execute(sql)

        if cursor.description is None:
            raise ValueError("The SQL query did not return a result set.")

        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        return columns, rows
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Could not execute the SQL query: {exc}") from exc
    finally:
        con.close()


def import_csv_to_table(uploaded_file, table_name: str) -> str:
    """Import a CSV into a new table without overwriting existing tables."""
    if not isinstance(table_name, str):
        raise ValueError("Please provide a valid table name.")

    table_name = table_name.strip()

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise ValueError(
            "Invalid table name. Use letters, numbers, and underscores; "
            "the name must not start with a number."
        )

    try:
        df = pd.read_csv(uploaded_file)
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(
            f"Could not read the CSV file. Check its format and encoding: {exc}"
        ) from exc

    if len(df.columns) == 0:
        raise ValueError("The CSV file has no columns.")

    if df.empty:
        raise ValueError("The CSV file contains no data rows.")

    if len(df.columns) > 100:
        raise ValueError("The CSV has too many columns. Maximum: 100.")

    cleaned_columns = []

    for column in df.columns:
        name = re.sub(r"\W+", "_", str(column).strip()).strip("_")

        if not name:
            name = "column"

        if name[0].isdigit():
            name = "col_" + name

        cleaned_columns.append(name)

    # SQLite identifiers are case-insensitive in this context.
    normalized_columns = [name.lower() for name in cleaned_columns]

    if len(set(normalized_columns)) != len(normalized_columns):
        raise ValueError(
            "Some CSV column names become duplicates after cleaning. "
            "Rename the columns in your CSV and try again."
        )

    df.columns = cleaned_columns

    con = get_connection()
    try:
        existing = con.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND lower(name) = lower(?)
            """,
            (table_name,),
        ).fetchone()

        if existing:
            raise ValueError(
                f"Table '{table_name}' already exists. "
                "Choose a different table name."
            )

        df.to_sql(table_name, con, index=False, if_exists="fail")
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Could not import the CSV into SQLite: {exc}") from exc
    finally:
        con.close()

    return table_name


def get_table_schema(table_name: str) -> str:
    """Return the CREATE TABLE statement for the selected table."""
    if not isinstance(table_name, str) or not re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_]*", table_name
    ):
        raise ValueError("Invalid table name.")

    con = get_connection()
    try:
        row = con.execute(
            """
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (table_name,),
        ).fetchone()

        if row is None:
            raise ValueError(f"Table '{table_name}' does not exist.")

        return row[0]
    finally:
        con.close()
