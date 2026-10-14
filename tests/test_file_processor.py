"""Tests for file upload validation, schema inference, and SQLite conversion."""

import io
import pytest
import pandas as pd
from services.file_processor import FileProcessor, FileProcessingError


@pytest.fixture
def processor(tmp_path):
    return FileProcessor(uploads_dir=tmp_path)


def test_valid_csv_upload_succeeds(processor):
    csv_content = io.BytesIO(b"id,name,department,salary\n1,Alice,Engineering,95000\n2,Bob,Marketing,72000\n")
    res = processor.process_file(csv_content, file_name="employees.csv")

    assert res.row_count == 2
    assert res.column_count == 4
    assert res.table_name == "employees"
    assert "id" in res.columns
    assert "salary" in res.columns
    assert res.db_path.exists()


def test_valid_excel_upload_succeeds(processor, tmp_path):
    df = pd.DataFrame({
        "item_code": [101, 102],
        "item_name": ["Widget A", "Widget B"],
        "stock": [50, 12],
    })
    excel_path = tmp_path / "inventory.xlsx"
    df.to_excel(excel_path, index=False)

    res = processor.process_file(excel_path, file_name="inventory.xlsx")
    assert res.row_count == 2
    assert res.table_name == "inventory"
    assert "stock" in res.columns


def test_empty_csv_fails_safely(processor):
    empty_csv = io.BytesIO(b"")
    with pytest.raises(FileProcessingError, match="no readable data"):
        processor.process_file(empty_csv, file_name="empty.csv")


def test_csv_with_headers_only_fails_safely(processor):
    headers_only = io.BytesIO(b"col1,col2,col3\n")
    with pytest.raises(FileProcessingError, match="zero data rows"):
        processor.process_file(headers_only, file_name="headers_only.csv")


def test_duplicate_column_names_handled(processor):
    # Two columns named 'score'
    dup_csv = io.BytesIO(b"student,score,score\nAlice,90,95\nBob,80,85\n")
    res = processor.process_file(dup_csv, file_name="students.csv")
    assert len(res.columns) == 3
    # Check deduplication occurred
    assert len(set(res.columns)) == 3
    assert len(res.warnings) > 0


def test_unusual_column_names_sanitized(processor):
    weird_csv = io.BytesIO(b"Customer #,Total ($),Date / Time\n1,100,2024-01-01\n")
    res = processor.process_file(weird_csv, file_name="transactions.csv")
    for col in res.columns:
        assert not any(char in col for char in ["#", "$", "(", ")", "/", " "])


def test_unsupported_file_extension_rejected(processor):
    txt_file = io.BytesIO(b"hello world")
    with pytest.raises(FileProcessingError, match="Unsupported file type"):
        processor.process_file(txt_file, file_name="data.txt")
