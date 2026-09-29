import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from askdb.db import connect_readonly, run_query
from askdb.llm import Answer, GaveUp, ask, build_sql_chain, summarize


def test_sql_chain_returns_clean_sql():
    model = FakeListChatModel(responses=["```sql\nSELECT count(*) AS n FROM customers;\n```"])
    sql = build_sql_chain(model).invoke({"schema": "TABLE customers (id)", "question": "how many?"})
    assert sql == "SELECT count(*) AS n FROM customers"


def fenced(sql):
    return f"```sql\n{sql}\n```"


class Recorder(FakeListChatModel):
    """Fake model that keeps the messages it was sent."""

    calls: list = []

    def _call(self, messages, *args, **kwargs):
        self.calls.append(messages)
        return super()._call(messages, *args, **kwargs)


def test_ask_runs_the_query(db_path):
    model = FakeListChatModel(responses=[fenced("SELECT count(*) FROM orders")])
    answer = ask(connect_readonly(db_path), "how many orders?", model)
    assert answer.result.rows == [(3,)]
    assert answer.tries == 1


def test_ask_sends_the_error_back_and_retries(db_path):
    model = Recorder(
        calls=[],
        responses=[fenced("SELECT count(*) FROM order"), fenced("SELECT count(*) FROM orders")],
    )
    answer = ask(connect_readonly(db_path), "how many orders?", model)
    assert answer.tries == 2
    assert answer.result.rows == [(3,)]
    retry_messages = model.calls[1]
    assert "SELECT count(*) FROM order\n" in retry_messages[-2].content
    assert "failed with" in retry_messages[-1].content


def test_ask_gives_up_after_max_tries(db_path):
    model = FakeListChatModel(responses=[fenced("SELECT nope FROM orders")] * 3)
    with pytest.raises(GaveUp) as info:
        ask(connect_readonly(db_path), "?", model, max_tries=3)
    assert "no such column: nope" in str(info.value)


def test_ask_does_not_retry_writes_into_success(db_path):
    model = FakeListChatModel(responses=[fenced("DELETE FROM orders")] * 2)
    with pytest.raises(GaveUp):
        ask(connect_readonly(db_path), "delete everything", model, max_tries=2)
    assert run_query(connect_readonly(db_path), "SELECT count(*) FROM orders").rows == [(3,)]


def test_summarize_passes_the_result_to_the_model(db_path):
    conn = connect_readonly(db_path)
    answer = Answer("SELECT name FROM customers", run_query(conn, "SELECT name FROM customers"), 1)
    model = Recorder(calls=[], responses=["There are three customers: Asha, Ben and Chloe."])
    text = summarize("who are the customers?", answer, model)
    assert text == "There are three customers: Asha, Ben and Chloe."
    sent = model.calls[0][-1].content
    assert "Result (all rows):\nname\nAsha\nBen\nChloe" in sent


def test_summarize_flags_cut_off_results(db_path):
    conn = connect_readonly(db_path)
    result = run_query(conn, "SELECT id FROM customers", max_rows=1)
    model = Recorder(calls=[], responses=["ok"])
    summarize("ids?", Answer("SELECT id FROM customers", result, 1), model)
    assert "Result (cut off)" in model.calls[0][-1].content


def test_retry_history_shows_what_the_model_actually_said(db_path):
    model = Recorder(
        calls=[],
        responses=[
            fenced("SELECT nope FROM orders"),
            "Sorry, I cannot answer that.",
            fenced("SELECT count(*) FROM orders"),
        ],
    )
    answer = ask(connect_readonly(db_path), "how many orders?", model)
    assert answer.tries == 3
    third_call = model.calls[2]
    assert third_call[-2].content == "Sorry, I cannot answer that."
    assert "SELECT nope" not in third_call[-2].content


def test_giving_up_reports_the_last_reply_not_an_older_query(db_path):
    model = FakeListChatModel(responses=[fenced("SELECT nope FROM orders"), "I am not sure."])
    with pytest.raises(GaveUp) as info:
        ask(connect_readonly(db_path), "?", model, max_tries=2)
    assert info.value.sql == "I am not sure."
    assert "nope" not in info.value.sql
