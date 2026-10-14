"""Database access and initialization package."""

from .database import (
    get_connection,
    execute_query,
    get_table_names,
    get_table_schema,
    get_database_schema_dict,
)
from .init_db import initialize_demo_database, DEMO_QUESTIONS

__all__ = [
    "get_connection",
    "execute_query",
    "get_table_names",
    "get_table_schema",
    "get_database_schema_dict",
    "initialize_demo_database",
    "DEMO_QUESTIONS",
]
