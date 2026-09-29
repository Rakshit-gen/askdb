import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from askdb.db import connect_readonly, run_query
from askdb.llm import GaveUp, ask, build_sql_chain


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
