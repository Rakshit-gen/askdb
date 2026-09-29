"""Pull the SQL statement out of a model reply."""

import re

FENCE_RE = re.compile(r"```(?:sql|sqlite)?\s*\n(.*?)```", re.DOTALL | re.IGNORECASE)


class NoSQLError(ValueError):
    pass


def extract_sql(reply: str) -> str:
    """Return the SQL in a reply, from a fenced block if there is one."""
    m = FENCE_RE.search(reply)
    sql = (m.group(1) if m else reply).strip()
    sql = sql.rstrip(";").strip()
    if not sql:
        raise NoSQLError("the model reply had no SQL in it")
    return sql
