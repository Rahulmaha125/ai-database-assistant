# AI Database Assistant — Project Specification

## 1. Executive Summary
**AI Database Assistant** bridges the gap between ordinary business users and complex relational databases. It translates questions formulated in natural English into safe, validated SQLite queries, executes them against preloaded demo data or user-uploaded spreadsheets, and presents real results alongside factual summaries and interactive charts.

---

## 2. System Architecture

The application adopts a modular 5-tier architecture:

```
[ User (Web Browser) ]
           │
           ▼
[ Presentation Layer (Streamlit app.py) ]
           │
           ├──► [ LLM Layer (Ollama / HuggingFace / Fallback) ] ─── (Generates Candidate SQL)
           │
           ├──► [ Security Layer (SQLGlot AST Validator) ] ──────── (Inspects & Clamps SQL)
           │
           ├──► [ Database Layer (SQLite with URI ro & PRAGMA) ] ── (Executes Query)
           │
           └──► [ Services (DataFrame Formatter & Plotly Charts) ]─ (Returns Tables & Charts)
```

---

## 3. Database Specifications

### 3.1 Demo Database Schema
Located at `data/demo_sales.db`.

1. **`products` Table:**
   - `product_id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `product_name` TEXT NOT NULL
   - `category` TEXT NOT NULL
   - `unit_price` REAL NOT NULL
   - `stock_quantity` INTEGER NOT NULL

2. **`customers` Table:**
   - `customer_id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `customer_name` TEXT NOT NULL
   - `city` TEXT NOT NULL

3. **`sales` Table:**
   - `sale_id` INTEGER PRIMARY KEY AUTOINCREMENT
   - `product_id` INTEGER NOT NULL (FK -> `products.product_id`)
   - `customer_id` INTEGER NOT NULL (FK -> `customers.customer_id`)
   - `quantity` INTEGER NOT NULL
   - `sale_date` TEXT NOT NULL (ISO 8601 `YYYY-MM-DD`)
   - `total_amount` REAL NOT NULL

### 3.2 Dynamic Upload Schema
- Each uploaded `.csv` or `.xlsx` file is converted into an isolated SQLite database file under `data/uploads/workspace_<uuid>.db`.
- The table name is derived from the sanitized file stem.
- Columns are cleaned, stripped of spaces and invalid symbols, and deduplicated.
- Data types are automatically mapped to SQLite affinity (`INTEGER`, `REAL`, `TEXT`).

---

## 4. Query Engine & Security Rules

1. **Single Statement Enforcement:** Rejects inputs with multiple semicolons or multi-statement ASTs.
2. **Read-Only Operation Restriction:** Allows solely `exp.Select` and `exp.Union` root AST expressions.
3. **Forbidden Keywords:** Rejects `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `ATTACH`, `DETACH`, `PRAGMA`, `LOAD_EXTENSION`, etc.
4. **Schema Allowlists:** Validates all table and column identifiers against introspected schema.
5. **LIMIT Clause Enforced:** Automatically injects `LIMIT 100` if none exists; clamps existing limits to a maximum of `500`.
6. **SQLite Connection Lockdown:**
   - Opened using `file:<path>?mode=ro` URI.
   - Enforces `PRAGMA query_only = ON;`.

---

## 5. Local Model Integration

- **Primary Provider:** Ollama local server (`http://localhost:11434`), model `qwen2.5-coder:1.5b`.
- **Secondary Provider:** In-memory Hugging Face Transformers pipeline (`Qwen/Qwen2.5-Coder-0.5B-Instruct`).
- **Offline / Fallback:** Evaluates against verified demo question templates with explicit attribution. Never pretends that a fallback is an LLM.

---

## 6. Result & Visualization Handling

- Results are structured as pandas DataFrames and rendered with Streamlit.
- Plain-English summarizer produces deterministic interpretations (e.g. single scalar, top ranked, or row counts).
- Plotly chart engine automatically renders bar, line, or scatter plots whenever data contains plottable numeric and categorical/date dimensions.
- Download button provides raw UTF-8 CSV exports.
