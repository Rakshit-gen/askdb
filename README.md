# askdb

Ask questions about a SQLite database in plain English. askdb shows the SQL it
ran next to the result, so you can check it.

```
$ askdb demo.db "Which customer spent the most on delivered orders?" --summary
SELECT
    c.id AS customer_id,
    c.name AS customer_name,
    SUM(oi.quantity * p.price_cents) AS total_spent_cents
FROM customers c
JOIN orders o ON o.customer_id = c.id
JOIN order_items oi ON oi.order_id = o.id
JOIN products p ON p.id = oi.product_id
WHERE o.status = 'delivered'
GROUP BY c.id, c.name
ORDER BY total_spent_cents DESC
LIMIT 1

customer_id  customer_name  total_spent_cents
-----------  -------------  -----------------
         18  Farid Kumar               595587

Farid Kumar spent 595587 cents.
```

## Quickstart

```
uv sync
export GROQ_API_KEY=...
uv run python examples/make_demo_db.py demo.db
uv run askdb demo.db "How many orders were cancelled?"
uv run askdb demo.db                      # print the schema
```

| Flag | What it does |
|---|---|
| `--summary` | Also answer in a sentence or two, based only on the rows returned. |
| `--sql-only` | Print the SQL without the table. |
| `--rows N` | Show at most N rows (default 50). |
| `--timeout S` | Stop a query after S seconds (default 10). |

The model defaults to `openai/gpt-oss-120b` on Groq. Set `ASKDB_MODEL` to use
another one.

## How it works

1. The schema (tables, columns, keys, foreign keys) and three sample rows per
   table go into the prompt. The sample rows show the model how dates and codes
   are stored.
2. The chain `prompt | ChatGroq | StrOutputParser | extract_sql` returns one
   SELECT statement.
3. If sqlite rejects it, the error goes back to the model as a new message and
   it gets up to three tries in total.
4. `--summary` runs a second chain that only sees the question, the SQL and at
   most 30 rows of the result.

## Why it cannot change your data

This does not rely on the prompt. sqlite enforces it:

- The file is opened with `mode=ro`, so sqlite refuses any write to it.
- A `set_authorizer` callback allows only reads, functions, CTEs and a short
  list of schema pragmas. `ATTACH` (which could read other files), temp tables
  and pragma writes are denied.
- `execute()` runs one statement only, so `SELECT 1; DROP TABLE x` fails.
- A progress handler stops any query that runs past the time limit.

Tests cover each of these, and all tests use LangChain's `FakeListChatModel`,
so `uv run pytest` needs no key and no network.
