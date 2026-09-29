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


def describe(conn: sqlite3.Connection) -> str:
    return "\n\n".join(describe_table(conn, t) for t in table_names(conn))
