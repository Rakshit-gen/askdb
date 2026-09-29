import pytest

from askdb.sqltext import NoSQLError, extract_sql


def test_plain_sql():
    assert extract_sql("SELECT 1;") == "SELECT 1"


def test_fenced_sql_ignores_the_prose_around_it():
    reply = "Here you go:\n```sql\nSELECT name\nFROM customers;\n```\nThis lists names."
    assert extract_sql(reply) == "SELECT name\nFROM customers"


def test_fence_without_language():
    assert extract_sql("```\nSELECT 2\n```") == "SELECT 2"


def test_empty_reply_is_an_error():
    with pytest.raises(NoSQLError):
        extract_sql("```sql\n;\n```")
