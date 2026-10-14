"""UI AppTest verifying Groq status rendering in navigation bar and settings."""

import sys
from pathlib import Path
from streamlit.testing.v1 import AppTest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def test_app_renders_with_groq_cloud():
    """Verify app.py initializes and renders cleanly with Groq Cloud configuration."""
    at = AppTest.from_file(str(PROJECT_ROOT / "app.py"), default_timeout=30)
    at.run()
    assert not at.exception
    # Check that session state has groq_api_key initialized
    assert "groq_api_key" in at.session_state
    assert "groq_model" in at.session_state
    assert at.session_state.groq_model == "qwen/qwen3.8-27b"
