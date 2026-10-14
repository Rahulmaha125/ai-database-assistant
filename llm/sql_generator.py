"""Prompt building and robust SQL extraction from LLM outputs."""

import re
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def extract_sql_from_response(raw_text: str) -> str:
    """Extract clean SQL statement from LLM output, removing reasoning, markdown, and chatter.

    Args:
        raw_text: Raw generation output from LLM.

    Returns:
        Cleaned SQL string, or empty string if no valid SQL found.
    """
    if not raw_text or not raw_text.strip():
        return ""

    text = raw_text.strip()

    # 1. Strip <think>...</think> reasoning blocks (e.g. from DeepSeek / Qwen thinking models)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    # 2. Extract from markdown code fences: ```sql ... ``` or ``` ... ```
    code_block_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if code_block_match:
        text = code_block_match.group(1).strip()

    # 3. If raw text contains "SELECT", find the start of the SELECT statement
    select_idx = text.upper().find("SELECT")
    if select_idx != -1:
        text = text[select_idx:]

    # 4. Truncate at the first semicolon or explanation marker
    semicolon_idx = text.find(";")
    if semicolon_idx != -1:
        text = text[:semicolon_idx + 1]

    # Remove any trailing explanatory paragraphs if no semicolon was present
    lines = text.splitlines()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Stop if an explanation marker is encountered
        if stripped.lower().startswith(("note:", "explanation:", "this query", "where ", "here is")):
            # Only stop if it's not a SQL clause
            if not stripped.upper().startswith("WHERE "):
                break
        clean_lines.append(line)

    sql_candidate = "\n".join(clean_lines).strip()
    return sql_candidate


class SQLGenerator:
    """Constructs prompts and orchestrates LLM SQL generation."""

    SYSTEM_PROMPT = """You are an expert SQLite database engineer.
Your task is to convert the user's natural language question into a single, valid, read-only SQLite SELECT query.

RULES:
1. Output ONLY the SQLite SELECT query. Do not wrap in markdown quotes. Do not add explanations or conversational filler.
2. Only use the tables and columns provided in the schema. Do not invent tables or columns.
3. NEVER produce INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH, DETACH, or PRAGMA statements.
4. Always qualify column names with table names or aliases when joining tables.
5. Use standard SQLite functions (e.g., strftime, ROUND, COUNT, SUM, AVG, MIN, MAX).
6. When answering questions regarding min, max, lowest, highest, or rankings, include both the identifying column (e.g. product_name) and the metric column (e.g. stock_quantity) in the SELECT clause.
"""

    @classmethod
    def build_prompt(cls, question: str, schema_text: str) -> str:
        """Construct full prompt for the LLM."""
        return f"""{cls.SYSTEM_PROMPT}

{schema_text}

User Question: "{question}"

SQLite Query:"""
