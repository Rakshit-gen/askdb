"""Build a small shop database to try askdb on.

    uv run python examples/make_demo_db.py demo.db

The data is random but seeded, so every run makes the same file.
"""

import random
import sqlite3
import sys
from datetime import date, timedelta

SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    signed_up TEXT NOT NULL
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price_cents INTEGER NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    placed_on TEXT NOT NULL,
    status TEXT NOT NULL
);
CREATE TABLE order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL
);
"""

FIRST = ["Asha", "Ben", "Chloe", "Dev", "Emma", "Farid", "Grace", "Hiro", "Ines", "Jonas"]
LAST = ["Rao", "Smith", "Martin", "Kumar", "Garcia", "Ito", "Silva", "Novak"]
COUNTRIES = ["IN", "US", "FR", "DE", "BR", "JP"]
PRODUCTS = [
    ("Desk lamp", "home", 2499),
    ("Standing desk", "home", 34900),
    ("Office chair", "home", 18900),
    ("Notebook", "stationery", 499),
    ("Gel pens (10)", "stationery", 899),
    ("Mechanical keyboard", "electronics", 8900),
    ("USB-C hub", "electronics", 3900),
    ("Monitor 27in", "electronics", 27900),
    ("Webcam", "electronics", 5900),
    ("Coffee mug", "kitchen", 1299),
    ("Kettle", "kitchen", 3499),
    ("Water bottle", "kitchen", 1999),
]
STATUSES = ["delivered"] * 8 + ["shipped", "cancelled"]


def build(path: str) -> None:
    rng = random.Random(42)
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    start = date(2025, 1, 1)
    for cid in range(1, 61):
        name = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        signed = start + timedelta(days=rng.randrange(365))
        conn.execute(
            "INSERT INTO customers VALUES (?, ?, ?, ?)",
            (cid, name, rng.choice(COUNTRIES), signed.isoformat()),
        )
    conn.executemany(
        "INSERT INTO products (name, category, price_cents) VALUES (?, ?, ?)", PRODUCTS
    )
    for oid in range(1, 401):
        placed = start + timedelta(days=rng.randrange(600))
        conn.execute(
            "INSERT INTO orders VALUES (?, ?, ?, ?)",
            (oid, rng.randrange(1, 61), placed.isoformat(), rng.choice(STATUSES)),
        )
        for pid in rng.sample(range(1, len(PRODUCTS) + 1), rng.randrange(1, 4)):
            conn.execute(
                "INSERT INTO order_items VALUES (?, ?, ?)", (oid, pid, rng.randrange(1, 4))
            )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "demo.db")
