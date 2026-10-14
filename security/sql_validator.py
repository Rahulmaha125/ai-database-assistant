import sys
from pathlib import Path
import re
from typing import Dict, List, Optional, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import sqlglot
from sqlglot import exp
from config import DEFAULT_QUERY_ROW_LIMIT, MAX_QUERY_ROW_LIMIT


class SQLValidationError(Exception):
    """Raised when a SQL query violates security constraints or schema rules."""
    pass


FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "replace", "attach", "detach", "pragma", "reindex", "vacuum", "analyze",
    "load_extension", "savepoint", "release", "rollback", "transaction", "commit",
}

FORBIDDEN_AST_TYPES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.Create,
    exp.Pragma,
    exp.Command,
    exp.Execute,
    exp.Transaction,
    exp.Commit,
    exp.Rollback,
)


class SQLValidator:
    """Validates and sanitizes SQL queries against strict read-only and schema rules."""

    def __init__(
        self,
        schema: Optional[Dict[str, List[str]]] = None,
        default_limit: int = DEFAULT_QUERY_ROW_LIMIT,
        max_limit: int = MAX_QUERY_ROW_LIMIT,
    ):
        """Initialize validator with optional schema map: {table_name: [col1, col2, ...]}.

        Table and column names in schema are normalized to lowercase.
        """
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.schema: Dict[str, Set[str]] = {}
        self.all_columns: Set[str] = set()

        if schema:
            self.set_schema(schema)

    def set_schema(self, schema: Dict[str, List[str]]) -> None:
        """Update allowed schema."""
        self.schema = {
            t.lower().strip(): {c.lower().strip() for c in cols}
            for t, cols in schema.items()
        }
        self.all_columns = {c for cols in self.schema.values() for c in cols}

    def validate(self, sql: str) -> str:
        """Validate, sanitize, and limit a SQL query.

        Args:
            sql: Raw SQL query string.

        Returns:
            Sanitized and normalized SQL query string with LIMIT applied.

        Raises:
            SQLValidationError: If query violates any security or schema rules.
        """
        if not sql or not sql.strip():
            raise SQLValidationError("Query is empty. Please enter a valid question or SQL query.")

        cleaned = sql.strip().rstrip(";")

        # Pre-scan for outright forbidden tokens
        raw_tokens = re.findall(r"\b[A-Za-z_]+\b", cleaned.lower())
        for token in raw_tokens:
            if token in FORBIDDEN_KEYWORDS:
                # Allow 'transaction' only if part of an alias or identifier? No, forbidden keyword
                # Note: 'date', 'month', 'quantity' etc are fine.
                raise SQLValidationError(
                    f"Forbidden SQL keyword detected: '{token.upper()}'. Only read-only SELECT queries are allowed."
                )

        # Parse AST with SQLGlot SQLite dialect
        try:
            parsed = sqlglot.parse(cleaned, read="sqlite")
        except Exception as e:
            raise SQLValidationError(f"SQL Syntax Error: Unable to parse query. ({str(e)})") from e

        if not parsed:
            raise SQLValidationError("Query could not be parsed into valid SQL.")

        # Reject multi-statement queries
        if len(parsed) > 1:
            raise SQLValidationError("Multiple SQL statements detected. Only a single SELECT query is permitted.")

        ast_root = parsed[0]
        if ast_root is None:
            raise SQLValidationError("SQL statement is empty.")

        # Root expression MUST be a Select or Union of Selects
        if not isinstance(ast_root, (exp.Select, exp.Union)):
            raise SQLValidationError(
                f"Disallowed query type '{type(ast_root).__name__}'. Only read-only SELECT queries are permitted."
            )

        # Walk entire AST to ensure no nested forbidden operations exist
        for node in ast_root.walk():
            if isinstance(node, FORBIDDEN_AST_TYPES):
                raise SQLValidationError(
                    f"Disallowed SQL operation '{type(node).__name__}' found in query tree. Only SELECT is permitted."
                )

            # Check function calls for hazardous extension loading
            if isinstance(node, exp.Anonymous):
                fn_name = node.name.lower()
                if fn_name in {"load_extension", "eval", "exec", "system"}:
                    raise SQLValidationError(f"Call to prohibited function '{fn_name}' is not permitted.")

        # Validate tables against schema allowlist if schema is configured
        if self.schema:
            table_aliases = self._extract_table_aliases(ast_root)
            referenced_tables = self._extract_tables(ast_root)

            if not referenced_tables:
                raise SQLValidationError("Query does not reference any database tables.")

            for tbl in referenced_tables:
                if tbl not in self.schema:
                    raise SQLValidationError(
                        f"Unauthorized or unknown table '{tbl}'. Allowed tables: {', '.join(sorted(self.schema.keys()))}."
                    )

            # Validate columns against schema
            self._validate_columns(ast_root, table_aliases)

        # Enforce row limit
        ast_root = self._enforce_limit(ast_root)

        return ast_root.sql(dialect="sqlite")

    def _extract_tables(self, ast_root: exp.Expression) -> Set[str]:
        """Extract all referenced table names, excluding CTE aliases."""
        ctes = set()
        for with_node in ast_root.find_all(exp.CTE):
            ctes.add(with_node.alias.lower())

        tables = set()
        for tbl in ast_root.find_all(exp.Table):
            t_name = tbl.name.lower()
            if t_name and t_name not in ctes:
                tables.add(t_name)
        return tables

    def _extract_table_aliases(self, ast_root: exp.Expression) -> Dict[str, str]:
        """Map table aliases to their real table name."""
        alias_map = {}
        for tbl in ast_root.find_all(exp.Table):
            real_name = tbl.name.lower()
            alias = tbl.alias.lower() if tbl.alias else real_name
            alias_map[alias] = real_name
            alias_map[real_name] = real_name
        return alias_map

    def _validate_columns(self, ast_root: exp.Expression, alias_map: Dict[str, str]) -> None:
        """Validate column names against allowed schema."""
        query_aliases = set()
        for alias_node in ast_root.find_all(exp.Alias):
            query_aliases.add(alias_node.alias.lower())

        for col_node in ast_root.find_all(exp.Column):
            col_name = col_node.name.lower()
            table_qualifier = col_node.table.lower() if col_node.table else None

            # Skip wildcard expressions
            if col_name in {"*", ""}:
                continue

            # Allow if it's an alias defined in the query (e.g. in GROUP BY / ORDER BY)
            if col_name in query_aliases:
                continue

            if table_qualifier:
                real_table = alias_map.get(table_qualifier)
                if real_table and real_table in self.schema:
                    if col_name not in self.schema[real_table]:
                        raise SQLValidationError(
                            f"Unknown column '{col_name}' for table '{real_table}'."
                        )
                elif table_qualifier not in alias_map:
                    raise SQLValidationError(f"Unknown table qualifier or alias '{table_qualifier}'.")
            else:
                # Unqualified column: must exist in at least one referenced schema table
                if col_name not in self.all_columns:
                    raise SQLValidationError(
                        f"Unknown column '{col_name}'. Column not found in any available table."
                    )

    def _enforce_limit(self, ast_root: exp.Expression) -> exp.Expression:
        """Ensure a safe LIMIT clause is attached to the query."""
        if not isinstance(ast_root, exp.Select):
            return ast_root

        existing_limit = ast_root.args.get("limit")
        if existing_limit is None:
            return ast_root.limit(self.default_limit)

        try:
            limit_val = int(existing_limit.expression.this)
            if limit_val > self.max_limit:
                ast_root.set("limit", exp.Limit(expression=exp.Literal.number(self.max_limit)))
        except (ValueError, AttributeError):
            ast_root.set("limit", exp.Limit(expression=exp.Literal.number(self.default_limit)))

        return ast_root


def validate_sql_query(
    sql: str,
    schema: Optional[Dict[str, List[str]]] = None,
    default_limit: int = DEFAULT_QUERY_ROW_LIMIT,
    max_limit: int = MAX_QUERY_ROW_LIMIT,
) -> str:
    """Convenience function to validate a SQL query."""
    validator = SQLValidator(schema=schema, default_limit=default_limit, max_limit=max_limit)
    return validator.validate(sql)
