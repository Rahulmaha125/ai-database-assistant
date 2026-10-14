"""File processing service for Excel and CSV upload, schema inference, and SQLite storage."""

import io
import re
import sqlite3
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import BinaryIO, Dict, List, Optional, Tuple, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from config import ALLOWED_EXTENSIONS, MAX_PREVIEW_ROWS, MAX_UPLOAD_SIZE_MB, UPLOADS_DIR


class FileProcessingError(Exception):
    """Raised when file validation or processing fails."""
    pass


@dataclass
class UploadResult:
    """Metadata and preview for a processed upload."""
    workspace_id: str
    db_path: Path
    table_name: str
    row_count: int
    column_count: int
    columns: List[str]
    column_mapping: Dict[str, str]  # sanitized_col -> original_col
    column_types: Dict[str, str]    # sanitized_col -> sqlite_type
    preview_df: pd.DataFrame
    file_name: str
    warnings: List[str] = field(default_factory=list)


class FileProcessor:
    """Handles upload validation, cleaning, schema inference, and isolated SQLite database creation."""

    def __init__(self, uploads_dir: Optional[Path] = None):
        self.uploads_dir = Path(uploads_dir or UPLOADS_DIR)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_identifier(name: str, fallback: str = "col") -> str:
        """Sanitize an arbitrary string into a safe, alphanumeric SQLite identifier."""
        cleaned = re.sub(r"[^\w]+", "_", str(name).strip().lower())
        cleaned = cleaned.strip("_")
        if not cleaned or cleaned[0].isdigit():
            cleaned = f"{fallback}_{cleaned}" if cleaned else fallback
        return cleaned

    def clean_column_names(self, columns: List[str]) -> Tuple[List[str], Dict[str, str], List[str]]:
        """Deduplicate and sanitize column names.

        Returns:
            Tuple of (sanitized_columns, mapping_sanitized_to_original, warnings)
        """
        sanitized = []
        mapping = {}
        warnings = []
        seen = {}

        for idx, col in enumerate(columns):
            orig_col = str(col).strip()
            if not orig_col or orig_col.startswith("Unnamed:"):
                orig_col = f"column_{idx + 1}"
                warnings.append(f"Header for column {idx + 1} was missing or empty; assigned name '{orig_col}'.")

            safe_name = self.sanitize_identifier(orig_col, fallback=f"col_{idx + 1}")

            # Check if pandas auto-renamed a duplicate column (e.g. score.1)
            base_orig = re.sub(r"\.\d+$", "", orig_col)
            is_pandas_duplicate = (base_orig != orig_col)

            if safe_name in seen or is_pandas_duplicate:
                count = seen.get(safe_name, 0) + 1
                seen[safe_name] = count
                unique_name = f"{safe_name}_{count}" if safe_name in seen else safe_name
                warnings.append(f"Duplicate column detected for '{base_orig}'; mapped to '{unique_name}'.")
            else:
                seen[safe_name] = 0
                unique_name = safe_name

            sanitized.append(unique_name)
            mapping[unique_name] = orig_col

        return sanitized, mapping, warnings

    @staticmethod
    def infer_sqlite_types(df: pd.DataFrame) -> Dict[str, str]:
        """Infer SQLite data types from DataFrame columns."""
        type_mapping = {}
        for col in df.columns:
            series = df[col].dropna()
            if series.empty:
                type_mapping[col] = "TEXT"
                continue

            if pd.api.types.is_integer_dtype(series):
                type_mapping[col] = "INTEGER"
            elif pd.api.types.is_float_dtype(series):
                # Check if floats are actually whole numbers
                if (series % 1 == 0).all():
                    type_mapping[col] = "INTEGER"
                else:
                    type_mapping[col] = "REAL"
            elif pd.api.types.is_bool_dtype(series):
                type_mapping[col] = "INTEGER"
            elif pd.api.types.is_datetime64_any_dtype(series):
                type_mapping[col] = "TEXT"
            else:
                # Try parsing as numeric or date
                converted_num = pd.to_numeric(series, errors="coerce")
                if converted_num.notna().sum() / len(series) > 0.8:
                    if (converted_num.dropna() % 1 == 0).all():
                        type_mapping[col] = "INTEGER"
                    else:
                        type_mapping[col] = "REAL"
                else:
                    type_mapping[col] = "TEXT"

        return type_mapping

    def process_file(
        self,
        file_input: Union[str, Path, BinaryIO, io.BytesIO],
        file_name: str,
        file_size_bytes: Optional[int] = None,
    ) -> UploadResult:
        """Process, validate, and convert an uploaded file into an isolated SQLite database.

        Args:
            file_input: File path, open file, or BytesIO buffer.
            file_name: Name of the uploaded file.
            file_size_bytes: Size in bytes if known.

        Returns:
            UploadResult dataclass.
        """
        suffix = Path(file_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise FileProcessingError(
                f"Unsupported file type '{suffix}'. Please upload a CSV (.csv) or Excel (.xlsx, .xls) file."
            )

        max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if file_size_bytes and file_size_bytes > max_bytes:
            raise FileProcessingError(
                f"File size ({file_size_bytes / (1024 * 1024):.1f} MB) exceeds maximum allowed limit of {MAX_UPLOAD_SIZE_MB} MB."
            )

        try:
            if suffix == ".csv":
                df = pd.read_csv(file_input)
            elif suffix in {".xlsx", ".xls"}:
                df = pd.read_excel(file_input)
            else:
                raise FileProcessingError(f"Unsupported format '{suffix}'")
        except pd.errors.EmptyDataError:
            raise FileProcessingError(f"The uploaded file '{file_name}' contains no readable data or rows.")
        except Exception as e:
            raise FileProcessingError(f"Failed to parse file '{file_name}': {str(e)}") from e

        if len(df.columns) == 0:
            raise FileProcessingError(f"The uploaded file '{file_name}' contains no readable columns.")

        if len(df) == 0:
            raise FileProcessingError(f"The uploaded file '{file_name}' contains headers but zero data rows.")

        # Clean and sanitize column names
        sanitized_cols, col_mapping, warnings = self.clean_column_names(list(df.columns))
        df.columns = sanitized_cols

        # Infer SQLite types
        col_types = self.infer_sqlite_types(df)

        # Generate isolated database
        workspace_id = uuid.uuid4().hex[:12]
        db_path = self.uploads_dir / f"workspace_{workspace_id}.db"

        # Table name normalized from filename stem
        stem = Path(file_name).stem
        table_name = self.sanitize_identifier(stem, fallback="uploaded_table")

        # Save into isolated SQLite database
        conn = sqlite3.connect(str(db_path))
        try:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            conn.commit()
        finally:
            conn.close()

        preview_df = df.head(MAX_PREVIEW_ROWS).copy()

        return UploadResult(
            workspace_id=workspace_id,
            db_path=db_path,
            table_name=table_name,
            row_count=len(df),
            column_count=len(df.columns),
            columns=sanitized_cols,
            column_mapping=col_mapping,
            column_types=col_types,
            preview_df=preview_df,
            file_name=file_name,
            warnings=warnings,
        )
