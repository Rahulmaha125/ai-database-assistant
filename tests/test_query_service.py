"""Tests for query orchestration, result formatting, and safety checks."""

import pytest
from db.init_db import initialize_demo_database
from services.query_service import QueryService
from services.result_formatter import ResultFormatter
from services.schema_builder import SchemaBuilder


@pytest.fixture(scope="module")
def demo_db():
    return initialize_demo_database()


@pytest.fixture
def query_service(demo_db):
    sb = SchemaBuilder(demo_db)
    schema = sb.get_validator_schema()
    return QueryService(demo_db, schema=schema)


def test_query_service_success(query_service):
    sql = "SELECT product_name, unit_price FROM products ORDER BY unit_price DESC LIMIT 3;"
    res = query_service.execute(sql, question="Top 3 expensive products")
    assert res.success is True
    assert res.row_count == 3
    assert len(res.columns) == 2
    assert "product_name" in res.columns
    assert res.execution_time_ms > 0
    assert not res.df.empty
    assert "3 records" in res.summary


def test_query_service_no_matching_records(query_service):
    sql = "SELECT * FROM products WHERE stock_quantity > 1000;"
    res = query_service.execute(sql, question="Products with huge stock")
    assert res.success is True
    assert res.row_count == 0
    assert "No matching records found" in res.summary


def test_query_service_blocks_forbidden_sql(query_service):
    sql = "DELETE FROM products WHERE product_id = 1;"
    res = query_service.execute(sql)
    assert res.success is False
    assert "Security Validation Failed" in res.error


def test_csv_export_generation(query_service):
    sql = "SELECT product_name, stock_quantity FROM products LIMIT 2;"
    res = query_service.execute(sql)
    csv_bytes = ResultFormatter.to_csv_bytes(res.df)
    assert isinstance(csv_bytes, bytes)
    assert b"product_name" in csv_bytes
    assert b"stock_quantity" in csv_bytes


def test_scalar_aggregation_summary(query_service):
    sql = "SELECT COUNT(*) AS total_count FROM products;"
    res = query_service.execute(sql)
    assert res.success is True
    assert res.row_count == 1
    assert "12" in res.summary
