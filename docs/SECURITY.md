# Security Architecture & Threat Model — AI Database Assistant

## 1. Threat Model & Untrusted Model Philosophy

Large Language Models (LLMs) are probabilistic generative models that can:
1. Hallucinate SQL statements that violate schema constraints.
2. Produce dangerous data modification queries (`DELETE`, `DROP`, `UPDATE`, `INSERT`).
3. Attempt administrative operations (`ATTACH`, `PRAGMA`, `LOAD_EXTENSION`).
4. Fall victim to prompt injection or user jailbreaks designed to exfiltrate database metadata or read unauthorized files.

Therefore, **all output from the LLM is treated as untrusted, potentially malicious input**.

---

## 2. Multi-Layer Defense in Depth

The application implements defense in depth across 4 distinct boundaries:

```
[ Natural Language Question ]
             │
             ▼
┌──────────────────────────────────────────────┐
│ Layer 1: Prompt Constraints & Sanitization   │
│ - Strict system prompt                       │
│ - Regex extraction of SELECT statement       │
└──────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│ Layer 2: SQLGlot AST Structural Validation   │
│ - Reject multi-statement queries             │
│ - Root expression MUST be exp.Select         │
│ - AST walk rejects forbidden nodes           │
│ - Forbidden keywords list                    │
└──────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│ Layer 3: Strict Schema Allowlisting          │
│ - Reject queries accessing unknown tables    │
│ - Reject queries accessing unknown columns   │
│ - Mandatory LIMIT clause injection / clamp   │
└──────────────────────────────────────────────┘
             │
             ▼
┌──────────────────────────────────────────────┐
│ Layer 4: SQLite Engine-Level Read-Only Lock  │
│ - Connection URI: file:<path>?mode=ro        │
│ - PRAGMA query_only = ON;                    │
│ - Execution timeout (10 seconds)             │
│ - Tenant workspace isolation                 │
└──────────────────────────────────────────────┘
```

---

## 3. Detailed Validation Rules

### 3.1 Prohibited Keywords & Commands
The following tokens and AST operations are categorically rejected:
- Data Modification: `INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `TRUNCATE`
- DDL Operations: `DROP`, `ALTER`, `CREATE`, `REINDEX`, `VACUUM`
- Administrative / System: `ATTACH`, `DETACH`, `PRAGMA`, `LOAD_EXTENSION`, `SAVEPOINT`, `TRANSACTION`

### 3.2 Schema Protection
Every table and column referenced in the query is cross-checked against the active database schema:
- If an attacker asks for `SELECT * FROM sqlite_master;`, the validator rejects it because `sqlite_master` is not in the allowed user schema.
- If a query attempts to read unapproved tables (e.g. `users`, `passwords`), it is rejected immediately before execution.

### 3.3 Resource Exhaustion Protections
- **Row Limits:** Queries without a `LIMIT` clause automatically receive `LIMIT 100`. Queries requesting `LIMIT > 500` are clamped to `500`.
- **Query Timeout:** SQLite connection locks are enforced with a 10-second timeout.
- **Upload File Size:** Restricted to a maximum of 25 MB.

### 3.4 Workspace Isolation
Uploaded files are converted into distinct, temporary SQLite databases with UUID-based filenames (`data/uploads/workspace_<uuid>.db`). Different uploads never share database connections or tables.
