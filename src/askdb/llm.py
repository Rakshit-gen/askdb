"""Turn a question into SQL with a chat model through LangChain."""

import sqlite3
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import Runnable, RunnableLambda

from askdb.db import Result, run_query
from askdb.schema import describe
from askdb.sqltext import NoSQLError, extract_sql

SQL_SYSTEM = """You write one SQLite SELECT statement that answers the user's question.

Rules:
- Use only the tables and columns in the schema below.
- Return a single statement in a ```sql block and nothing else.
- Read only. Never write INSERT, UPDATE, DELETE, CREATE, DROP, ATTACH or PRAGMA.
- Give columns readable names with AS when you compute them.
- If the question asks for "top" or "most" without a number, return 10 rows.

Schema:
{schema}"""

SQL_HUMAN = "{question}"


def build_sql_chain(model: BaseChatModel) -> Runnable:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SQL_SYSTEM),
            ("human", SQL_HUMAN),
            MessagesPlaceholder("attempts", optional=True),
        ]
    )
    return prompt | model | StrOutputParser() | RunnableLambda(extract_sql)


@dataclass
class Answer:
    sql: str
    result: Result
    tries: int


class GaveUp(RuntimeError):
    def __init__(self, sql: str, error: str, tries: int):
        super().__init__(f"no working query after {tries} tries. Last error: {error}")
        self.sql = sql
        self.error = error


def ask(
    conn: sqlite3.Connection, question: str, model: BaseChatModel, max_tries: int = 3
) -> Answer:
    """Ask for SQL, run it, and on a sqlite error show the model the error and ask again."""
    chain = build_sql_chain(model)
    inputs = {"schema": describe(conn), "question": question, "attempts": []}
    sql = ""
    for tries in range(1, max_tries + 1):
        try:
            sql = chain.invoke(inputs)
            return Answer(sql, run_query(conn, sql), tries)
        except (sqlite3.Error, NoSQLError) as e:
            error = str(e)
            inputs["attempts"] += [
                AIMessage(f"```sql\n{sql}\n```"),
                HumanMessage(f"That query failed with: {error}\nReturn a fixed query."),
            ]
    raise GaveUp(sql, error, max_tries)
