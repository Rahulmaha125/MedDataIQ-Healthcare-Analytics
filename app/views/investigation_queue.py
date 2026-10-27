"""
MedDataIQ — View 7: Actionable Investigation Triage Queue
Prioritizes flagged discrepancies with concrete compliance recommendations for revenue cycle auditors.
"""

from pathlib import Path
import streamlit as st
import pandas as pd
from app.components.theme import format_currency, render_html
from src.config import PROCESSED_DATA_DIR
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0;">
            Audit & Investigation Triage Queue
        </h2>
        <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
            Actionable worklist of 1,443 flagged records categorized by audit risk with recommended remediation actions.
        </p>
    </div>
    """)

    # 1. Load Queue Data
    queue_file = PROCESSED_DATA_DIR / "audit_investigation_queue.csv"
    if not queue_file.exists():
        # Fallback to generating or querying database
        from src.reconciliation import ReconciliationEngine
        engine = ReconciliationEngine(db_manager=db)
        engine.run_reconciliation_audit()

    queue_df = pd.read_csv(queue_file)

    total_queue = len(queue_df)
    high_prio = len(queue_df[queue_df["investigation_priority"] == "HIGH"])
    med_prio = len(queue_df[queue_df["investigation_priority"] == "MEDIUM"])
    total_exposure = queue_df["variance_amount"].abs().sum()

    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Queue Items</span>
            <div class="kpi-value kpi-value-cyan">{total_queue:,}</div>
            <p class="kpi-subtext">Total flagged transactions</p>
        </div>
        """)
    with c2:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">High Priority Action</span>
            <div class="kpi-value kpi-value-rose">{high_prio:,}</div>
            <p class="kpi-subtext">Unbilled, duplicates & unmatched</p>
        </div>
        """)
    with c3:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Medium Priority Review</span>
            <div class="kpi-value kpi-value-amber">{med_prio:,}</div>
            <p class="kpi-subtext">Variances & timing anomalies</p>
        </div>
        """)
    with c4:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Total Financial Exposure</span>
            <div class="kpi-value kpi-value-amber">{format_currency(total_exposure)}</div>
            <p class="kpi-subtext">Cumulative absolute dollar risk</p>
        </div>
        """)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Interactive Queue Table
    render_html("""
    <div class="glass-panel-header" style="margin-top: 20px; margin-bottom: 10px;">
        <h3 class="glass-panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2">
                <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
                <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
            </svg>
            Compliance Triage Worklist
        </h3>
        <p class="glass-panel-subtitle">Review recommended audit steps and export task assignments for billing coordinators</p>
    </div>
    """)

    # Filter Controls
    f1, f2, f3 = st.columns([1.2, 1.5, 1.3])
    with f1:
        prio_opts = ["ALL", "HIGH", "MEDIUM"]
        sel_prio = st.selectbox("Filter Priority", prio_opts, index=0)
    with f2:
        cat_opts = ["ALL"] + sorted(queue_df["reconciliation_status"].unique().tolist())
        sel_cat = st.selectbox("Filter Category", cat_opts, index=0)
    with f3:
        search_kw = st.text_input("Search ID, Action, or Claim #", "")

    # Apply filters
    filtered_q = queue_df.copy()
    if sel_prio != "ALL":
        filtered_q = filtered_q[filtered_q["investigation_priority"] == sel_prio]
    if sel_cat != "ALL":
        filtered_q = filtered_q[filtered_q["reconciliation_status"] == sel_cat]
    if search_kw.strip():
        kw = search_kw.strip().lower()
        filtered_q = filtered_q[
            filtered_q["claim_number"].astype(str).str.lower().str.contains(kw) |
            filtered_q["recommended_action"].astype(str).str.lower().str.contains(kw) |
            filtered_q["reconciliation_status"].astype(str).str.lower().str.contains(kw)
        ]

    st.write(f"Displaying **{len(filtered_q):,}** audit items:")

    # Table columns
    display_q = filtered_q[[
        "investigation_priority", "reconciliation_status", "claim_number",
        "service_date", "clinical_encounter_cost", "claim_billed_amount",
        "variance_amount", "recommended_action"
    ]].copy()

    display_q = display_q.rename(columns={
        "investigation_priority": "Priority",
        "reconciliation_status": "Category",
        "claim_number": "Claim #",
        "service_date": "Service Date",
        "clinical_encounter_cost": "Clinical Cost ($)",
        "claim_billed_amount": "Billed ($)",
        "variance_amount": "Variance ($)",
        "recommended_action": "Recommended Audit Action"
    })

    for c in ["Clinical Cost ($)", "Billed ($)", "Variance ($)"]:
        display_q[c] = display_q[c].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")

    st.dataframe(display_q, use_container_width=True, hide_index=True)

    # Download Button
    q_csv = filtered_q.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Active Investigation Queue CSV",
        data=q_csv,
        file_name="active_investigation_queue.csv",
        mime="text/csv"
    )
