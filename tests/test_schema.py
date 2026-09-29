from askdb.db import connect_readonly
from askdb.schema import describe, table_names


def test_table_names_skip_sqlite_internals(db_path):
    assert table_names(connect_readonly(db_path)) == ["customers", "orders"]


def test_describe_lists_columns_keys_and_references(db_path):
    text = describe(connect_readonly(db_path))
    assert "TABLE customers (\n  id INTEGER PRIMARY KEY,\n  name TEXT NOT NULL," in text
    assert "customer_id REFERENCES customers(id)" in text
