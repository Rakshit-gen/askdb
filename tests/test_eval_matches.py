import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

from run_eval import matches  # noqa: E402


def test_extra_columns_are_fine():
    assert matches([("Standing desk",)], [("Standing desk", 34900)])


def test_repeated_values_must_all_be_present():
    assert not matches([(5, 5)], [(5, 7)])
    assert matches([(5, 5)], [(5, 5, "x")])


def test_row_count_must_match():
    assert not matches([(1,)], [(1,), (2,)])


def test_floats_are_rounded():
    assert matches([(4.21,)], [(4.2123,)])
