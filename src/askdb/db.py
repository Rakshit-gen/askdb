"""Open a SQLite database so that nothing run through it can change data."""

import sqlite3
from pathlib import Path


def connect_readonly(path: str | Path) -> sqlite3.Connection:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"no database at {path}")
    # mode=ro makes sqlite itself refuse writes to the file.
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    return conn
