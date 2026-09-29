from askdb.db import Result
from askdb.table import format_table


def test_numbers_right_aligned_text_left_aligned():
    out = format_table(Result(["name", "total"], [("Asha", 6500), ("Ben", 1200)], False))
    assert out == "name  total\n----  -----\nAsha   6500\nBen    1200"


def test_nulls_long_values_and_truncation_note():
    out = format_table(Result(["note"], [(None,), ("x" * 50,)], True), max_width=10)
    assert out.splitlines() == [
        "note",
        "----------",
        "NULL",
        "xxxxxxx...",
        "(showing first 2 rows)",
    ]


def test_empty_result():
    assert format_table(Result(["id"], [], False)) == "id\n--\n(no rows)"
