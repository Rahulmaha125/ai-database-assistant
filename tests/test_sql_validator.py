"""Tests for SQL validation and security checks."""

import pytest
from security.sql_validator import SQLValidator, SQLValidationError


@pytest.fixture
def test_schema():
    return {
        "products": ["product_id", "product_name", "category", "unit_price", "stock_quantity"],
        "customers": ["customer_id", "customer_name", "city"],
        "sales": ["sale_id", "product_id", "customer_id", "quantity", "sale_date", "total_amount"],
    }


@pytest.fixture
def validator(test_schema):
    return SQLValidator(schema=test_schema, default_limit=100, max_limit=500)


def test_valid_select_query_accepted(validator):
    sql = "SELECT product_name, unit_price FROM products;"
    result = validator.validate(sql)
    assert "SELECT" in result.upper()
    assert "LIMIT" in result.upper()


def test_valid_count_and_aggregation_queries(validator):
    sql = "SELECT category, COUNT(*) AS count, AVG(unit_price) AS avg_price FROM products GROUP BY category;"
    result = validator.validate(sql)
    assert "SELECT" in result.upper()
    assert "GROUP BY" in result.upper()


def test_valid_filtering_and_sorting(validator):
    sql = "SELECT product_name, stock_quantity FROM products WHERE stock_quantity < 10 ORDER BY stock_quantity ASC;"
    result = validator.validate(sql)
    assert "WHERE" in result.upper()
    assert "ORDER BY" in result.upper()


def test_valid_join_query(validator):
    sql = """
    SELECT p.product_name, SUM(s.quantity) AS total_sold
    FROM sales s
    JOIN products p ON s.product_id = p.product_id
    GROUP BY p.product_id, p.product_name
    ORDER BY total_sold DESC;
    """
    result = validator.validate(sql)
    assert "JOIN" in result.upper()


@pytest.mark.parametrize("malicious_sql", [
    "DROP TABLE products;",
    "DELETE FROM products WHERE product_id = 1;",
    "UPDATE products SET unit_price = 0;",
    "INSERT INTO products (product_name, category, unit_price, stock_quantity) VALUES ('Bad', 'Test', 1, 1);",
    "ALTER TABLE products ADD COLUMN secret TEXT;",
    "CREATE TABLE backdoor (id INT);",
    "PRAGMA table_info(products);",
    "ATTACH DATABASE 'evil.db' AS evil;",
    "DETACH DATABASE evil;",
])
def test_prohibited_write_and_admin_operations_rejected(validator, malicious_sql):
    with pytest.raises(SQLValidationError):
        validator.validate(malicious_sql)


def test_multiple_statements_rejected(validator):
    sql = "SELECT * FROM products; SELECT * FROM customers;"
    with pytest.raises(SQLValidationError, match="Multiple SQL statements"):
        validator.validate(sql)


def test_unknown_table_rejected(validator):
    sql = "SELECT * FROM users;"
    with pytest.raises(SQLValidationError, match="Unauthorized or unknown table 'users'"):
        validator.validate(sql)


def test_unknown_column_rejected(validator):
    sql = "SELECT password FROM products;"
    with pytest.raises(SQLValidationError, match="Unknown column 'password'"):
        validator.validate(sql)


def test_empty_sql_rejected(validator):
    with pytest.raises(SQLValidationError, match="Query is empty"):
        validator.validate("   ")


def test_prohibited_functions_rejected(validator):
    sql = "SELECT load_extension('exploit.so') FROM products;"
    with pytest.raises(SQLValidationError):
        validator.validate(sql)


def test_limit_enforcement_default(validator):
    sql = "SELECT product_name FROM products;"
    result = validator.validate(sql)
    assert "LIMIT 100" in result.upper()


def test_limit_enforcement_clamping(validator):
    sql = "SELECT product_name FROM products LIMIT 5000;"
    result = validator.validate(sql)
    assert "LIMIT 500" in result.upper()


def test_limit_preserves_smaller_limit(validator):
    sql = "SELECT product_name FROM products LIMIT 5;"
    result = validator.validate(sql)
    assert "LIMIT 5" in result.upper()
