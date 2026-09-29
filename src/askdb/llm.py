"""Turn a question into SQL with a chat model through LangChain."""

import os
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


SUMMARY_SYSTEM = """You answer a question in one or two plain sentences using only the
query result given. Say the numbers. If the result is empty, say nothing matched.
If the result was cut off, say the answer covers only the rows shown."""

SUMMARY_HUMAN = """Question: {question}

SQL: {sql}

Result ({note}):
{table}"""


def summarize(question: str, answer: Answer, model: BaseChatModel, max_rows: int = 30) -> str:
    rows = answer.result.rows[:max_rows]
    table = "\n".join([" | ".join(answer.result.columns)] + [" | ".join(map(str, r)) for r in rows])
    note = (
        "cut off" if answer.result.truncated or len(answer.result.rows) > max_rows else "all rows"
    )
    prompt = ChatPromptTemplate.from_messages(
        [("system", SUMMARY_SYSTEM), ("human", SUMMARY_HUMAN)]
    )
    chain = prompt | model | StrOutputParser()
    return chain.invoke(
        {"question": question, "sql": answer.sql, "note": note, "table": table}
    ).strip()


# Checked against Groq's model list on 2026-09-29. Override with ASKDB_MODEL.
DEFAULT_MODEL = "openai/gpt-oss-120b"


def groq_model() -> BaseChatModel:
    from langchain_groq import ChatGroq

    # gpt-oss reasons before answering, and that counts against max_tokens. Low effort
    # plus a roomy cap keeps the SQL from being cut off.
    return ChatGroq(
        model=os.environ.get("ASKDB_MODEL", DEFAULT_MODEL),
        temperature=0,
        reasoning_effort="low",
        max_tokens=4096,
    )
