from langchain_core.language_models.fake_chat_models import FakeListChatModel

from askdb.llm import build_sql_chain


def test_sql_chain_returns_clean_sql():
    model = FakeListChatModel(responses=["```sql\nSELECT count(*) AS n FROM customers;\n```"])
    sql = build_sql_chain(model).invoke({"schema": "TABLE customers (id)", "question": "how many?"})
    assert sql == "SELECT count(*) AS n FROM customers"
