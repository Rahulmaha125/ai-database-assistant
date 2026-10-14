"""AI Database Assistant — Premium SaaS Dashboard.

Redesigned modern user interface inspired by SaaS data platforms.
Features:
- Dark navy sidebar with iconography and live Ollama connection status.
- Top breadcrumb and status header bar.
- Action cards for Demo Database and Excel/CSV Upload.
- Popular question shortcut cards.
- Natural-language query input with 'Ask AI' trigger.
- Live dataset statistics cards (Products, Customers, Sales / Uploaded metrics).
- 'How it works' timeline & security guarantee card.
- Interactive results table, Plotly visualizations, CSV download, and AST SQL inspector.
"""

import os
import sys
from pathlib import Path
import streamlit as st
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import (
    APP_SUBTITLE,
    APP_TITLE,
    DEFAULT_GROQ_MODEL,
    DEFAULT_HF_MODEL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    DEMO_DB_PATH,
    GROQ_API_KEY,
    MAX_UPLOAD_SIZE_MB,
    SUPPORTED_GROQ_MODELS,
)
from db.database import execute_query, get_database_schema_dict, get_table_names
from db.init_db import DEMO_QUESTIONS, initialize_demo_database
from llm.model_manager import LLMManager, LLMStatus
from security.sql_validator import SQLValidationError
from services.chart_service import ChartService
from services.file_processor import FileProcessingError, FileProcessor, UploadResult
from services.query_service import QueryResult, QueryService
from services.result_formatter import ResultFormatter
from services.schema_builder import SchemaBuilder


