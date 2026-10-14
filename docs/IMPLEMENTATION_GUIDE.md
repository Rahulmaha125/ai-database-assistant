# AI Database Assistant — Implementation & Developer Guide

## 1. Development Environment Setup (Windows)

### 1.1 Python Virtual Environment
Use Python 3.12 (or 3.11) with 64-bit architecture:

```powershell
# Open terminal in project root
py -3.12 -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 1.2 Verification
Verify the setup by executing:
```powershell
python -m pytest -v
```

---

## 2. Module Tour & Code Responsibilities

### `app.py`
The Streamlit front-end. Manages:
- Active state (`data_mode`: 'demo' vs 'upload').
- File upload drag-and-drop widget.
- Sidebar diagnostics for Ollama and hardware status.
- Session chat history and interactive question triggers.
- Plotly charts and CSV export triggers.

### `config.py`
Global constants and parameters:
- `BASE_DIR`, `DATA_DIR`, `UPLOADS_DIR`, `DEMO_DB_PATH`.
- Safety thresholds: `DEFAULT_QUERY_ROW_LIMIT` (100), `MAX_QUERY_ROW_LIMIT` (500), `QUERY_TIMEOUT_SECONDS` (10).
- File upload constraints: `MAX_UPLOAD_SIZE_MB` (25 MB), `ALLOWED_EXTENSIONS`.

### `db/database.py`
Encapsulates SQLite interactions:
- `get_connection()`: Configures read-only mode using SQLite URIs and `PRAGMA query_only = ON;`.
- `execute_query()`: Runs queries with row truncation and timing.
- `get_database_schema_dict()`: Introspects table columns and primary keys.

### `db/init_db.py`
Seeds the demo database repeatably:
- `products`: 12 items with categories, prices, and stock numbers.
- `customers`: 12 records with customer names and cities.
- `sales`: 28 transactions across multiple months with foreign keys.
- Ensures no duplicated rows on application restart.

### `security/sql_validator.py`
The security gatekeeper:
- Parses SQL strings into an AST using SQLGlot (SQLite dialect).
- Rejects non-`SELECT` statements and non-approved keywords.
- Enforces table and column allowlists.
- Injects or clamps `LIMIT` clauses.

### `services/file_processor.py`
Handles arbitrary file uploads:
- Parses `.csv` and `.xlsx` via pandas and openpyxl.
- Automatically renames duplicate column headers and sanitizes symbols.
- Infers SQLite types (`INTEGER`, `REAL`, `TEXT`).
- Generates an isolated SQLite database file under `data/uploads/`.

### `services/schema_builder.py`
Constructs contextual DDL and samples for LLM prompts:
- Formats table and column names with data types.
- Extracts distinct sample values from the database to improve model understanding.

### `services/query_service.py`
Orchestrator tying together validation, execution, formatting, and charting:
- Catches errors and returns structured `QueryResult` objects.

---

## 3. Extending the Application

### 3.1 Adding a New Local Model
To configure a different model in Ollama:
1. Run `ollama pull <model-name>` (e.g. `ollama pull deepseek-coder:1.3b` or `ollama pull duckdb-nsql:7b`).
2. In `app.py` sidebar, enter the model name in "AI Connection Settings" and click "Apply".

### 3.2 Adding Pre-verified Questions
To add more default clickable questions for the demo database, append to `DEMO_QUESTIONS` in `db/init_db.py`:
```python
DEMO_QUESTIONS.append({
    "question": "Which category generated the highest total revenue?",
    "sql": "SELECT p.category, ROUND(SUM(s.total_amount), 2) AS revenue FROM sales s JOIN products p ON s.product_id = p.product_id GROUP BY p.category ORDER BY revenue DESC LIMIT 1;",
    "description": "Calculates top category by sales revenue.",
})
```

---

## 4. Troubleshooting on Windows

| Problem | Cause | Solution |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'streamlit'` | Virtual environment not activated | Run `.\.venv\Scripts\activate` before launching. |
| `Connection timed out` on Ollama | Ollama daemon not running | Launch Ollama from the Windows Start menu or run `ollama serve`. |
| `FileProcessingError: Unsupported file type` | Non-supported format uploaded | Convert the file to standard `.csv` or `.xlsx` format. |
| Streamlit port conflicts | Port 8501 is busy | Run `streamlit run app.py --server.port 8502`. |
