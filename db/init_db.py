"""Demo database initialization and realistic sample data seeding."""

import sqlite3
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DEMO_DB_PATH


DEMO_QUESTIONS: List[Dict[str, str]] = [
    {
        "question": "How many products are there?",
        "sql": "SELECT COUNT(*) AS total_products FROM products;",
        "description": "Counts total products in the catalog.",
    },
    {
        "question": "Which products have stock below 10?",
        "sql": "SELECT product_name, category, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC;",
        "description": "Lists all products running low on stock.",
    },
    {
        "question": "Which product has the lowest stock?",
        "sql": "SELECT product_name, stock_quantity, category FROM products ORDER BY stock_quantity ASC LIMIT 1;",
        "description": "Finds the single product with minimum inventory.",
    },
    {
        "question": "Show the five most expensive products.",
        "sql": "SELECT product_name, category, unit_price FROM products ORDER BY unit_price DESC LIMIT 5;",
        "description": "Retrieves the top 5 highest priced products.",
    },
    {
        "question": "What is the total sales amount?",
        "sql": "SELECT ROUND(SUM(total_amount), 2) AS total_sales_amount FROM sales;",
        "description": "Calculates overall gross revenue across all transactions.",
    },
    {
        "question": "Which products sold the highest quantity?",
        "sql": """SELECT p.product_name, p.category, SUM(s.quantity) AS total_sold
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_sold DESC
LIMIT 5;""",
        "description": "Ranks top selling products by units sold.",
    },
    {
        "question": "Which city has the most customers?",
        "sql": "SELECT city, COUNT(*) AS customer_count FROM customers GROUP BY city ORDER BY customer_count DESC LIMIT 1;",
        "description": "Identifies the city with the largest customer base.",
    },
    {
        "question": "Show monthly sales totals.",
        "sql": "SELECT strftime('%Y-%m', sale_date) AS month, ROUND(SUM(total_amount), 2) AS monthly_sales FROM sales GROUP BY month ORDER BY month ASC;",
        "description": "Aggregates revenue by calendar month.",
    },
]


def create_schema(conn: sqlite3.Connection) -> None:
    """Create demo schema tables with foreign key constraints."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_name TEXT NOT NULL,
        category TEXT NOT NULL,
        unit_price REAL NOT NULL,
        stock_quantity INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        city TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS sales (
        sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        customer_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL,
        sale_date TEXT NOT NULL,
        total_amount REAL NOT NULL,
        FOREIGN KEY (product_id) REFERENCES products(product_id),
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
    );
    """)
    conn.commit()


