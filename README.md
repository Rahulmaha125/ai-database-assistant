# 📊 AI Database Assistant

**AI Database Assistant** is a desktop and web-ready data application that allows ordinary users to ask questions about relational data in plain English — without knowing SQL or database programming.

Powered by a local, open-source AI engine, AST-level SQL validation with [SQLGlot](https://github.com/tobymao/sqlglot), and SQLite, it guarantees that queries are safe, read-only, and factually grounded in real data.

---

## 🌟 Key Features

1. **🚀 Try Demo Database:**
   - Preloaded with a fictional retail catalog: `products`, `customers`, and `sales`.
   - Clickable questions like *"Which product has the lowest stock?"* and *"Show monthly sales totals"*.
   - Zero setup required: works right out of the box with zero external dependencies.

2. **📁 Upload My File (Excel & CSV):**
   - Upload any `.csv` or `.xlsx` spreadsheet (employees, expenses, inventory, sales, students, etc.).
   - Automatic column deduplication, identifier sanitization, and data type inference.
   - Isolated temporary SQLite workspace per upload for data privacy.

3. **🛡️ Rock-Solid SQL Security:**
   - Treats all model-generated SQL as untrusted.
   - AST validation using SQLGlot: permits **only** single `SELECT` statements.
   - Rejects `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `ATTACH`, `DETACH`, `PRAGMA`, and multi-statement injection.
   - Enforces schema allowlisting (rejects queries targeting unapproved tables or columns).
   - SQLite engine-level read-only mode (`PRAGMA query_only = ON` and URI `mode=ro`).
   - Automatic `LIMIT` row clamping (default 100, max 500).

4. **📈 Plain-English Summaries & Visualizations:**
   - Real query results displayed in an interactive data table.
   - Deterministic factual summary without AI hallucination.
   - Automatic interactive charts using Plotly (bar charts, line charts, time-series).
   - One-click CSV export of query results.
   - Expandable SQL inspector showing the generated SQL, execution time, and security status.

5. **🤖 Flexible Local LLM Options:**
   - **Ollama (Recommended):** Connects to `http://localhost:11434` running models like `qwen2.5-coder:1.5b` or `llama3.2:1b`.
   - **Hugging Face Transformers:** CPU/GPU pipeline support for lightweight open models (`Qwen2.5-Coder-0.5B-Instruct`).
   - **Safe Offline / Template Mode:** If no LLM is running, the app runs verified demo question templates and explains the setup steps without pretending to be an AI.

---

## 💻 Quickstart on Windows

### 1. Prerequisites
- Windows 10 or 11 (64-bit)
- Python 3.11 or 3.12 (Python 3.12 recommended)

### 2. Create and Activate Virtual Environment
Open PowerShell in the project directory:

```powershell
# Create virtual environment with Python 3.12
py -3.12 -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### 4. Initialize Demo Database
```powershell
python db/init_db.py
```

### 5. Run Automated Tests
```powershell
python -m pytest -v
```

### 6. Launch the Application
```powershell
streamlit run app.py
```
Streamlit will automatically open your browser at `http://localhost:8501`.

---

## 🤖 Optional: Setting Up Local Ollama AI

To ask custom, arbitrary natural-language questions with a local open-source LLM:

1. Download and install Ollama from [ollama.com](https://ollama.com).
2. Open PowerShell and run:
   ```powershell
   ollama run qwen2.5-coder:1.5b
   ```
   *(Requires ~1.2 GB download; runs fast even on standard 8GB RAM laptops).*
3. Open or refresh the **AI Database Assistant** app in your browser. The sidebar badge will turn green: `● Online (OLLAMA)`.

---

## 📂 Project Directory Structure

```text
AI_Database_Assistant/
│
├── app.py                      # Main Streamlit web application
├── config.py                   # Central configuration & safety limits
├── requirements.txt            # Python package dependencies
├── README.md                   # This overview guide
├── .gitignore                  # Git exclusion rules
│
├── db/                         # Database layer
│   ├── __init__.py
│   ├── init_db.py              # Demo database seeder & schema creator
│   └── database.py             # SQLite connection, URI ro mode, introspection
│
├── llm/                        # Local LLM and prompt engineering
│   ├── __init__.py
│   ├── model_manager.py        # Ollama, HuggingFace & safe offline fallback manager
│   └── sql_generator.py        # Prompt builder & SQL regex/markdown extractor
│
├── security/                   # Untrusted SQL validation
│   ├── __init__.py
│   └── sql_validator.py        # SQLGlot AST parser, schema allowlist & LIMIT injector
│
├── services/                   # Application business logic
│   ├── __init__.py
│   ├── file_processor.py       # Excel/CSV parser, type inference & isolated storage
│   ├── schema_builder.py       # Schema DDL formatting & sample value extractor
│   ├── query_service.py        # Query orchestrator (validate -> execute -> format)
│   ├── result_formatter.py     # DataFrame conversion, CSV export & factual summary
│   └── chart_service.py        # Plotly chart detection and renderer
│
├── tests/                      # Automated test suite (48 tests)
│   ├── test_sql_validator.py   # Security AST and keyword rejection tests
│   ├── test_database.py        # SQLite schema and read-only tests
│   ├── test_file_processor.py  # CSV/Excel parsing and edge case tests
│   ├── test_query_service.py   # Query execution and formatting tests
│   ├── test_sql_generator.py   # SQL extraction and model manager tests
│   └── test_integration.py     # End-to-end demo and upload workflows
│
├── data/                       # Local data storage
│   ├── demo_sales.db           # SQLite demo retail database
│   └── uploads/                # Isolated uploaded temporary SQLite databases
│
└── docs/                       # In-depth architectural documentation
    ├── PROJECT_SPECIFICATION.md
    ├── IMPLEMENTATION_GUIDE.md
    ├── SECURITY.md
    └── AI_CODING_AGENT_PROMPT.md
```

---

## 🧪 Running the Tests

To run the complete automated test suite:

```powershell
python -m pytest -v
```

All 48 tests verify:
- Valid SELECT queries, aggregations, filters, joins, and group by clauses.
- Immediate rejection of `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, and `PRAGMA`.
- Multi-statement SQL rejection.
- Access to unapproved tables and columns rejection.
- CSV and Excel file parsing, duplicate headers, and empty files.
- Safe offline fallback when no LLM is running.
- End-to-end integration workflows.

---

## 🔒 Security Architecture Highlights

- **Untrusted Input Philosophy:** Every candidate query from the AI is treated as potentially adversarial.
- **SQLGlot AST Parsing:** Bypasses simple regex flaws by verifying the actual syntax tree.
- **SQLite Engine Read-Only Mode:** Every query execution uses `mode=ro` SQLite URIs and executes `PRAGMA query_only = ON;`.
- **Tenant Isolation:** Uploaded files are converted into unique UUID-named SQLite databases and never intermingled.
