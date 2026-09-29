"""Describe a database schema in a compact form the model can read."""

import sqlite3


def quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return [r[0] for r in rows]


def describe_table(conn: sqlite3.Connection, table: str) -> str:
    cols = []
    for _, name, col_type, notnull, _, pk in conn.execute(f"PRAGMA table_info({quote(table)})"):
        parts = [name, col_type or "ANY"]
        if pk:
            parts.append("PRIMARY KEY")
        if notnull:
            parts.append("NOT NULL")
        cols.append(" ".join(parts))
    for row in conn.execute(f"PRAGMA foreign_key_list({quote(table)})"):
        ref_table, from_col, to_col = row[2], row[3], row[4]
        cols.append(f"{from_col} REFERENCES {ref_table}({to_col})")
    return f"TABLE {table} (\n  " + ",\n  ".join(cols) + "\n)"


def sample_rows(conn: sqlite3.Connection, table: str, n: int) -> str:
    cur = conn.execute(f"SELECT * FROM {quote(table)} LIMIT {int(n)}")
    header = [d[0] for d in cur.description]
    lines = [" | ".join(header)]
    for row in cur:
        # Long text values would crowd out the schema, so cut them short.
        lines.append(" | ".join(str(v)[:40] for v in row))
    return "\n".join(lines)


def describe(conn: sqlite3.Connection, samples: int = 3) -> str:
    """Schema plus a few rows per table, so the model sees value formats like dates."""
    blocks = []
    for t in table_names(conn):
        block = describe_table(conn, t)
        if samples:
            block += f"\n-- first {samples} rows of {t}:\n" + sample_rows(conn, t, samples)
        blocks.append(block)
    return "\n\n".join(blocks)