# Streamlit Page Configuration
st.set_page_config(
    page_title=f"{APP_TITLE} — Modern AI Data Workspace",
    page_icon="🗄️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End SaaS Styling (Matching Dark Navy Sidebar & Clean White Cards Mockup)
st.markdown(
    """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #0F172A;
    }

    /* Main background */
    .stApp {
        background-color: #F8FAFC;
    }

    /* Hide standard Streamlit header clutter */
    header[data-testid="stHeader"] {
        background-color: rgba(248, 250, 252, 0.8) !important;
        backdrop-filter: blur(8px);
    }
    #MainMenu, footer { visibility: hidden; }

    /* Dark Navy Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0B192C !important;
        color: #F8FAFC !important;
        border-right: 1px solid #1E293B;
    }
    [data-testid="stSidebar"] .stMarkdown, 
    [data-testid="stSidebar"] p, 
    [data-testid="stSidebar"] span, 
    [data-testid="stSidebar"] label {
        color: #94A3B8 !important;
    }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {
        color: #FFFFFF !important;
    }

    /* Sidebar Logo Header */
    .sidebar-brand {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 4px 20px 4px;
        border-bottom: 1px solid #1E293B;
        margin-bottom: 20px;
    }
    .sidebar-brand-icon {
        width: 38px;
        height: 38px;
        background: linear-gradient(135deg, #2563EB, #38BDF8);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: white;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35);
    }
    .sidebar-brand-text {
        font-size: 1.15rem;
        font-weight: 800;
        color: #FFFFFF !important;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }

    /* Navigation Radio Items in Sidebar */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 6px;
    }
    [data-testid="stSidebar"] .stRadio label {
        padding: 10px 14px !important;
        border-radius: 10px !important;
        transition: all 0.2s ease !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        color: #94A3B8 !important;
        cursor: pointer !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background-color: #1E293B !important;
        color: #F8FAFC !important;
    }
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] + div {
        background-color: #1E293B !important;
        color: #FFFFFF !important;
        font-weight: 700 !important;
    }

    /* Sidebar Model Connection Card at Bottom */
    .sidebar-connection-card {
        background: #0F172A;
        border: 1px solid #1E293B;
        border-radius: 12px;
        padding: 14px 16px;
        margin-top: 25px;
    }
    .sidebar-conn-status {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .status-dot-green {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #10B981;
        box-shadow: 0 0 8px #10B981;
    }
    .status-dot-red {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #EF4444;
        box-shadow: 0 0 8px #EF4444;
    }

    /* Top Breadcrumb & Navbar */
    .top-navbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0 24px 0;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 24px;
        flex-wrap: wrap;
        gap: 12px;
    }
    .breadcrumbs {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.9rem;
        color: #64748B;
        font-weight: 500;
    }
    .breadcrumbs strong {
        color: #0F172A;
    }
    .top-badges {
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .top-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ECFDF5;
        border: 1px solid #A7F3D0;
        color: #065F46;
        padding: 6px 14px;
        border-radius: 9999px;
        font-size: 0.8rem;
        font-weight: 700;
    }
    .top-model-box {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        padding: 5px 12px;
        border-radius: 8px;
        font-size: 0.82rem;
        color: #475569;
        font-weight: 500;
    }
    .top-avatar {
        width: 34px;
        height: 34px;
        border-radius: 50%;
        background: #2563EB;
        color: white;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 700;
        font-size: 0.85rem;
    }

    /* Hero Headers */
    .hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #0F172A;
        margin-bottom: 6px;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 24px;
        font-weight: 400;
    }

    /* Big Action Cards (Demo vs Upload) */
    .action-card {
        background: #FFFFFF;
        border-radius: 16px;
        padding: 24px;
        transition: all 0.25s ease;
        display: flex;
        justify-content: space-between;
        align-items: center;
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .action-card-demo {
        border: 1px solid #BFDBFE;
    }
    .action-card-demo:hover {
        border-color: #3B82F6;
        box-shadow: 0 10px 25px -5px rgba(59, 130, 246, 0.15);
    }
    .action-card-upload {
        border: 1px solid #BBF7D0;
    }
    .action-card-upload:hover {
        border-color: #10B981;
        box-shadow: 0 10px 25px -5px rgba(16, 185, 129, 0.15);
    }
    .card-icon-box-blue {
        width: 52px;
        height: 52px;
        background: #EFF6FF;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        color: #2563EB;
        margin-bottom: 12px;
    }
    .card-icon-box-green {
        width: 52px;
        height: 52px;
        background: #F0FDF4;
        border-radius: 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 26px;
        color: #16A34A;
        margin-bottom: 12px;
    }
    .card-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .card-desc {
        font-size: 0.88rem;
        color: #64748B;
        margin-bottom: 14px;
        line-height: 1.4;
    }
    .card-pill-blue {
        display: inline-block;
        background: #EFF6FF;
        color: #2563EB;
        border: 1px solid #DBEAFE;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .card-pill-green {
        display: inline-block;
        background: #F0FDF4;
        color: #16A34A;
        border: 1px solid #DCFCE7;
        padding: 3px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .arrow-icon {
        font-size: 20px;
        font-weight: bold;
        color: #2563EB;
    }

    /* Popular Questions Buttons */
    .stButton > button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .question-btn > button {
        background: #FFFFFF !important;
        color: #1E293B !important;
        border: 1px solid #E2E8F0 !important;
        text-align: left !important;
        justify-content: space-between !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
        padding: 14px 18px !important;
    }
    .question-btn > button:hover {
        border-color: #3B82F6 !important;
        background: #F8FAFC !important;
        box-shadow: 0 4px 12px rgba(59, 130, 246, 0.1) !important;
    }

    /* Query Box Card */
    .query-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        margin-top: 10px;
        margin-bottom: 24px;
    }
    .query-card-header {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.05rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 12px;
    }

    /* Dataset Metric Statistics Cards */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px 20px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .metric-icon-box {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }
    .metric-val {
        font-size: 1.65rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
        margin-bottom: 2px;
    }

    /* How it Works Panel (Right Column) */
    .how-it-works-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
    }
    .how-it-works-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 1.15rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 20px;
    }
    .step-item {
        display: flex;
        gap: 14px;
        position: relative;
        padding-bottom: 24px;
    }
    .step-item:last-child {
        padding-bottom: 12px;
    }
    .step-line {
        position: absolute;
        left: 15px;
        top: 32px;
        bottom: 0px;
        width: 2px;
        border-left: 2px dotted #CBD5E1;
    }
    .step-num {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background: #EFF6FF;
        color: #2563EB;
        border: 2px solid #DBEAFE;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 0.9rem;
        flex-shrink: 0;
        z-index: 2;
    }
    .step-content-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 3px;
    }
    .step-content-desc {
        font-size: 0.82rem;
        color: #64748B;
        line-height: 1.4;
    }
    .security-notice-card {
        background: #F0FDF4;
        border: 1px solid #BBF7D0;
        border-radius: 12px;
        padding: 14px;
        display: flex;
        gap: 12px;
        margin-top: 10px;
    }

    /* Query Result Display */
    .result-banner {
        background: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        padding: 24px;
        margin-top: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .summary-box {
        background: #F8FAFC;
        border-left: 4px solid #2563EB;
        padding: 14px 18px;
        border-radius: 8px;
        font-size: 1rem;
        color: #1E293B;
        margin-bottom: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_html(html_str: str) -> None:
    """Render HTML safely without triggering Markdown indented code block parsing."""
    cleaned = "".join(line.strip() for line in html_str.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "nav_view" not in st.session_state:
        st.session_state.nav_view = "Overview"

    if "data_mode" not in st.session_state:
        st.session_state.data_mode = "demo"  # 'demo' or 'upload'

    if "demo_initialized" not in st.session_state:
        initialize_demo_database()
        st.session_state.demo_initialized = True

    if "upload_result" not in st.session_state:
        st.session_state.upload_result = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if "current_question" not in st.session_state:
        st.session_state.current_question = ""

    if "upload_current_question" not in st.session_state:
        st.session_state.upload_current_question = ""

    if "groq_api_key" not in st.session_state:
        st.session_state.groq_api_key = GROQ_API_KEY

    if "groq_model" not in st.session_state:
        st.session_state.groq_model = DEFAULT_GROQ_MODEL

    if "llm_manager" not in st.session_state:
        st.session_state.llm_manager = LLMManager(
            groq_api_key=st.session_state.groq_api_key,
            groq_model=st.session_state.groq_model,
        )

    if "ollama_url" not in st.session_state:
        st.session_state.ollama_url = DEFAULT_OLLAMA_URL

    if "ollama_model" not in st.session_state:
        st.session_state.ollama_model = DEFAULT_OLLAMA_MODEL


init_session_state()

# Live Check of AI Engine (Groq Cloud or Local Ollama)
llm_manager: LLMManager = st.session_state.llm_manager
status: LLMStatus = llm_manager.get_status()


def run_query_flow(question_text: str, db_path: str | Path, schema_dict: dict, prompt_text: str) -> None:
    """Execute the complete AI-to-SQL-to-SQLite workflow and prepend to chat_history."""
    if db_path is None or not Path(db_path).exists():
        st.warning("⚠️ Database file not found. Please upload a CSV/Excel file or initialize the demo database.")
        return

    engine_name = "Groq Cloud" if (status.is_available and status.provider == "groq") else "Local AI Engine"
    with st.spinner(f"⚡ {engine_name} is interpreting question & querying database..."):
        # 1. Real Ollama SQL generation
        gen_res = st.session_state.llm_manager.generate_sql(
            question=question_text,
            schema_text=prompt_text,
            table_columns=schema_dict,
        )

        if gen_res["sql"] is None:
            st.error(f"❌ {gen_res['error']}")
        else:
            candidate_sql = gen_res["sql"]
            model_source = gen_res.get("model", "Local Ollama")
            gen_src = gen_res.get("source", "unknown")
            raw_resp = gen_res.get("raw_response")

            # 2. SQLGlot AST validation & read-only SQLite execution
            qs = QueryService(db_path, schema=schema_dict)
            q_res: QueryResult = qs.execute(candidate_sql, question=question_text)

            # 3. Store in session history
            st.session_state.chat_history.insert(
                0,
                {
                    "question": question_text,
                    "query_result": q_res,
                    "model_source": model_source,
                    "generation_source": gen_src,
                    "raw_response": raw_resp,
                    "sql": candidate_sql,
                },
            )



# =========================================================================
# SIDEBAR NAVIGATION (Dark Navy SaaS Style)
# =========================================================================
with st.sidebar:
    # Sidebar Logo Header
    render_html(
        """
        <div class="sidebar-brand">
            <div class="sidebar-brand-icon">🗄️</div>
            <div class="sidebar-brand-text">AI Database<br>Assistant</div>
        </div>
        """
    )

    # Navigation menu
    nav_options = [
        "🏠  Overview",
        "🗄️  Demo Database",
        "📤  Upload Data",
        "🕒  Query History",
        "⚙️  Settings",
        "❓  Help",
    ]
    # Map label to internal view key
    view_keys = {
        "🏠  Overview": "Overview",
        "🗄️  Demo Database": "Demo Database",
        "📤  Upload Data": "Upload Data",
        "🕒  Query History": "Query History",
        "⚙️  Settings": "Settings",
        "❓  Help": "Help",
    }

    # Find current index
    current_idx = 0
    for idx, opt in enumerate(nav_options):
        if view_keys[opt] == st.session_state.nav_view:
            current_idx = idx
            break

    selected_nav = st.radio(
        "Navigation",
        options=nav_options,
        index=current_idx,
        label_visibility="collapsed",
    )
    selected_view = view_keys[selected_nav]
    if selected_view != st.session_state.nav_view:
        st.session_state.nav_view = selected_view
        st.rerun()

    # Bottom Model Connection Indicator
    st.markdown("<div style='flex-grow: 1; height: 120px;'></div>", unsafe_allow_html=True)
    if status.is_available and status.provider == "groq":
        render_html(
            f"""
            <div class="sidebar-connection-card">
                <div class="sidebar-conn-status" style="color: #10B981;">
                    <div class="status-dot-green"></div> Groq Cloud Online
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 2px;">Model</div>
                <div style="font-size: 0.88rem; color: #FFFFFF; font-weight: 600; font-family: monospace;">{status.model_name}</div>
                <div style="font-size: 0.78rem; color: #64748B; margin-top: 6px; margin-bottom: 2px;">Latency / Mode</div>
                <div style="font-size: 0.8rem; color: #38BDF8; font-weight: 600;">⚡ ~0.5s • 24/7 Cloud Ready</div>
            </div>
            """
        )
    elif status.is_available and status.provider == "ollama":
        render_html(
            f"""
            <div class="sidebar-connection-card">
                <div class="sidebar-conn-status" style="color: #10B981;">
                    <div class="status-dot-green"></div> Ollama Connected
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 2px;">Model</div>
                <div style="font-size: 0.88rem; color: #FFFFFF; font-weight: 600; font-family: monospace;">{status.model_name}</div>
                <div style="font-size: 0.78rem; color: #64748B; margin-top: 6px; margin-bottom: 2px;">Endpoint</div>
                <div style="font-size: 0.8rem; color: #94A3B8; font-family: monospace;">{st.session_state.ollama_url}</div>
            </div>
            """
        )
    elif status.is_available:
        render_html(
            f"""
            <div class="sidebar-connection-card">
                <div class="sidebar-conn-status" style="color: #10B981;">
                    <div class="status-dot-green"></div> AI Engine Online
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 2px;">Model</div>
                <div style="font-size: 0.88rem; color: #FFFFFF; font-weight: 600; font-family: monospace;">{status.model_name}</div>
            </div>
            """
        )
    else:
        render_html(
            f"""
            <div class="sidebar-connection-card">
                <div class="sidebar-conn-status" style="color: #EF4444;">
                    <div class="status-dot-red"></div> AI Backend Offline
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-bottom: 2px;">Groq Cloud / Ollama</div>
                <div style="font-size: 0.76rem; color: #F59E0B; margin-top: 6px;">Add GROQ_API_KEY in Settings or start Ollama locally</div>
            </div>
            """
        )

    # Quick Refresh Button
    if st.button("🔄 Refresh Connection", use_container_width=True):
        st.session_state.llm_manager.get_status(force_refresh=True)
        st.rerun()


# =========================================================================
# TOP NAVIGATION BAR (Breadcrumbs, Status, Model Pill, User Profile)
# =========================================================================
col_nav_left, col_nav_right = st.columns([1, 1])

with col_nav_left:
    render_html(
        f"""
        <div class="breadcrumbs">
            <span>🏠 Workspace</span> <span>/</span> <strong>{st.session_state.nav_view}</strong>
        </div>
        """
    )

with col_nav_right:
    # Model status & user profile on right
    if status.is_available and status.provider == "groq":
        badge_html = f'<span class="top-status-badge" style="background:#ECFDF5; border-color:#A7F3D0; color:#065F46;"><span class="status-dot-green"></span> Groq Cloud Online (24/7)</span>'
        model_name_disp = status.model_name
    elif status.is_available and status.provider == "ollama":
        badge_html = f'<span class="top-status-badge"><span class="status-dot-green"></span> Ollama Connected</span>'
        model_name_disp = status.model_name
    elif status.is_available:
        badge_html = f'<span class="top-status-badge"><span class="status-dot-green"></span> LLM Online</span>'
        model_name_disp = status.model_name
    else:
        badge_html = f'<span class="top-status-badge" style="background:#FEF2F2; border-color:#FECACA; color:#991B1B;"><span class="status-dot-red"></span> Disconnected</span>'
        model_name_disp = "Offline"

    render_html(
        f"""
        <div class="top-badges" style="justify-content: flex-end;">
            {badge_html}
            <div class="top-model-box">
                <span style="color:#94A3B8; font-size:0.75rem;">Model</span>
                <span style="font-family: monospace; font-weight:700; color:#0F172A;">{model_name_disp}</span>
            </div>
            <div class="top-avatar" title="Active User: Rahul">R</div>
        </div>
        """
    )


# Determine Active Database & Schema
if st.session_state.data_mode == "demo":
    active_db_path = DEMO_DB_PATH
    sb = SchemaBuilder(active_db_path)
    active_schema_dict = sb.get_validator_schema()
    schema_prompt_text = sb.build_schema_prompt_text()
    source_title = "Demo Retail Database"
else:
    if st.session_state.upload_result:
        active_db_path = st.session_state.upload_result.db_path
        sb = SchemaBuilder(active_db_path)
        active_schema_dict = sb.get_validator_schema()
        schema_prompt_text = sb.build_schema_prompt_text()
        source_title = f"Uploaded File: {st.session_state.upload_result.file_name}"
    else:
        active_db_path = None
        active_schema_dict = {}
        schema_prompt_text = ""
        source_title = "No file uploaded"


# =========================================================================
# VIEW 1: OVERVIEW DASHBOARD (Exact Match to Visual Mockup)
# =========================================================================
if st.session_state.nav_view == "Overview":
    # Hero Title & Subtitle
    st.markdown('<div class="hero-title">Ask your data anything.</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Get answers from your Excel, CSV, or demo database — no SQL knowledge needed.</div>',
        unsafe_allow_html=True,
    )

    # 2-Column Main Layout (Left 73% Workspace, Right 27% How It Works Panel)
    col_main, col_sidebar_info = st.columns([2.7, 1.0], gap="large")

    with col_main:
        # ROW 1: TWO BIG ACTION CARDS (Try Demo Database vs Upload Excel/CSV)
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            render_html(
                """
                <div class="action-card action-card-demo">
                    <div>
                        <div class="card-icon-box-blue">🗄️</div>
                        <div class="card-title">Try Demo Database</div>
                        <div class="card-desc">Explore with our sample dataset and see how it works.</div>
                        <span class="card-pill-blue">Sample Data</span>
                    </div>
                    <div class="arrow-icon">➔</div>
                </div>
                """
            )
            if st.button("Use Demo Database", key="btn_switch_demo", use_container_width=True):
                st.session_state.data_mode = "demo"
                st.rerun()

        with col_c2:
            render_html(
                """
                <div class="action-card action-card-upload">
                    <div>
                        <div class="card-icon-box-green">📤</div>
                        <div class="card-title">Upload Excel / CSV</div>
                        <div class="card-desc">Upload your own data file (.xlsx, .xls, .csv).</div>
                        <span class="card-pill-green">Supports: XLSX, XLS, CSV</span>
                    </div>
                    <div class="arrow-icon">➔</div>
                </div>
                """
            )
            if st.button("Upload Spreadsheet", key="btn_switch_upload", use_container_width=True):
                st.session_state.data_mode = "upload"
                st.session_state.nav_view = "Upload Data"
                st.rerun()

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        # ROW 2: POPULAR QUESTIONS SHORTCUTS
        st.markdown("##### ⚡ Popular questions")
        row_q1, row_q2 = st.columns(2)

        demo_shortcuts = [
            ("📊  Which product has the lowest stock?", "Which product has the lowest stock?"),
            ("📈  Show monthly sales totals.", "Show monthly sales totals."),
            ("👥  Which city has the most customers?", "Which city has the most customers?"),
            ("🥧  Find the top 5 products by sales.", "Which products sold the highest quantity?"),
        ]

        with row_q1:
            if st.button(demo_shortcuts[0][0], key="pop_q0", use_container_width=True):
                st.session_state.data_mode = "demo"
                st.session_state.current_question = demo_shortcuts[0][1]
                st.session_state["question_input"] = demo_shortcuts[0][1]
                st.rerun()

            if st.button(demo_shortcuts[2][0], key="pop_q2", use_container_width=True):
                st.session_state.data_mode = "demo"
                st.session_state.current_question = demo_shortcuts[2][1]
                st.session_state["question_input"] = demo_shortcuts[2][1]
                st.rerun()

        with row_q2:
            if st.button(demo_shortcuts[1][0], key="pop_q1", use_container_width=True):
                st.session_state.data_mode = "demo"
                st.session_state.current_question = demo_shortcuts[1][1]
                st.session_state["question_input"] = demo_shortcuts[1][1]
                st.rerun()

            if st.button(demo_shortcuts[3][0], key="pop_q3", use_container_width=True):
                st.session_state.data_mode = "demo"
                st.session_state.current_question = demo_shortcuts[3][1]
                st.session_state["question_input"] = demo_shortcuts[3][1]
                st.rerun()

        st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

        # ROW 3: QUESTION INPUT CARD WITH PROMINENT ASK AI BUTTON
        render_html(
            f"""
            <div class="query-card">
                <div class="query-card-header">
                    <span>💬</span> Ask a question about your data <span style="font-size:0.8rem; color:#64748B; font-weight:500;">(Target: <b>{source_title}</b>)</span>
                </div>
            """
        )

        col_input_box, col_btn_box = st.columns([3.8, 1.2])
        with col_input_box:
            user_input = st.text_input(
                "Ask a question in plain English:",
                value=st.session_state.current_question,
                placeholder="Ask a question in plain English...",
                label_visibility="collapsed",
                key="question_input",
            )
        with col_btn_box:
            ask_ai_clicked = st.button("✨ Ask AI →", type="primary", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        # TRIGGER QUERY EXECUTION
        question_to_run = user_input.strip() if user_input.strip() else st.session_state.current_question.strip()
        if (ask_ai_clicked or bool(st.session_state.current_question)) and question_to_run:
            st.session_state.current_question = ""
            user_input = question_to_run

            if active_db_path is None or not Path(active_db_path).exists():
                st.warning("⚠️ Please upload a CSV or Excel file before asking questions in Upload mode.")
            else:
                run_query_flow(
                    question_text=user_input,
                    db_path=active_db_path,
                    schema_dict=active_schema_dict,
                    prompt_text=schema_prompt_text,
                )

        # ROW 4: DATASET STATISTICS CARDS (Dynamic & Real)
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.session_state.data_mode == "demo":
            render_html(
                """
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
                    <h5 style="margin:0; font-weight:700;">🗄️ Demo dataset</h5>
                    <span class="card-pill-green">Sample data for testing</span>
                </div>
                """
            )
            # Query actual row counts from SQLite
            c_prod = execute_query(DEMO_DB_PATH, "SELECT COUNT(*) FROM products;", read_only=True)["rows"][0][0]
            c_cust = execute_query(DEMO_DB_PATH, "SELECT COUNT(*) FROM customers;", read_only=True)["rows"][0][0]
            c_sale = execute_query(DEMO_DB_PATH, "SELECT COUNT(*) FROM sales;", read_only=True)["rows"][0][0]

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                render_html(
                    f"""
                    <div class="metric-card">
                        <div>
                            <div class="metric-label">Products</div>
                            <div class="metric-val">{c_prod}</div>
                        </div>
                        <div class="metric-icon-box" style="background:#EFF6FF; color:#2563EB;">📦</div>
                    </div>
                    """
                )
            with col_m2:
                render_html(
                    f"""
                    <div class="metric-card">
                        <div>
                            <div class="metric-label">Customers</div>
                            <div class="metric-val">{c_cust}</div>
                        </div>
                        <div class="metric-icon-box" style="background:#F0FDF4; color:#16A34A;">👥</div>
                    </div>
                    """
                )
            with col_m3:
                render_html(
                    f"""
                    <div class="metric-card">
                        <div>
                            <div class="metric-label">Sales Records</div>
                            <div class="metric-val">{c_sale}</div>
                        </div>
                        <div class="metric-icon-box" style="background:#FEF3C7; color:#D97706;">📊</div>
                    </div>
                    """
                )
        else:
            if st.session_state.upload_result is not None:
                up_res = st.session_state.upload_result
                render_html(
                    f"""
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:14px;">
                        <h5 style="margin:0; font-weight:700;">📁 Uploaded dataset: {up_res.file_name}</h5>
                        <span class="card-pill-blue">Active Workspace</span>
                    </div>
                    """
                )
                col_m1, col_m2, col_m3 = st.columns(3)
                with col_m1:
                    render_html(
                        f"""
                        <div class="metric-card">
                            <div>
                                <div class="metric-label">Total Rows</div>
                                <div class="metric-val">{up_res.row_count:,}</div>
                            </div>
                            <div class="metric-icon-box" style="background:#EFF6FF; color:#2563EB;">📄</div>
                        </div>
                        """
                    )
                with col_m2:
                    render_html(
                        f"""
                        <div class="metric-card">
                            <div>
                                <div class="metric-label">Columns</div>
                                <div class="metric-val">{up_res.column_count}</div>
                            </div>
                            <div class="metric-icon-box" style="background:#F0FDF4; color:#16A34A;">🏷️</div>
                        </div>
                        """
                    )
                with col_m3:
                    render_html(
                        f"""
                        <div class="metric-card">
                            <div>
                                <div class="metric-label">Table Name</div>
                                <div class="metric-val" style="font-size:1.15rem; font-family:monospace;">{up_res.table_name}</div>
                            </div>
                            <div class="metric-icon-box" style="background:#FEF3C7; color:#D97706;">🗃️</div>
                        </div>
                        """
                    )

    # RIGHT COLUMN: "HOW IT WORKS" TIMELINE PANEL
    with col_sidebar_info:
        model_display = status.model_name if status.is_available else "qwen2.5-coder:1.5b"
        how_it_works_html = (
            f'<div class="how-it-works-card">'
            f'<div class="how-it-works-title"><span>💡</span> How it works</div>'
            f'<div class="step-item">'
            f'<div class="step-num">1</div>'
            f'<div class="step-line"></div>'
            f'<div>'
            f'<div class="step-content-title">Ask in plain English</div>'
            f'<div class="step-content-desc">Type your question in natural language, like "Which product has the lowest stock?".</div>'
            f'</div>'
            f'</div>'
            f'<div class="step-item">'
            f'<div class="step-num">2</div>'
            f'<div class="step-line"></div>'
            f'<div>'
            f'<div class="step-content-title">Local LLM generates SQL</div>'
            f'<div class="step-content-desc">Our local AI ({model_display}) converts your question into verified SQLite query.</div>'
            f'</div>'
            f'</div>'
            f'<div class="step-item">'
            f'<div class="step-num">3</div>'
            f'<div>'
            f'<div class="step-content-title">SQLite returns verified results</div>'
            f'<div class="step-content-desc">The query is safely executed on your data with strict AST security validation.</div>'
            f'</div>'
            f'</div>'
            f'<div class="security-notice-card">'
            f'<div style="font-size:24px; color:#16A34A; line-height:1;">🛡️</div>'
            f'<div>'
            f'<div style="font-size:0.85rem; font-weight:700; color:#065F46; margin-bottom:2px;">Read-only queries</div>'
            f'<div style="font-size:0.78rem; color:#047857; line-height:1.35;">Your data is protected with read-only access and strict SQL validation.</div>'
            f'</div>'
            f'</div>'
            f'</div>'
        )
        st.markdown(how_it_works_html, unsafe_allow_html=True)


# =========================================================================
# VIEW 2: DEMO DATABASE (Tables, Columns, Relationships)
# =========================================================================
elif st.session_state.nav_view == "Demo Database":
    st.markdown('<div class="hero-title">Demo Database Catalog</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Preloaded fictional retail records for products, customers, and sales transactions.</div>',
        unsafe_allow_html=True,
    )

    t1, t2, t3 = st.tabs(["📦 Products (12 items)", "👥 Customers (12 records)", "📊 Sales (28 transactions)"])

    with t1:
        st.markdown("**Catalog Items with Inventory & Pricing:**")
        df_p = pd.DataFrame(execute_query(DEMO_DB_PATH, "SELECT * FROM products;", read_only=True)["rows"],
                            columns=["product_id", "product_name", "category", "unit_price", "stock_quantity"])
        st.dataframe(df_p, use_container_width=True, hide_index=True)

    with t2:
        st.markdown("**Customer Records & Geographic Locations:**")
        df_c = pd.DataFrame(execute_query(DEMO_DB_PATH, "SELECT * FROM customers;", read_only=True)["rows"],
                            columns=["customer_id", "customer_name", "city"])
        st.dataframe(df_c, use_container_width=True, hide_index=True)

    with t3:
        st.markdown("**Sales Transactions Linked by Foreign Keys:**")
        df_s = pd.DataFrame(execute_query(DEMO_DB_PATH, "SELECT * FROM sales;", read_only=True)["rows"],
                            columns=["sale_id", "product_id", "customer_id", "quantity", "sale_date", "total_amount"])
        st.dataframe(df_s, use_container_width=True, hide_index=True)


# =========================================================================
# VIEW 3: UPLOAD DATA (Excel / CSV Pipeline)
# =========================================================================
elif st.session_state.nav_view == "Upload Data":
    st.markdown('<div class="hero-title">Upload Excel or CSV File</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Upload any tabular dataset. Each upload is saved in an isolated temporary SQLite database.</div>',
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Choose an Excel or CSV file (Max 25 MB):",
        type=["csv", "xlsx", "xls"],
        help="Upload CSV or Excel spreadsheets. Duplicates and types are automatically resolved.",
    )

    if uploaded_file is not None and (
        st.session_state.upload_result is None
        or st.session_state.upload_result.file_name != uploaded_file.name
    ):
        with st.spinner("Processing file, inferring column types & isolating workspace..."):
            try:
                processor = FileProcessor()
                result = processor.process_file(
                    uploaded_file,
                    file_name=uploaded_file.name,
                    file_size_bytes=uploaded_file.size,
                )
                st.session_state.upload_result = result
                st.session_state.data_mode = "upload"
                st.session_state.chat_history = []
                st.success(f"Successfully loaded '{uploaded_file.name}' into table `{result.table_name}` ({result.row_count:,} rows)!")
                st.rerun()
            except FileProcessingError as e:
                st.error(f"Upload Error: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")

    if st.session_state.upload_result is not None:
        up_res = st.session_state.upload_result
        st.markdown(
            f"""
            <div class="summary-box" style="margin-top:14px;">
                Active Table: <code>{up_res.table_name}</code> | Rows: <b>{up_res.row_count:,}</b> | Columns: <b>{up_res.column_count}</b>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if up_res.warnings:
            for w in up_res.warnings:
                st.warning(f"⚠️ {w}")

        st.markdown("#### Preview (First 10 Rows):")
        st.dataframe(up_res.preview_df, use_container_width=True, hide_index=True)

        st.markdown("#### Inferred SQLite Column Data Types:")
        col_type_data = [{"Column Name": c, "SQLite Affinity Type": up_res.column_types.get(c, "TEXT")} for c in up_res.columns]
        st.dataframe(pd.DataFrame(col_type_data), use_container_width=True, hide_index=True)

        # ASK A QUESTION ABOUT YOUR DATA SECTION
        st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
        st.markdown("### 💬 Ask a Question About Your Data")
        st.caption(f"Query `{up_res.table_name}` ({up_res.row_count:,} rows) in natural English. SQL will be generated by Ollama and executed safely on SQLite.")

        render_html(
            f"""
            <div class="query-card">
                <div class="query-card-header">
                    <span>💬</span> Ask a question about your uploaded data <span style="font-size:0.8rem; color:#64748B; font-weight:500;">(Target: <b>{up_res.file_name}</b>)</span>
                </div>
            """
        )

        col_up_input, col_up_btn = st.columns([3.8, 1.2])
        with col_up_input:
            up_input_val = st.text_input(
                "Ask a question about your uploaded file in plain English:",
                value=st.session_state.get("upload_current_question", ""),
                placeholder=f"e.g. Which {up_res.columns[0] if up_res.columns else 'item'} has the highest value? / What is the total count?",
                label_visibility="collapsed",
                key="upload_question_input",
            )
        with col_up_btn:
            upload_ask_clicked = st.button("✨ Ask AI →", key="btn_upload_ask", type="primary", use_container_width=True)

        st.markdown("</div>", unsafe_allow_html=True)

        up_question_to_run = up_input_val.strip() if up_input_val.strip() else st.session_state.get("upload_current_question", "").strip()
        if (upload_ask_clicked or bool(st.session_state.get("upload_current_question", ""))) and up_question_to_run:
            st.session_state["upload_current_question"] = ""
            st.session_state.data_mode = "upload"
            sb_up = SchemaBuilder(up_res.db_path)
            schema_dict_up = sb_up.get_validator_schema()
            prompt_text_up = sb_up.build_schema_prompt_text()
            run_query_flow(
                question_text=up_question_to_run,
                db_path=up_res.db_path,
                schema_dict=schema_dict_up,
                prompt_text=prompt_text_up,
            )


# =========================================================================
# VIEW 4: QUERY HISTORY
# =========================================================================
elif st.session_state.nav_view == "Query History":
    st.markdown('<div class="hero-title">Session Query History</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Chronological record of questions, AI-generated SQL, and returned datasets in this session.</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_history:
        st.info("No queries have been executed yet in this session. Ask a question on the Overview page to get started!")
    else:
        if st.button("🗑️ Clear History"):
            st.session_state.chat_history = []
            st.rerun()


# =========================================================================
# VIEW 5: SETTINGS
# =========================================================================
elif st.session_state.nav_view == "Settings":
    st.markdown('<div class="hero-title">Application Settings</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Manage cloud Groq API keys, local Ollama endpoints, and database resets.</div>',
        unsafe_allow_html=True,
    )

    tab_cloud, tab_local, tab_data = st.tabs(["⚡ Groq Cloud (24/7 Hosting)", "🖥️ Local Ollama (Offline)", "🧹 Dataset Management"])

    with tab_cloud:
        st.subheader("⚡ Groq Cloud AI Engine (Fast & 24/7)")
        st.markdown(
            """
            Groq provides lightning-fast LPU inference (~0.5s SQL generation) with a generous free tier.
            It enables your app to run 24/7 on **Streamlit Community Cloud** or any mobile/laptop browser without needing your PC running.
            """
        )
        with st.form("groq_settings_form"):
            groq_key_input = st.text_input(
                "Groq API Key",
                value=st.session_state.groq_api_key,
                type="password",
                help="Get your free key from https://console.groq.com/keys",
            )
            # Find current model index
            groq_model_idx = 0
            if st.session_state.groq_model in SUPPORTED_GROQ_MODELS:
                groq_model_idx = SUPPORTED_GROQ_MODELS.index(st.session_state.groq_model)

            groq_model_select = st.selectbox(
                "Groq Model",
                options=SUPPORTED_GROQ_MODELS,
                index=groq_model_idx,
                help="Recommended: qwen/qwen3.8-27b (ultra-fast 0.5s SQL) or openai/gpt-oss-120b (high reasoning)",
            )
            save_groq = st.form_submit_button("💾 Save & Test Groq Connection", type="primary")

            if save_groq:
                st.session_state.groq_api_key = groq_key_input.strip()
                st.session_state.groq_model = groq_model_select
                st.session_state.llm_manager = LLMManager(
                    groq_api_key=st.session_state.groq_api_key,
                    groq_model=st.session_state.groq_model,
                    ollama_url=st.session_state.ollama_url,
                    ollama_model=st.session_state.ollama_model,
                )
                new_st = st.session_state.llm_manager.get_status(force_refresh=True)
                if new_st.is_available and new_st.provider == "groq":
                    st.success(f"✅ Connected to Groq Cloud model '{new_st.model_name}'! Responses will be ~0.5s.")
                else:
                    st.error(f"❌ Connection failed: {new_st.details}")
                st.rerun()

    with tab_local:
        st.subheader("🖥️ Local Ollama Configuration (Offline & Private)")
        st.markdown("Use local Ollama when you are working offline on your local computer without internet access.")
        with st.form("ollama_settings_form"):
            c_url = st.text_input("Ollama Endpoint URL", value=st.session_state.ollama_url)
            c_mod = st.text_input("Model Name", value=st.session_state.ollama_model)
            save_ollama = st.form_submit_button("💾 Save & Test Ollama Connection")

            if save_ollama:
                st.session_state.ollama_url = c_url.strip()
                st.session_state.ollama_model = c_mod.strip()
                st.session_state.llm_manager = LLMManager(
                    groq_api_key=st.session_state.groq_api_key,
                    groq_model=st.session_state.groq_model,
                    ollama_url=c_url,
                    ollama_model=c_mod,
                )
                new_st = st.session_state.llm_manager.get_status(force_refresh=True)
                if new_st.is_available:
                    st.success(f"✅ Connected to model '{new_st.model_name}' (Provider: {new_st.provider})!")
                else:
                    st.error(f"❌ Failed to connect: {new_st.details}")
                st.rerun()

    with tab_data:
        st.subheader("🧹 Dataset Management")
        st.markdown("Reset the demonstration database back to pristine initial state.")
        if st.button("🔄 Reset Demo Database"):
            initialize_demo_database(force_recreate=True)
            st.success("Demo database reseeding completed.")
            st.rerun()


# =========================================================================
# VIEW 6: HELP & ARCHITECTURE
# =========================================================================
elif st.session_state.nav_view == "Help":
    st.markdown('<div class="hero-title">How AI Database Assistant Works</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Understanding the collaboration between the AI model, SQLGlot, and SQLite.</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        ### 🛡️ Multi-Layer Security Architecture
        1. **Dual AI Backend (Cloud & Local):**
           - **Groq Cloud:** Ultra-fast LPUs (~0.5s SQL generation) powering 24/7 public web deployments without needing local hardware.
           - **Local Ollama:** 100% private, offline inference on local machines (`qwen2.5-coder:1.5b`).
        2. **SQLGlot AST Inspection:** All generated SQL is treated as untrusted input. The query Abstract Syntax Tree (AST) is strictly checked to permit only a single `SELECT` query.
        3. **Strict Allowlists:** Tables and columns are validated against known schemas. Administrative commands (`DROP`, `DELETE`, `PRAGMA`, etc.) are unconditionally rejected.
        4. **SQLite Engine Read-Only Mode:** SQLite connections execute in read-only mode (`mode=ro`) with `PRAGMA query_only = ON;`.
        5. **Factual Grounding:** Results are calculated strictly by SQLite; the LLM never invents data rows.
        """
    )


# =========================================================================
# RESULTS SECTION (Renders Whenever Queries Have Been Executed)
# =========================================================================
if st.session_state.chat_history:
    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)
    st.markdown("### 📊 Query Results & Answer")

    for idx, entry in enumerate(st.session_state.chat_history):
        q_text = entry["question"]
        q_res: QueryResult = entry["query_result"]
        model_source = entry["model_source"]
        gen_src = entry.get("generation_source", "")
        raw_resp = entry.get("raw_response")
        sql_used = entry["sql"]

        st.markdown('<div class="result-banner">', unsafe_allow_html=True)
        st.markdown(f"#### ❓ {q_text}")

        # Model Attribution Badge
        if gen_src == "cloud_llm_groq":
            st.markdown(
                f'<span class="card-pill-green" style="font-size:0.8rem; padding:4px 12px; margin-bottom:12px;">⚡ Real Groq Cloud Inference ({model_source})</span>',
                unsafe_allow_html=True,
            )
        elif gen_src == "local_llm_ollama":
            st.markdown(
                f'<span class="card-pill-green" style="font-size:0.8rem; padding:4px 12px; margin-bottom:12px;">🟢 Real Local LLM Inference ({model_source})</span>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<span class="card-pill-blue" style="font-size:0.8rem; padding:4px 12px; margin-bottom:12px;">ℹ️ {model_source}</span>',
                unsafe_allow_html=True,
            )

        if not q_res.success:
            st.error(f"❌ {q_res.error}")
        else:
            # Plain-English factual answer summary
            st.markdown(f'<div class="summary-box">💡 {q_res.summary}</div>', unsafe_allow_html=True)

            # Interactive Data Table
            if not q_res.df.empty:
                st.dataframe(q_res.df, use_container_width=True, hide_index=True)

                col_dl, col_space = st.columns([1.5, 4])
                with col_dl:
                    csv_bytes = ResultFormatter.to_csv_bytes(q_res.df)
                    st.download_button(
                        label="📥 Export Results as CSV",
                        data=csv_bytes,
                        file_name=f"query_result_{idx + 1}.csv",
                        mime="text/csv",
                        key=f"dl_res_csv_{idx}",
                        use_container_width=True,
                    )
            else:
                st.info("Query returned 0 rows.")

            # Optional Chart (rendered strictly once when chart_fig is not None)
            if q_res.chart_fig is not None:
                st.plotly_chart(q_res.chart_fig, use_container_width=True)

        # Exactly ONE SQL Inspector (rendered regardless of whether chart is available)
        with st.expander("🛡️ Verified SQL Query & Security Details", expanded=not q_res.success):
            if q_res.success:
                st.markdown(
                    f'<span class="card-pill-blue">✓ AST Validated & Read-Only Enforced</span> &nbsp; '
                    f'<span>Model Source: <b>{model_source}</b></span> &nbsp; '
                    f'<span>Execution time: <b>{q_res.execution_time_ms} ms</b></span>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<span style="background:#FEE2E2; color:#991B1B; padding:3px 10px; border-radius:12px; font-weight:600; font-size:0.8rem; border:1px solid #FECACA;">⚠️ Validation / Execution Error</span> &nbsp; '
                    f'<span>Model Source: <b>{model_source}</b></span>',
                    unsafe_allow_html=True,
                )

            st.markdown("**Generated SQL (from LLM):**")
            st.code(sql_used or q_res.raw_sql, language="sql")

            if q_res.validated_sql and q_res.validated_sql.strip() != (sql_used or "").strip():
                st.markdown("**Validated & Executed SQL (in SQLite):**")
                st.code(q_res.validated_sql, language="sql")
            elif q_res.validated_sql:
                st.markdown("**Validated & Executed SQL:**")
                st.code(q_res.validated_sql, language="sql")

            if raw_resp:
                st.markdown("**Raw LLM Output (Uncut):**")
                st.code(raw_resp, language="text")

        st.markdown("</div>", unsafe_allow_html=True)
