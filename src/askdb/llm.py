"""Turn a question into SQL with a chat model through LangChain."""

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda

from askdb.sqltext import extract_sql

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
    prompt = ChatPromptTemplate.from_messages([("system", SQL_SYSTEM), ("human", SQL_HUMAN)])
    return prompt | model | StrOutputParser() | RunnableLambda(extract_sql)
