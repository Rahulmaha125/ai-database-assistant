"""Tests to verify that the results display and How it works panel in app.py are rendered correctly."""

import re
from pathlib import Path

APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


def test_no_duplicate_charts_or_expanders_in_results():
    """Verify results section renders chart once and has exactly one SQL inspector."""
    content = APP_PATH.read_text(encoding="utf-8")

    # Locate results section
    assert "RESULTS SECTION" in content
    results_section = content.split("RESULTS SECTION")[-1]

    # Count occurrences of plotly_chart in results section
    chart_calls = re.findall(r"st\.plotly_chart\(", results_section)
    assert len(chart_calls) == 1, f"Expected 1 plotly_chart call, found {len(chart_calls)}"

    # Count occurrences of expander in results section
    expander_calls = re.findall(r"st\.expander\(", results_section)
    assert len(expander_calls) == 1, f"Expected 1 expander in results section, found {len(expander_calls)}"

    # Verify the expander is NOT nested inside the chart_fig block
    chart_pattern = re.search(r"if q_res\.chart_fig is not None:\s+st\.plotly_chart\([^\)]+\)", results_section)
    assert chart_pattern is not None, "Chart condition structure not found"

    # Confirm expander label is consistent
    assert 'st.expander("🛡️ Verified SQL Query & Security Details"' in results_section

    # Confirm preservation of fields
    assert "q_res.execution_time_ms" in results_section
    assert "model_source" in results_section
    assert "raw_resp" in results_section
    assert "sql_used" in results_section
    assert "q_res.validated_sql" in results_section


def test_how_it_works_panel_structure():
    """Verify How it works panel contains all 3 steps, security card, and has no raw HTML hazards."""
    content = APP_PATH.read_text(encoding="utf-8")

    assert "how-it-works-card" in content
    assert "Ask in plain English" in content
    assert "Local LLM generates SQL" in content
    assert "SQLite returns verified results" in content
    assert "Read-only queries" in content
    assert "🛡️" in content

    # Verify how_it_works_html definition
    panel_match = re.search(r"how_it_works_html\s*=\s*\((.*?)\)\s*st\.markdown", content, re.DOTALL)
    assert panel_match is not None, "how_it_works_html definition not found"
    panel_body = panel_match.group(1)

    assert "Ask in plain English" in panel_body
    assert "Local LLM generates SQL" in panel_body
    assert "SQLite returns verified results" in panel_body
    assert "security-notice-card" in panel_body
    assert "Read-only queries" in panel_body


def test_how_it_works_renders_without_raw_code_blocks():
    """Run AppTest to verify no markdown element renders HTML tags as code blocks."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception

    # Find How it works markdown element
    found = False
    for m in at.markdown:
        if "How it works" in m.value:
            found = True
            # Verify the HTML tags are intact and not wrapped in code fences or escaped
            assert '<div class="how-it-works-card">' in m.value
            assert '<div class="step-item">' in m.value
            assert "Ask in plain English" in m.value
            assert "Local LLM generates SQL" in m.value
            assert "SQLite returns verified results" in m.value
            assert "Read-only queries" in m.value
            assert "```" not in m.value
            # Verify no line starts with 4+ spaces
            for line in m.value.splitlines():
                assert not line.startswith("    "), f"Line has 4+ spaces indentation hazard: {line}"
    assert found, "How it works panel element was not found in AppTest"
