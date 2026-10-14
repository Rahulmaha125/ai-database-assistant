"""Configuration settings for AI Database Assistant."""

import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DEMO_DB_PATH = DATA_DIR / "demo_sales.db"

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Application Settings
APP_TITLE = "AI Database Assistant"
APP_SUBTITLE = "Ask questions about your data in plain English — No SQL required"

# File Upload Settings
MAX_UPLOAD_SIZE_MB = 25
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_PREVIEW_ROWS = 10

# Query Execution Safety
DEFAULT_QUERY_ROW_LIMIT = 100
MAX_QUERY_ROW_LIMIT = 500
QUERY_TIMEOUT_SECONDS = 10

# Load .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except Exception:
    pass


def get_secret(key: str, default: str = "") -> str:
    """Retrieve secret from Streamlit secrets (for cloud deployment) or environment variable."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return os.getenv(key, default)


# Groq Cloud LLM Settings (Ultra-fast cloud LLM for 24/7 deployment)
GROQ_API_KEY = get_secret("GROQ_API_KEY", "")
DEFAULT_GROQ_MODEL = get_secret("GROQ_MODEL", "qwen/qwen3.8-27b")
GROQ_API_URL = "https://api.groq.com/openai/v1"
SUPPORTED_GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]

# Local LLM Backend Settings
DEFAULT_LLM_PROVIDER = "auto"  # 'auto', 'groq', 'ollama', 'huggingface', 'template_fallback'
DEFAULT_OLLAMA_URL = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
DEFAULT_HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-Coder-0.5B-Instruct")

# SQL Generation
SQL_TEMPERATURE = 0.0
SQL_MAX_NEW_TOKENS = 256

