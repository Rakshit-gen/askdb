import sqlite3

import pytest

from askdb.db import connect_readonly, run_query


def test_reads_work(db_path):
    conn = connect_readonly(db_path)
    assert conn.execute("SELECT count(*) FROM customers").fetchone() == (3,)


def test_writes_are_refused(db_path):
    conn = connect_readonly(db_path)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM customers")


def test_missing_file_is_an_error_not_a_new_empty_db(tmp_path):
    with pytest.raises(FileNotFoundError):
        connect_readonly(tmp_path / "nope.db")
    assert not (tmp_path / "nope.db").exists()


@pytest.mark.parametrize(
    "sql",
    [
        "ATTACH DATABASE ':memory:' AS other",
        "CREATE TEMP TABLE t (x)",
        "PRAGMA query_only = 0",
        "PRAGMA journal_mode = WAL",
    ],
)
def test_authorizer_blocks_non_reads(db_path, sql):
    conn = connect_readonly(db_path)
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute(sql)


def test_joins_ctes_and_schema_pragmas_are_allowed(db_path):
    conn = connect_readonly(db_path)
    rows = conn.execute(
        """
        WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 3)
        SELECT c.name, sum(o.total_cents) FROM customers c
        JOIN orders o ON o.customer_id = c.id GROUP BY c.name ORDER BY c.name
        """
    ).fetchall()
    assert rows == [("Asha", 6500), ("Ben", 1200)]
    assert len(conn.execute("PRAGMA table_info(orders)").fetchall()) == 4


def test_run_query_returns_columns_and_rows(db_path):
    result = run_query(connect_readonly(db_path), "SELECT id, name FROM customers ORDER BY id")
    assert result.columns == ["id", "name"]
    assert result.rows == [(1, "Asha"), (2, "Ben"), (3, "Chloe")]
    assert result.truncated is False


def test_run_query_caps_rows(db_path):
    result = run_query(connect_readonly(db_path), "SELECT id FROM customers", max_rows=2)
    assert len(result.rows) == 2
    assert result.truncated is True


def test_second_statement_never_runs(db_path):
    with pytest.raises(sqlite3.ProgrammingError):
        run_query(connect_readonly(db_path), "SELECT 1; DELETE FROM customers")
