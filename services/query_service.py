"""Orchestrator for SQL validation, execution, formatting, and charting."""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import execute_query, DatabaseError, ReadOnlyViolationError
from security.sql_validator import SQLValidator, SQLValidationError
from services.chart_service import ChartService
from services.result_formatter import ResultFormatter


@dataclass
class QueryResult:
    """Encapsulates the full result lifecycle of an executed query."""
    success: bool
    raw_sql: str
    validated_sql: str = ""
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    columns: List[str] = field(default_factory=list)
    rows: List[List[Any]] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    summary: str = ""
    chart_fig: Optional[go.Figure] = None
    error: Optional[str] = None
    truncated: bool = False


class QueryService:
    """Executes validated SQL against SQLite databases safely."""

    def __init__(self, db_path: str | Path, schema: Optional[Dict[str, List[str]]] = None):
        self.db_path = Path(db_path)
        self.schema = schema or {}
        self.validator = SQLValidator(schema=self.schema)

    def update_schema(self, schema: Dict[str, List[str]]) -> None:
        """Update active schema for validation."""
        self.schema = schema
        self.validator.set_schema(schema)

    def execute(self, sql_query: str, question: str = "") -> QueryResult:
        """Validate and execute a SQL query string.

        Args:
            sql_query: Model or user-supplied SQL string.
            question: Original natural-language question for summary context.

        Returns:
            QueryResult dataclass.
        """
        raw_sql = sql_query.strip() if sql_query else ""

        if not raw_sql:
            return QueryResult(
                success=False,
                raw_sql=raw_sql,
                error="No SQL query provided to execute.",
            )

        # Step 1: Security and AST Validation
        try:
            validated_sql = self.validator.validate(raw_sql)
        except SQLValidationError as e:
            return QueryResult(
                success=False,
                raw_sql=raw_sql,
                error=f"Security Validation Failed: {str(e)}",
            )
        except Exception as e:
            return QueryResult(
                success=False,
                raw_sql=raw_sql,
                error=f"Unexpected Validation Error: {str(e)}",
            )

        # Step 2: Read-Only SQLite Execution
        try:
            db_res = execute_query(self.db_path, validated_sql, read_only=True)
        except ReadOnlyViolationError as e:
            return QueryResult(
                success=False,
                raw_sql=raw_sql,
                validated_sql=validated_sql,
                error=f"Security Violation: Database write rejected. ({str(e)})",
            )
        except DatabaseError as e:
            return QueryResult(
                success=False,
                raw_sql=raw_sql,
                validated_sql=validated_sql,
                error=f"Database Execution Error: {str(e)}",
            )
        except Exception as e:
            return QueryResult(
                success=False,
                raw_sql=raw_sql,
                validated_sql=validated_sql,
                error=f"Execution Failed: {str(e)}",
            )

        # Step 3: Format results
        columns = db_res["columns"]
        rows = db_res["rows"]
        df = ResultFormatter.to_dataframe(columns, rows)
        summary = ResultFormatter.summarize_result(columns, rows, question=question)

        # Step 4: Optional Chart Generation
        chart_fig = None
        if ChartService.can_plot(df):
            chart_fig = ChartService.create_chart(df, title=f"Results: {question}" if question else "Query Results")

        return QueryResult(
            success=True,
            raw_sql=raw_sql,
            validated_sql=validated_sql,
            df=df,
            columns=columns,
            rows=rows,
            row_count=db_res["row_count"],
            execution_time_ms=db_res["execution_time_ms"],
            summary=summary,
            chart_fig=chart_fig,
            truncated=db_res["truncated"],
        )
