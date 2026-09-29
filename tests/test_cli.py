import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from askdb.cli import main


def fake(*replies):
    return FakeListChatModel(responses=list(replies))


def test_no_question_prints_the_schema(db_path, capsys):
    assert main([str(db_path)]) == 0
    out = capsys.readouterr().out
    assert out.startswith("TABLE customers (")
    assert "-- first" not in out


def test_question_prints_sql_and_table(db_path, capsys):
    model = fake("```sql\nSELECT name, country FROM customers ORDER BY name\n```")
    assert main([str(db_path), "list customers"], model=model) == 0
    out = capsys.readouterr().out
    assert out.startswith("SELECT name, country FROM customers ORDER BY name\n\n")
    assert "Chloe  FR" in out


def test_summary_is_printed_after_the_table(db_path, capsys):
    model = fake("SELECT count(*) AS n FROM orders", "There are 3 orders.")
    assert main([str(db_path), "how many orders", "--summary"], model=model) == 0
    assert capsys.readouterr().out.rstrip().endswith("There are 3 orders.")


def test_giving_up_exits_2_and_shows_last_sql(db_path, capsys):
    model = fake(*["SELECT bad FROM orders"] * 3)
    assert main([str(db_path), "?"], model=model) == 2
    err = capsys.readouterr().err
    assert "no such column: bad" in err
    assert err.rstrip().endswith("SELECT bad FROM orders")


def test_missing_db_exits_1(tmp_path, capsys):
    assert main([str(tmp_path / "x.db"), "?"]) == 1
    assert "no database at" in capsys.readouterr().err


def test_missing_api_key_is_a_clear_error(db_path, capsys, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert main([str(db_path), "how many orders?"]) == 1
    assert "GROQ_API_KEY is not set" in capsys.readouterr().err


@pytest.mark.parametrize("flag", [["--rows", "0"], ["--rows", "-5"], ["--timeout", "0"]])
def test_non_positive_limits_are_rejected(db_path, flag, capsys):
    with pytest.raises(SystemExit) as info:
        main([str(db_path), "?", *flag], model=fake("SELECT 1"))
    assert info.value.code == 2
    assert "must be greater than 0" in capsys.readouterr().err


def test_non_database_file_exits_1(tmp_path, capsys):
    notes = tmp_path / "notes.txt"
    notes.write_text("just some text, long enough to not look like an empty database file\n" * 20)
    assert main([str(notes)]) == 1
    assert "is not a SQLite database" in capsys.readouterr().err
