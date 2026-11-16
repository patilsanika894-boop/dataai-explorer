"""Create the sample SQLite database (a small e-commerce shop).

Deterministic seed data so results are reproducible.

Run:  python -m src.build_db
"""
import sqlite3
from pathlib import Path

from src.config import DB_PATH

SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT,
    country TEXT,
    signup_date TEXT
);
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT,
    price REAL NOT NULL
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    order_date TEXT,
    status TEXT
);
CREATE TABLE order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL
);
"""

CUSTOMERS = [
    (1, "Ava Chen", "Sydney", "Australia", "2025-01-12"),
    (2, "Liam Smith", "Melbourne", "Australia", "2025-02-03"),
    (3, "Noah Patel", "Adelaide", "Australia", "2025-02-20"),
    (4, "Mia Williams", "Auckland", "New Zealand", "2025-03-01"),
    (5, "Ethan Brown", "London", "United Kingdom", "2025-03-15"),
    (6, "Sophia Garcia", "Singapore", "Singapore", "2025-04-02"),
    (7, "Oliver Jones", "Perth", "Australia", "2025-04-18"),
    (8, "Isla Wilson", "Brisbane", "Australia", "2025-05-05"),
]

PRODUCTS = [
    (1, "Slim Wallet", "Wallets", 79.0),
    (2, "Card Holder", "Wallets", 59.0),
    (3, "Backpack", "Bags", 199.0),
    (4, "Sling Bag", "Bags", 129.0),
    (5, "Laptop Sleeve", "Bags", 89.0),
    (6, "Phone Case", "Tech", 45.0),
    (7, "Cable Organiser", "Tech", 29.0),
    (8, "Travel Pouch", "Accessories", 39.0),
    (9, "Key Cover", "Accessories", 25.0),
    (10, "Tote Bag", "Bags", 149.0),
]

# (id, customer_id, order_date, status)
ORDERS = [
    (1, 1, "2025-05-10", "completed"),
    (2, 1, "2025-06-01", "shipped"),
    (3, 2, "2025-05-12", "completed"),
    (4, 3, "2025-05-15", "pending"),
    (5, 3, "2025-06-02", "completed"),
    (6, 4, "2025-05-20", "completed"),
    (7, 5, "2025-05-22", "cancelled"),
    (8, 6, "2025-05-25", "shipped"),
    (9, 7, "2025-06-03", "completed"),
    (10, 8, "2025-06-05", "pending"),
    (11, 2, "2025-06-08", "completed"),
    (12, 1, "2025-06-10", "completed"),
]

# (id, order_id, product_id, quantity)
ORDER_ITEMS = [
    (1, 1, 3, 1), (2, 1, 1, 2), (3, 2, 6, 3),
    (4, 3, 10, 1), (5, 3, 2, 1), (6, 4, 4, 1),
    (7, 5, 5, 2), (8, 5, 7, 2), (9, 6, 3, 1),
    (10, 6, 8, 2), (11, 7, 1, 1), (12, 8, 4, 1),
    (13, 8, 9, 3), (14, 9, 10, 2), (15, 9, 6, 1),
    (16, 10, 3, 1), (17, 11, 2, 2), (18, 11, 5, 1),
    (19, 12, 1, 1), (20, 12, 8, 1),
]


def main() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    if Path(DB_PATH).exists():
        Path(DB_PATH).unlink()

    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", CUSTOMERS)
    con.executemany("INSERT INTO products VALUES (?,?,?,?)", PRODUCTS)
    con.executemany("INSERT INTO orders VALUES (?,?,?,?)", ORDERS)
    con.executemany("INSERT INTO order_items VALUES (?,?,?,?)", ORDER_ITEMS)
    con.commit()
    con.close()
    print(
        f"Built {DB_PATH} with "
        f"{len(CUSTOMERS)} customers, {len(PRODUCTS)} products, "
        f"{len(ORDERS)} orders, {len(ORDER_ITEMS)} order items."
    )


if __name__ == "__main__":
    main()
