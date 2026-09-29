"""Command line entry point."""

import argparse
import sys

from askdb.db import QueryTimeout, connect_readonly
from askdb.table import format_table


def main(argv: list[str] | None = None, model=None) -> int:
    parser = argparse.ArgumentParser(
        prog="askdb", description="Ask questions about a SQLite database in plain English."
    )
    parser.add_argument("db", help="path to a SQLite file")
    parser.add_argument("question", nargs="?", help="question to ask; omit to print the schema")
    parser.add_argument("--rows", type=int, default=50, help="max rows to show (default 50)")
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds per query")
    parser.add_argument("--summary", action="store_true", help="also answer in a sentence")
    parser.add_argument("--sql-only", action="store_true", help="print the SQL without the table")
    args = parser.parse_args(argv)

    from askdb.llm import GaveUp, ask, summarize
    from askdb.schema import describe

    try:
        conn = connect_readonly(args.db)
    except FileNotFoundError as e:
        print(f"askdb: {e}", file=sys.stderr)
        return 1

    if not args.question:
        print(describe(conn, samples=0))
        return 0

    if model is None:
        from askdb.llm import groq_model

        model = groq_model()

    try:
        answer = ask(conn, args.question, model, max_rows=args.rows, timeout_s=args.timeout)
    except GaveUp as e:
        print(f"askdb: {e}\n\nlast SQL tried:\n{e.sql}", file=sys.stderr)
        return 2
    except QueryTimeout as e:
        print(f"askdb: {e}", file=sys.stderr)
        return 2

    print(answer.sql, end="\n\n")
    if args.sql_only:
        return 0
    print(format_table(answer.result))
    if args.summary:
        print()
        print(summarize(args.question, answer, model))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
