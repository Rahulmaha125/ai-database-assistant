"""End-to-end regression test verifying real Ollama model inference on user uploaded dataset."""

from pathlib import Path
import pytest
from llm.model_manager import LLMManager
from services.file_processor import FileProcessor
from services.query_service import QueryService
from services.schema_builder import SchemaBuilder


def test_real_ollama_workflow_on_user_csv(tmp_path):
    # 1. Verify Ollama is online
    mgr = LLMManager()
    status = mgr.get_status(force_refresh=True)
    if not status.is_available or status.provider != "ollama":
        pytest.skip("Local Ollama daemon is not running; skipping live Ollama inference test.")

    # 2. Process user CSV with unique items
    csv_path = Path("data/user_rahul_sensors.csv")
    assert csv_path.exists(), "CSV test data file missing"

    fp = FileProcessor(uploads_dir=tmp_path)
    up = fp.process_file(csv_path, file_name="user_rahul_sensors.csv")

    assert up.row_count == 3
    assert up.table_name == "user_rahul_sensors"
    assert "product_name" in up.columns
    assert "stock_quantity" in up.columns

    # 3. Build schema description
    sb = SchemaBuilder(up.db_path)
    schema_dict = sb.get_validator_schema()
    schema_prompt = sb.build_schema_prompt_text()

    # 4. Generate SQL using REAL Ollama model inference
    question = "Which product has the lowest stock?"
    gen = mgr.generate_sql(
        question=question,
        schema_text=schema_prompt,
        table_columns=schema_dict,
    )

    print("\n--- OLLAMA GENERATION RESULT ---")
    print(f"Source: {gen['source']}")
    print(f"Model: {gen['model']}")
    print(f"Raw Output: {gen.get('raw_response')}")
    print(f"Extracted SQL: {gen['sql']}")

    assert gen["source"] == "local_llm_ollama", "Inference must be tagged as real Ollama inference"
    assert "qwen2.5-coder" in gen["model"].lower(), "Model must be qwen2.5-coder"
    assert gen["sql"] is not None, "Ollama must generate a candidate SQL query"
    assert "SELECT" in gen["sql"].upper()
    assert up.table_name in gen["sql"]

    # 5. Validate & Execute through QueryService
    qs = QueryService(up.db_path, schema=schema_dict)
    query_res = qs.execute(gen["sql"], question=question)

    print("\n--- QUERY EXECUTION RESULT ---")
    print(f"Success: {query_res.success}")
    print(f"Validated SQL: {query_res.validated_sql}")
    print(f"Columns: {query_res.columns}")
    print(f"Rows: {query_res.rows}")
    print(f"Summary: {query_res.summary}")

    assert query_res.success is True, f"Query execution failed: {query_res.error}"
    assert query_res.row_count >= 1

    # 6. Verify correct row is returned (RahulSensor with stock 3)
    first_row = query_res.rows[0]
    # Check that RahulSensor is in the first row
    assert "RahulSensor" in first_row, f"Expected 'RahulSensor' in row but got: {first_row}"
    # If stock_quantity was selected, check that 3 is in the row
    if len(first_row) > 1:
        assert 3 in first_row, f"Expected stock 3 in row but got: {first_row}"
