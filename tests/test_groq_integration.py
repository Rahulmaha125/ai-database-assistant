"""Tests for Groq Cloud API LLM integration and hybrid fallback."""

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import DEFAULT_GROQ_MODEL, GROQ_API_KEY
from db.init_db import initialize_demo_database
from llm.model_manager import LLMManager, ModelProvider
from services.query_service import QueryService
from services.schema_builder import SchemaBuilder


def test_groq_status_online_with_valid_key():
    """Verify Groq Cloud is detected as online when valid key is provided."""
    if not GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY not configured in environment.")

    mgr = LLMManager(groq_api_key=GROQ_API_KEY)
    status = mgr.get_status(force_refresh=True)

    assert status.is_available is True
    assert status.provider == "groq"
    assert status.model_name == DEFAULT_GROQ_MODEL
    assert len(status.installed_models) > 0


def test_groq_sql_generation_and_execution_on_demo_db():
    """Verify real Groq Cloud generates valid SQLite query that passes AST check and executes."""
    if not GROQ_API_KEY:
        pytest.skip("GROQ_API_KEY not configured in environment.")

    db_path = initialize_demo_database()
    sb = SchemaBuilder(db_path)
    schema_dict = sb.get_validator_schema()
    schema_prompt = sb.build_schema_prompt_text()

    mgr = LLMManager(groq_api_key=GROQ_API_KEY)
    question = "Which category has the highest total sales amount?"

    gen = mgr.generate_sql(question, schema_text=schema_prompt, table_columns=schema_dict)

    assert gen["sql"] is not None
    assert gen["source"] == "cloud_llm_groq"
    assert "Groq Cloud" in gen["model"]

    # Execute against QueryService
    qs = QueryService(db_path, schema=schema_dict)
    res = qs.execute(gen["sql"], question=question)

    assert res.success is True
    assert res.row_count > 0
    assert not res.df.empty
    assert len(res.summary) > 0


def test_groq_fallback_when_key_is_empty():
    """Verify system seamlessly falls back to Ollama or template when Groq key is empty."""
    mgr = LLMManager(groq_api_key="", ollama_url="http://127.0.0.1:59999")
    status = mgr.get_status(force_refresh=True)

    # When both Groq key is empty and Ollama is unreachable
    assert status.is_available is False
    assert status.provider == "offline_template_fallback"
