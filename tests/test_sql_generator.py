"""Tests for LLM SQL output extraction, prompt formatting, and unavailable-model state."""

import pytest
from llm.model_manager import LLMManager
from llm.sql_generator import SQLGenerator, extract_sql_from_response


def test_extract_sql_from_markdown():
    raw = """Here is the query you requested:
```sql
SELECT product_name, stock_quantity FROM products WHERE stock_quantity < 10;
```
Hope that helps!"""
    extracted = extract_sql_from_response(raw)
    assert extracted.startswith("SELECT")
    assert "stock_quantity < 10" in extracted
    assert "```" not in extracted


def test_extract_sql_with_thinking_tags():
    raw = """<think>
The user wants to count the products in the catalog.
Table is products.
Column is product_id or *.
</think>
SELECT COUNT(*) FROM products;"""
    extracted = extract_sql_from_response(raw)
    assert "<think>" not in extracted
    assert extracted.strip() == "SELECT COUNT(*) FROM products;"


def test_extract_sql_from_conversational_prefix():
    raw = "Sure! Here is the SQL:\nSELECT * FROM customers ORDER BY city ASC;"
    extracted = extract_sql_from_response(raw)
    assert extracted.startswith("SELECT")
    assert "customers" in extracted


def test_extract_sql_empty_input():
    assert extract_sql_from_response("") == ""
    assert extract_sql_from_response("   \n  ") == ""


def test_llm_manager_safe_unavailable_state():
    # Connect to nonexistent URL with empty Groq key to guarantee offline status
    manager = LLMManager(groq_api_key="", ollama_url="http://127.0.0.1:59999")
    status = manager.get_status()
    assert status.is_available is False
    assert "offline" in status.provider.lower()

    # Asking a demo question uses verified template, with transparent labeling
    gen = manager.generate_sql(
        question="How many products are there?",
        schema_text="",
    )
    assert gen["sql"] is not None
    assert "products" in gen["sql"]
    assert gen["source"] == "verified_demo_template"
    # Ensure it does NOT pretend to be an LLM
    assert "Local LLM is offline" in gen["explanation"]


def test_llm_manager_unmapped_question_fails_safely_when_offline():
    manager = LLMManager(groq_api_key="", ollama_url="http://127.0.0.1:59999")
    gen = manager.generate_sql(
        question="What is the quantum coefficient of Mars?",
        schema_text="",
    )
    assert gen["sql"] is None
    assert gen["source"] == "unavailable"
    assert "offline" in gen["error"].lower()
