"""Formatting query results into DataFrames, CSV exports, and plain-language summaries."""

import io
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class ResultFormatter:
    """Formats SQL results for presentation, download, and factual summarization."""

    @staticmethod
    def to_dataframe(columns: List[str], rows: List[List[Any]]) -> pd.DataFrame:
        """Convert columns and rows into a pandas DataFrame."""
        if not columns:
            return pd.DataFrame()
        return pd.DataFrame(rows, columns=columns)

    @staticmethod
    def to_csv_bytes(df: pd.DataFrame) -> bytes:
        """Convert DataFrame to UTF-8 CSV bytes for download."""
        return df.to_csv(index=False).encode("utf-8")

    @staticmethod
    def summarize_result(columns: List[str], rows: List[List[Any]], question: str = "") -> str:
        """Generate a factual, deterministic plain-English summary of query results without LLM hallucination."""
        row_count = len(rows)

        if row_count == 0:
            return "No matching records found in the database for this query."

        # Case 1: Single scalar value (e.g. COUNT, SUM, AVG)
        if row_count == 1 and len(columns) == 1:
            col = columns[0].replace("_", " ").title()
            val = rows[0][0]
            if isinstance(val, (int, float)):
                if isinstance(val, float):
                    val_str = f"{val:,.2f}"
                else:
                    val_str = f"{val:,}"
            else:
                val_str = str(val)
            return f"The calculated **{col}** is **{val_str}**."

        # Case 2: Single record with multiple columns (e.g. top item, specific lookup)
        if row_count == 1 and len(columns) > 1:
            pairs = [f"**{col.replace('_', ' ').title()}**: {val}" for col, val in zip(columns, rows[0])]
            return "Found 1 matching record — " + ", ".join(pairs) + "."

        # Case 3: Multiple rows
        # Check if first column is categorical and second is numeric (e.g. top ranking)
        first_row = rows[0]
        if len(columns) >= 2 and isinstance(first_row[1], (int, float)):
            top_entity = str(first_row[0])
            top_val = first_row[1]
            val_format = f"{top_val:,.2f}" if isinstance(top_val, float) else f"{top_val:,}"
            metric_col = columns[1].replace("_", " ").title()
            return f"Retrieved **{row_count} records**. The leading item is **{top_entity}** with a {metric_col} of **{val_format}**."

        return f"Retrieved **{row_count} records** matching your question."