def seed_data(conn: sqlite3.Connection) -> None:
    """Seed realistic fictional data into demo tables."""
    cursor = conn.cursor()

    products_data = [
        ("Quantum Wireless Headphones", "Audio", 149.99, 45),
        ("UltraHD 4K Curved Monitor", "Electronics", 399.50, 12),
        ("Ergonomic Mechanical Keyboard", "Accessories", 89.00, 28),
        ("Pro Wireless Precision Mouse", "Accessories", 49.99, 5),     # low stock
        ("Noise Cancelling Earbuds", "Audio", 79.99, 60),
        ("Smart Fitness Tracker Band", "Wearables", 129.00, 8),      # low stock
        ("USB-C Multi-Port Hub", "Accessories", 34.50, 75),
        ("Portable Bluetooth Speaker", "Audio", 59.99, 3),            # lowest stock
        ("Gaming Laptop 16-inch", "Electronics", 1299.00, 15),
        ("Office High-Back Mesh Chair", "Office", 249.00, 20),
        ("Aluminum Laptop Stand", "Accessories", 39.99, 50),
        ("Dual-Band WiFi 6 Router", "Electronics", 119.99, 18),
    ]

    cursor.executemany(
        "INSERT INTO products (product_name, category, unit_price, stock_quantity) VALUES (?, ?, ?, ?);",
        products_data,
    )

    customers_data = [
        ("Alice Walker", "New York"),
        ("Benjamin Scott", "Chicago"),
        ("Catherine Miller", "San Francisco"),
        ("David Hernandez", "Austin"),
        ("Emma Watson", "New York"),
        ("Frank Reynolds", "Seattle"),
        ("Grace Hopper", "Boston"),
        ("Henry Ford", "Los Angeles"),
        ("Isabella Garcia", "New York"),
        ("Jack Thompson", "Austin"),
        ("Karen Davis", "New York"),  # New York has 4 customers (highest)
        ("Liam Patel", "Chicago"),
    ]

    cursor.executemany(
        "INSERT INTO customers (customer_name, city) VALUES (?, ?);",
        customers_data,
    )

    # 30 sales transactions across 2024-01 through 2024-05
    sales_data = [
        (1, 1, 2, "2024-01-05", 299.98),
        (2, 2, 1, "2024-01-08", 399.50),
        (3, 3, 3, "2024-01-14", 267.00),
        (4, 4, 4, "2024-01-19", 199.96),
        (5, 5, 2, "2024-01-25", 159.98),
        (7, 6, 5, "2024-01-30", 172.50),
        (9, 7, 1, "2024-02-02", 1299.00),
        (1, 8, 3, "2024-02-09", 449.97),
        (3, 9, 2, "2024-02-14", 178.00),
        (6, 10, 2, "2024-02-20", 258.00),
        (10, 11, 1, "2024-02-27", 249.00),
        (11, 12, 4, "2024-03-03", 159.96),
        (5, 1, 3, "2024-03-09", 239.97),
        (2, 3, 1, "2024-03-15", 399.50),
        (8, 4, 6, "2024-03-22", 359.94),
        (7, 5, 10, "2024-03-29", 345.00),  # high volume
        (12, 6, 2, "2024-04-04", 239.98),
        (1, 7, 4, "2024-04-10", 599.96),
        (4, 8, 5, "2024-04-16", 249.95),
        (9, 9, 1, "2024-04-21", 1299.00),
        (3, 10, 3, "2024-04-28", 267.00),
        (6, 11, 1, "2024-05-03", 129.00),
        (10, 12, 2, "2024-05-07", 498.00),
        (1, 2, 2, "2024-05-12", 299.98),
        (5, 4, 4, "2024-05-18", 319.96),
        (7, 8, 8, "2024-05-23", 276.00),
        (8, 1, 2, "2024-05-27", 119.98),
        (11, 5, 3, "2024-05-30", 119.97),
    ]

    cursor.executemany(
        "INSERT INTO sales (product_id, customer_id, quantity, sale_date, total_amount) VALUES (?, ?, ?, ?, ?);",
        sales_data,
    )

    conn.commit()


def initialize_demo_database(db_path: Optional[str | Path] = None, force_recreate: bool = False) -> Path:
    """Initialize the SQLite demo database repeatably without duplicate seeding.

    Args:
        db_path: Path to database file. Defaults to config.DEMO_DB_PATH.
        force_recreate: If True, drops existing tables and reseeds fresh data.

    Returns:
        Path to initialized database.
    """
    target_path = Path(db_path or DEMO_DB_PATH).resolve()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if force_recreate and target_path.exists():
        target_path.unlink()

    conn = sqlite3.connect(str(target_path))
    try:
        # Check if already seeded
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products';")
        has_products = cursor.fetchone() is not None

        if not has_products:
            create_schema(conn)
            seed_data(conn)
        else:
            # Check row count
            cursor.execute("SELECT COUNT(*) FROM products;")
            count = cursor.fetchone()[0]
            if count == 0:
                seed_data(conn)
    finally:
        conn.close()

    return target_path


if __name__ == "__main__":
    path = initialize_demo_database(force_recreate=True)
    print(f"Successfully initialized demo database at: {path}")
