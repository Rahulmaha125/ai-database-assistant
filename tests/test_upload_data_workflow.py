"""End-to-end tests for the Upload Data workflow with Superstore CSV data."""

from pathlib import Path
import pandas as pd
import pytest

from services.file_processor import FileProcessor
from services.schema_builder import SchemaBuilder
from services.query_service import QueryService
from llm.model_manager import LLMManager

SUPERSTORE_CSV = Path(__file__).resolve().parent.parent / "data" / "SampleSuperstore.csv"
APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_superstore_upload_and_schema_extraction():
    """Verify that Superstore CSV is parsed and loaded into SQLite accurately."""
    assert SUPERSTORE_CSV.exists(), "SampleSuperstore.csv does not exist"

    processor = FileProcessor()
    with open(SUPERSTORE_CSV, "rb") as f:
        upload_res = processor.process_file(f, file_name="SampleSuperstore.csv")

    assert upload_res.table_name == "samplesuperstore"
    assert upload_res.row_count == 9994
    assert "sales" in upload_res.columns
    assert "state" in upload_res.columns
    assert "profit" in upload_res.columns

    # Check schema builder
    sb = SchemaBuilder(upload_res.db_path)
    schema = sb.get_validator_schema()
    assert "samplesuperstore" in schema
    assert "sales" in schema["samplesuperstore"]


def test_ollama_query_on_uploaded_superstore():
    """Verify real Ollama inference and execution on uploaded Superstore dataset."""
    processor = FileProcessor()
    with open(SUPERSTORE_CSV, "rb") as f:
        upload_res = processor.process_file(f, file_name="SampleSuperstore.csv")

    manager = LLMManager()
    status = manager.get_status()
    if not status.is_available:
        pytest.skip("Local Ollama is offline")

    sb = SchemaBuilder(upload_res.db_path)
    schema_dict = sb.get_validator_schema()
    prompt_text = sb.build_schema_prompt_text()

    question = "What is the total sales amount?"
    gen_res = manager.generate_sql(
        question=question,
        schema_text=prompt_text,
        table_columns=schema_dict,
    )

    assert gen_res["sql"] is not None
    assert "samplesuperstore" in gen_res["sql"].lower()

    # Validate and execute
    qs = QueryService(upload_res.db_path, schema=schema_dict)
    q_res = qs.execute(gen_res["sql"], question=question)

    assert q_res.success is True
    assert len(q_res.rows) == 1
    # Sales should be around 2.29 million
    total_sales = float(q_res.rows[0][0])
    assert total_sales > 1000000


def test_upload_page_displays_question_section_with_apptest():
    """Verify that the Upload Data page displays the question section below preview."""
    from streamlit.testing.v1 import AppTest

    processor = FileProcessor()
    with open(SUPERSTORE_CSV, "rb") as f:
        upload_res = processor.process_file(f, file_name="SampleSuperstore.csv")

    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.session_state["nav_view"] = "Upload Data"
    at.session_state["data_mode"] = "upload"
    at.session_state["upload_result"] = upload_res
    at.run()

    assert not at.exception

    # Check for the section title
    markdown_texts = [m.value for m in at.markdown]
    has_ask_section = any("Ask a Question About Your Data" in text for text in markdown_texts)
    assert has_ask_section, "Ask a Question About Your Data section was not found on Upload Data page"

    # Check for text input with key 'upload_question_input'
    assert len(at.text_input) >= 1
    input_keys = [ti.key for ti in at.text_input]
    assert "upload_question_input" in input_keys

    # Check for Ask AI button with key 'btn_upload_ask'
    btn_keys = [b.key for b in at.button]
    assert "btn_upload_ask" in btn_keys
