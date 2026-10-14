"""Tests for SQLite database operations and read-only constraints."""

import pytest
from pathlib import Path
from db.database import (
    execute_query,
    get_connection,
    get_table_names,
    get_table_schema,
    get_database_schema_dict,
    DatabaseError,
    ReadOnlyViolationError,
)
from db.init_db import initialize_demo_database, DEMO_QUESTIONS
from config import DEMO_DB_PATH


@pytest.fixture(scope="module")
def initialized_db():
    return initialize_demo_database(force_recreate=True)


def test_tables_created(initialized_db):
    tables = get_table_names(initialized_db)
    assert "products" in tables
    assert "customers" in tables
    assert "sales" in tables


def test_schema_introspection(initialized_db):
    schema = get_database_schema_dict(initialized_db)
    assert "products" in schema
    product_cols = [c["name"] for c in schema["products"]]
    assert "product_id" in product_cols
    assert "product_name" in product_cols
    assert "unit_price" in product_cols
    assert "stock_quantity" in product_cols


def test_demo_questions_execution(initialized_db):
    for item in DEMO_QUESTIONS:
        result = execute_query(initialized_db, item["sql"], read_only=True)
        assert result["row_count"] > 0
        assert len(result["columns"]) > 0


def test_read_only_connection_blocks_insert(initialized_db):
    with pytest.raises((ReadOnlyViolationError, DatabaseError)):
        execute_query(
            initialized_db,
            "INSERT INTO products (product_name, category, unit_price, stock_quantity) VALUES ('Hack', 'Test', 10, 10);",
            read_only=True,
        )


def test_lowest_stock_product(initialized_db):
    result = execute_query(
        initialized_db,
        "SELECT product_name, stock_quantity FROM products ORDER BY stock_quantity ASC LIMIT 1;",
        read_only=True,
    )
    assert result["rows"][0][0] == "Portable Bluetooth Speaker"
    assert result["rows"][0][1] == 3


def test_city_with_most_customers(initialized_db):
    result = execute_query(
        initialized_db,
        "SELECT city, COUNT(*) AS count FROM customers GROUP BY city ORDER BY count DESC LIMIT 1;",
        read_only=True,
    )
    assert result["rows"][0][0] == "New York"
    assert result["rows"][0][1] == 4


def test_nonexistent_table_raises_error(initialized_db):
    with pytest.raises(DatabaseError):
        execute_query(initialized_db, "SELECT * FROM non_existent_table;", read_only=True)
