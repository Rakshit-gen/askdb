from askdb.db import connect_readonly
from askdb.schema import describe, table_names


def test_table_names_skip_sqlite_internals(db_path):
    assert table_names(connect_readonly(db_path)) == ["customers", "orders"]


def test_describe_lists_columns_keys_and_references(db_path):
    text = describe(connect_readonly(db_path))
    assert "TABLE customers (\n  id INTEGER PRIMARY KEY,\n  name TEXT NOT NULL," in text
    assert "customer_id REFERENCES customers(id)" in text


def test_describe_includes_sample_rows(db_path):
    text = describe(connect_readonly(db_path), samples=2)
    assert "-- first 2 rows of orders:\nid | customer_id | total_cents | placed_on\n" in text
    assert "1 | 1 | 2500 | 2026-01-04" in text
    assert "3 | 2 | 1200" not in text


def test_samples_can_be_turned_off(db_path):
    assert "-- first" not in describe(connect_readonly(db_path), samples=0)
