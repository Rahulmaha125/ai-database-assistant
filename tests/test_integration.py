"""End-to-end integration tests for Demo Mode and Upload Mode workflows."""

import io
import pytest
import pandas as pd
from db.init_db import initialize_demo_database, DEMO_QUESTIONS
from llm.model_manager import LLMManager
from services.chart_service import ChartService
from services.file_processor import FileProcessor
from services.query_service import QueryService
from services.result_formatter import ResultFormatter
from services.schema_builder import SchemaBuilder


def test_e2e_demo_mode_workflow():
    # 1. Initialize demo database
    db_path = initialize_demo_database()
    sb = SchemaBuilder(db_path)
    schema_dict = sb.get_validator_schema()
    schema_prompt = sb.build_schema_prompt_text()

    assert "products" in schema_dict
    assert "customers" in schema_dict
    assert "sales" in schema_dict

    # 2. Test model manager generating SQL for each demo question
    llm = LLMManager()
    qs = QueryService(db_path, schema=schema_dict)

    for item in DEMO_QUESTIONS:
        question = item["question"]
        gen = llm.generate_sql(question, schema_text=schema_prompt, table_columns=schema_dict)

        assert gen["sql"] is not None
        assert gen["source"] in ["cloud_llm_groq", "verified_demo_template", "local_llm_ollama", "local_llm_huggingface"]

        # 3. Execute query
        res = qs.execute(gen["sql"], question=question)
        assert res.success is True
        assert res.row_count > 0
        assert not res.df.empty
        assert len(res.summary) > 0

        # 4. Check CSV export capability
        csv_bytes = ResultFormatter.to_csv_bytes(res.df)
        assert len(csv_bytes) > 0


def test_e2e_upload_mode_workflow(tmp_path):
    # 1. Simulate user uploading an inventory CSV file
    csv_data = io.BytesIO(
        b"warehouse_id,item_name,category,quantity_on_hand,reorder_level\n"
        b"1,Heavy Duty Drill,Power Tools,15,5\n"
        b"2,Laser Level,Measuring Tools,4,10\n"
        b"3,Safety Goggles,Personal Protective,50,20\n"
        b"4,Toolbox Chest,Storage,2,5\n"
    )
    processor = FileProcessor(uploads_dir=tmp_path)
    upload_res = processor.process_file(csv_data, file_name="inventory_stock.csv")

    assert upload_res.table_name == "inventory_stock"
    assert upload_res.row_count == 4
    assert upload_res.column_count == 5

    # 2. Schema build
    sb = SchemaBuilder(upload_res.db_path)
    schema_dict = sb.get_validator_schema()
    schema_prompt = sb.build_schema_prompt_text()

    assert upload_res.table_name in schema_dict

    # 3. Ask question: preview or count
    llm = LLMManager()
    gen = llm.generate_sql("how many rows in data?", schema_text=schema_prompt, table_columns=schema_dict)
    assert gen["sql"] is not None

    # 4. Execute validated query
    qs = QueryService(upload_res.db_path, schema=schema_dict)
    res = qs.execute(gen["sql"], question="how many rows in data?")
    assert res.success is True
    assert res.row_count == 1
    assert res.df.iloc[0, 0] == 4

    # 5. Direct analytical query on uploaded data
    custom_sql = f'SELECT item_name, quantity_on_hand FROM "{upload_res.table_name}" WHERE quantity_on_hand < reorder_level;'
    res_reorder = qs.execute(custom_sql, question="Items below reorder level")
    assert res_reorder.success is True
    assert res_reorder.row_count == 2  # Laser Level (4 < 10) and Toolbox Chest (2 < 5)

    # 6. Chart service check
    chart = ChartService.create_chart(res_reorder.df, title="Items Below Reorder Level")
    assert chart is not None
