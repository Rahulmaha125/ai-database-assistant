"""Schema introspection and prompt context builder."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import execute_query, get_database_schema_dict, get_foreign_keys, get_table_names


class SchemaBuilder:
    """Builds clean schema descriptions and column allowlists for LLMs and SQL validators."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def get_validator_schema(self) -> Dict[str, List[str]]:
        """Return dict of {table_name: [column_name_1, column_name_2, ...]} for SQLValidator."""
        schema_dict = get_database_schema_dict(self.db_path)
        return {
            table: [col["name"] for col in cols]
            for table, cols in schema_dict.items()
        }

    def get_sample_values(self, table: str, column: str, limit: int = 3) -> List[Any]:
        """Fetch distinct non-null sample values for a column to give semantic context."""
        try:
            # Table and column are validated from schema_dict
            query = f'SELECT DISTINCT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT {limit};'
            res = execute_query(self.db_path, query, read_only=True)
            return [row[0] for row in res["rows"]]
        except Exception:
            return []

    def build_schema_prompt_text(self) -> str:
        """Construct a detailed, LLM-friendly schema description in SQLite DDL format."""
        tables = get_table_names(self.db_path)
        schema_dict = get_database_schema_dict(self.db_path)

        schema_lines = ["### Database Schema (SQLite Dialect):"]

        for table in tables:
            cols = schema_dict.get(table, [])
            fks = get_foreign_keys(self.db_path, table)
            schema_lines.append(f"\nTable: `{table}`")
            schema_lines.append("Columns:")

            for col in cols:
                pk_flag = " [PRIMARY KEY]" if col["pk"] else ""
                col_name = col["name"]
                col_type = col["type"] or "TEXT"
                samples = self.get_sample_values(table, col_name, limit=3)
                sample_str = f" (e.g. {samples})" if samples else ""
                schema_lines.append(f"  - `{col_name}` ({col_type}){pk_flag}{sample_str}")

            if fks:
                schema_lines.append("Relationships:")
                for fk in fks:
                    schema_lines.append(f"  - FOREIGN KEY (`{fk['from']}`) REFERENCES `{fk['table']}`(`{fk['to']}`)")

        return "\n".join(schema_lines)
