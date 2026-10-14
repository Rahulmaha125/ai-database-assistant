# AI Database Assistant — Master Blueprint & Coding Agent Reference

## Mission Overview
Build a beginner-friendly, secure, modular AI Database Assistant in Python 3.12 and Streamlit that translates natural-language questions into SQL, runs against preloaded demo data or user-uploaded Excel/CSV files, and presents factual results with charts and CSV exports.

---

## Architectural Principles

1. **Deterministic Execution:** The LLM only suggests SQL queries. Python and SQLGlot validate the SQL syntax and security boundaries, and SQLite executes the calculation against real data. The LLM never touches disk or executes SQL directly.
2. **Never Fabricate Answers:** If data is missing or a question cannot be answered by the available columns, explain the limitation clearly. Never invent numbers.
3. **No Mandatory Paid APIs:** Designed to run 100% locally using open-source models (Ollama / Hugging Face) or graceful offline templates.
4. **Hardware Awareness:** Works cleanly on standard laptops (8GB RAM) without memory overflow or freezing.
5. **Windows Native:** All commands, paths, and URI formats are tested and compatible with Windows PowerShell and command prompts.

---

## Acceptance Criteria Checklist

- [x] Streamlit web application with Demo and Upload modes.
- [x] Repeatable demo database seeder (`products`, `customers`, `sales`).
- [x] Robust file upload pipeline supporting `.csv` and `.xlsx` with column sanitization and type inference.
- [x] AST-based SQL validation using SQLGlot with SQLite dialect.
- [x] Strict read-only SQLite execution with `mode=ro` and `PRAGMA query_only = ON`.
- [x] LIMIT clause enforcement (default 100, max 500).
- [x] Modular local LLM manager with Ollama support and safe offline fallback.
- [x] Plain-English factual summaries, Plotly charts, and CSV exports.
- [x] Full automated test suite (48 tests) covering security, database, upload, and integration.
- [x] Complete documentation: README, Specification, Implementation Guide, and Security Model.
