"""Score askdb against the questions in eval_questions.json on the demo database.

    uv run python examples/run_eval.py

Needs GROQ_API_KEY. A question counts as correct when the model's result has the
same number of rows as the gold query and every gold row's values appear in one
of the model's rows. Extra columns are fine. Floats are rounded to 2 places.
"""

import json
import sqlite3
import tempfile
import time
from pathlib import Path

from make_demo_db import build

from askdb.db import connect_readonly
from askdb.llm import GaveUp, ask, groq_model

HERE = Path(__file__).parent


def norm(v):
    return round(v, 2) if isinstance(v, float) else v


def matches(gold: list[tuple], got: list[tuple]) -> bool:
    if len(gold) != len(got):
        return False
    remaining = [set(map(norm, r)) for r in got]
    for row in gold:
        want = set(map(norm, row))
        hit = next((i for i, r in enumerate(remaining) if want <= r), None)
        if hit is None:
            return False
        remaining.pop(hit)
    return True


def main() -> int:
    questions = json.loads((HERE / "eval_questions.json").read_text())
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "demo.db"
        build(str(path))
        conn = connect_readonly(path)
        model = groq_model()
        correct = 0
        started = time.monotonic()
        for item in questions:
            gold = sqlite3.connect(path).execute(item["gold"]).fetchall()
            try:
                answer = ask(conn, item["q"], model)
                ok = matches(gold, answer.result.rows)
                tries = answer.tries
            except GaveUp:
                ok, tries = False, "gave up"
            correct += ok
            print(f"{'PASS' if ok else 'FAIL'}  tries={tries}  {item['q']}")
        elapsed = time.monotonic() - started
    print(f"\n{correct}/{len(questions)} correct in {elapsed:.1f}s")
    return 0 if correct == len(questions) else 1


if __name__ == "__main__":
    raise SystemExit(main())
