import sqlite3

import pytest

SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id),
    total_cents INTEGER NOT NULL,
    placed_on TEXT NOT NULL
);
INSERT INTO customers VALUES (1, 'Asha', 'IN'), (2, 'Ben', 'US'), (3, 'Chloe', 'FR');
INSERT INTO orders VALUES
    (1, 1, 2500, '2026-01-04'),
    (2, 1, 4000, '2026-02-11'),
    (3, 2, 1200, '2026-02-12');
"""


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "shop.db"
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    return path
