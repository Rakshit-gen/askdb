"""Print query results as a plain text table."""

from askdb.db import Result


def format_table(result: Result, max_width: int = 40) -> str:
    if not result.columns:
        return "(no columns)"

    def cell(v) -> str:
        s = "NULL" if v is None else str(v).replace("\n", " ")
        return s if len(s) <= max_width else s[: max_width - 3] + "..."

    body = [[cell(v) for v in row] for row in result.rows]
    widths = [max([len(c)] + [len(r[i]) for r in body]) for i, c in enumerate(result.columns)]
    # Right-align numbers so columns of totals line up.
    numeric = [all(isinstance(r[i], int | float) for r in result.rows) for i in range(len(widths))]

    def line(values):
        parts = [
            v.rjust(w) if num else v.ljust(w)
            for v, w, num in zip(values, widths, numeric, strict=True)
        ]
        return "  ".join(parts).rstrip()

    out = [line(result.columns), line(["-" * w for w in widths])]
    out += [line(r) for r in body]
    if not result.rows:
        out.append("(no rows)")
    if result.truncated:
        out.append(f"(showing first {len(result.rows)} rows)")
    return "\n".join(out)
