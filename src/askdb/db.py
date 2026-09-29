"""Open a SQLite database so that nothing run through it can change data."""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

ALLOWED_ACTIONS = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
# SQLITE_RECURSIVE was added in sqlite 3.8.3; older builds just don't report it.
if hasattr(sqlite3, "SQLITE_RECURSIVE"):
    ALLOWED_ACTIONS.add(sqlite3.SQLITE_RECURSIVE)

# Pragmas that only describe the schema. Their argument is a table or index name,
# never a setting, so they are safe with any argument.
ALLOWED_PRAGMAS = {"table_info", "table_xinfo", "foreign_key_list", "index_list", "index_info"}


def _authorize(action, arg1, arg2, db_name, trigger):
    if action in ALLOWED_ACTIONS:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_PRAGMA and arg1 in ALLOWED_PRAGMAS:
        return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


class NotADatabaseError(ValueError):
    pass


def connect_readonly(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no database at {path}")
    # mode=ro makes sqlite itself refuse writes to the file.
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    # The authorizer is a second wall: it also blocks ATTACH (which could read other
    # files), temp tables and pragmas that change settings. It runs inside sqlite
    # for every statement, so it does not depend on parsing the SQL ourselves.
    conn.set_authorizer(_authorize)
    try:
        # sqlite opens any file lazily; the first read is what fails on a non-database.
        conn.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except sqlite3.DatabaseError as e:
        conn.close()
        raise NotADatabaseError(f"{path} is not a SQLite database ({e})") from e
    return conn


@dataclass
class Result:
    columns: list[str]
    rows: list[tuple]
    truncated: bool


class QueryTimeout(RuntimeError):
    pass


def run_query(
    conn: sqlite3.Connection, sql: str, max_rows: int = 200, timeout_s: float = 10.0
) -> Result:
    # A model can write a cross join that runs for minutes. sqlite calls the progress
    # handler every N VM steps, and a non-zero return aborts the statement.
    deadline = time.monotonic() + timeout_s
    conn.set_progress_handler(lambda: time.monotonic() > deadline, 10_000)
    try:
        # execute() refuses more than one statement, so "SELECT 1; DROP ..." never runs.
        cur = conn.execute(sql)
        columns = [d[0] for d in cur.description or []]
        rows = cur.fetchmany(max_rows + 1)
    except sqlite3.OperationalError as e:
        if "interrupted" in str(e):
            raise QueryTimeout(f"query took longer than {timeout_s:g}s") from e
        raise
    finally:
        conn.set_progress_handler(None, 0)
    return Result(columns, rows[:max_rows], truncated=len(rows) > max_rows)
