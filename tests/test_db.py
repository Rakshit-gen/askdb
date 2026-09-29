import sqlite3

import pytest

from askdb.db import connect_readonly


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
