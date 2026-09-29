"""Open a SQLite database so that nothing run through it can change data."""

import sqlite3
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
    return conn
