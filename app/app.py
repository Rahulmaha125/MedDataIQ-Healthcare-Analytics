"""
MedDataIQ — Healthcare Data Quality & Analytics Platform
Main Streamlit Application Entrypoint
Design: 3D Glassmorphism + Futuristic Medical Intelligence + Cinematic Dark UI
"""

import sys
from pathlib import Path
import streamlit as st

# Ensure repository root is in python path and prevent app directory from shadowing app package
ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = Path(__file__).resolve().parent

# Remove script directory from sys.path if Streamlit inserted it
sys.path = [p for p in sys.path if Path(p).resolve() != APP_DIR]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Clear shadowed non-package 'app' module if loaded as script
if "app" in sys.modules and not hasattr(sys.modules["app"], "__path__"):
    del sys.modules["app"]

from src.db.connection import DatabaseManager
from app.components.theme import render_html
from app.views import (
    executive_overview,
    billing_reconciliation,
    revenue_leakage,
    duplicate_unmatched,
    provider_operations,
    data_quality,
    investigation_queue,
    hospital_connect
)

# 1. Page Configuration
st.set_page_config(
    page_title="MedDataIQ — Healthcare Intelligence",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Inject Custom 3D Glassmorphism Stylesheet
CSS_FILE = Path(__file__).parent / "assets" / "styles.css"
if CSS_FILE.exists():
    with open(CSS_FILE, "r", encoding="utf-8") as f:
        custom_css = f.read()
    st.markdown(f"<style>{custom_css}</style>", unsafe_allow_html=True)

# 3. Initialize Shared Database Manager
@st.cache_resource
def get_database_connection():
    return DatabaseManager()

db = get_database_connection()
db_status = db.get_status()

# 4. Sidebar Branding & Navigation
if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Executive Overview"

ANALYTIC_PAGES = {
    "Executive Overview": executive_overview,
    "Billing Reconciliation": billing_reconciliation,
    "Revenue Leakage": revenue_leakage,
    "Duplicate & Unmatched Claims": duplicate_unmatched,
    "Provider & Hospital Operations": provider_operations,
    "Data Quality": data_quality,
    "Investigation Queue": investigation_queue
}

ALL_PAGES = {
    **ANALYTIC_PAGES,
    "Hospital Connect & Data Hub": hospital_connect
}

with st.sidebar:
    render_html("""
    <div class="sidebar-brand">
        <div class="sidebar-logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <span>MedData<span class="sidebar-logo-highlight">IQ</span></span>
        </div>
        <p class="sidebar-tagline">Clinical Operations & Revenue Integrity</p>
    </div>
    """)

    # 1. SEPARATE SECTION: Hospital Data Pipeline & Onboarding
    render_html("""
    <p style='font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #00F2FE; letter-spacing: 0.08em; margin: 4px 0 8px 4px; display: flex; align-items: center; gap: 6px;'>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
        Data Ingestion Hub
    </p>
    """)

    is_connect_active = (st.session_state["current_page"] == "Hospital Connect & Data Hub")

    if st.button(
        "🏥 Hospital Connect & Data Hub" if not is_connect_active else "🟢 Active: Hospital Ingestion Hub",
        key="btn_nav_connect",
        type="primary" if is_connect_active else "secondary",
        use_container_width=True
    ):
        st.session_state["current_page"] = "Hospital Connect & Data Hub"
        st.rerun()

    # 2. SEPARATE SECTION: Healthcare Analytics & Audits
    render_html("""
    <div style="margin: 18px 0 10px 0; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 14px;">
        <p style='font-size: 0.72rem; text-transform: uppercase; font-weight: 700; color: #64748B; letter-spacing: 0.08em; margin: 0 0 8px 4px; display: flex; align-items: center; gap: 6px;'>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#64748B" stroke-width="2.5"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>
            Healthcare Analytics & Audits
        </p>
    </div>
    """)

    analytic_keys = list(ANALYTIC_PAGES.keys())
    current_analytic_idx = analytic_keys.index(st.session_state["current_page"]) if st.session_state["current_page"] in analytic_keys else None

    selected_analytic = st.radio(
        label="Analytics Workspaces",
        options=analytic_keys,
        index=current_analytic_idx,
        label_visibility="collapsed"
    )

    # When user clicks a radio option from the analytics list
    if selected_analytic:
        if is_connect_active:
            st.session_state["current_page"] = selected_analytic
            st.rerun()
        elif selected_analytic != st.session_state["current_page"]:
            st.session_state["current_page"] = selected_analytic
            st.rerun()

    st.markdown("---")

    # Engine Status Widget in Sidebar Footer
    engine_name = "PostgreSQL 18" if db_status.get("postgresql_reachable") else "SQLite Data Mart"
    render_html(f"""
    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 10px; padding: 12px; margin-top: 10px;">
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <span class="status-pulse-dot"></span>
            <span style="font-size: 0.8rem; font-weight: 700; color: #FFFFFF;">System Connected</span>
        </div>
        <div style="font-size: 0.72rem; color: #94A3B8;">Engine: <b style="color: #00F2FE;">{engine_name}</b></div>
        <div style="font-size: 0.72rem; color: #64748B; margin-top: 2px;">Environment: Production SaaS</div>
    </div>
    """)

# 5. Route to Selected Page View
active_page_name = st.session_state.get("current_page", "Executive Overview")
active_view_module = ALL_PAGES.get(active_page_name, executive_overview)
active_view_module.render(db)
