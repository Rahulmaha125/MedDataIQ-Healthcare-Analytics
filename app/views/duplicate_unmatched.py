"""
MedDataIQ — View 4: Duplicate Claims & Unmatched Billing Audit
Focuses on duplicate claim risk isolation and ghost billing detection.
"""

import streamlit as st
import pandas as pd
from app.components.theme import format_currency, render_html
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0;">
            Duplicate Claims & Unmatched Billing Audit
        </h2>
        <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
            Isolates redundant claim submissions and investigates orphan claims lacking EHR documentation.
        </p>
    </div>
    """)

    # 1. Fetch metrics
    dup_q = """
    SELECT 
        claim_id,
        claim_number,
        encounter_id,
        patient_id,
        provider_id,
        payer_id,
        service_date,
        billed_amount,
        allowed_amount,
        paid_amount,
        claim_status
    FROM fact_billing_claims
    WHERE audit_category = 'DUPLICATE_CLAIM' OR claim_number LIKE '%-DUP'
    ORDER BY service_date DESC
    """
    dup_df = db.execute_query(dup_q)

    unmatched_q = """
    SELECT 
        claim_id,
        claim_number,
        encounter_id,
        patient_id,
        provider_id,
        payer_id,
        service_date,
        claim_submission_date,
        billed_amount,
        claim_status
    FROM fact_billing_claims
    WHERE encounter_id NOT IN (SELECT encounter_id FROM fact_encounters)
    ORDER BY service_date DESC
    """
    unmatched_df = db.execute_query(unmatched_q)

    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Duplicate Claims</span>
            <div class="kpi-value kpi-value-rose">{len(dup_df):,}</div>
            <p class="kpi-subtext">Redundant claim submissions</p>
        </div>
        """)
    with c2:
        dup_sum = dup_df["billed_amount"].sum()
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Duplicate Billed Risk</span>
            <div class="kpi-value kpi-value-rose">{format_currency(dup_sum)}</div>
            <p class="kpi-subtext">Excess financial exposure</p>
        </div>
        """)
    with c3:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Unmatched Claims</span>
            <div class="kpi-value kpi-value-amber">{len(unmatched_df):,}</div>
            <p class="kpi-subtext">Claims missing EHR encounter</p>
        </div>
        """)
    with c4:
        unmatched_sum = unmatched_df["billed_amount"].sum()
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Unmatched Billed Value</span>
            <div class="kpi-value kpi-value-amber">{format_currency(unmatched_sum)}</div>
            <p class="kpi-subtext">Documentation compliance risk</p>
        </div>
        """)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Tabs: Duplicate Claims vs Unmatched Claims
    tab1, tab2 = st.tabs(["Duplicate Claim Submissions (Action Required)", "Unmatched Claims (Documentation Audit)"])

    with tab1:
        render_html("""
        <div class="glass-panel-header">
            <h3 class="glass-panel-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F43F5E" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
                Duplicate Claims Queue (Voiding & Retraction)
            </h3>
            <p class="glass-panel-subtitle">These 240 secondary claims have already been billed once. Voiding them prevents payer penalties and recoupment.</p>
        </div>
        """)

        dup_disp = dup_df[[
            "claim_number", "service_date", "encounter_id", "patient_id",
            "billed_amount", "claim_status"
        ]].copy()
        dup_disp = dup_disp.rename(columns={
            "claim_number": "Duplicate Claim #",
            "service_date": "Service Date",
            "encounter_id": "Encounter UUID",
            "patient_id": "Patient UUID",
            "billed_amount": "Redundant Billed ($)",
            "claim_status": "Status"
        })
        dup_disp["Redundant Billed ($)"] = dup_disp["Redundant Billed ($)"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(dup_disp, use_container_width=True, hide_index=True)

        dup_csv = dup_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Duplicate Claims for Voiding",
            data=dup_csv,
            file_name="duplicate_claims_to_void.csv",
            mime="text/csv"
        )

    with tab2:
        render_html("""
        <div class="glass-panel-header">
            <h3 class="glass-panel-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="4.93" y1="4.93" x2="19.07" y2="19.07"></line>
                </svg>
                Unmatched Claims (Ghost Bills Without EHR Entry)
            </h3>
            <p class="glass-panel-subtitle">Claims billed to payers referencing non-existent clinical visits in the EHR system.</p>
        </div>
        """)

        unmatched_disp = unmatched_df[[
            "claim_number", "service_date", "claim_submission_date",
            "patient_id", "billed_amount", "claim_status"
        ]].copy()
        unmatched_disp = unmatched_disp.rename(columns={
            "claim_number": "Claim #",
            "service_date": "Service Date",
            "claim_submission_date": "Submitted Date",
            "patient_id": "Patient UUID",
            "billed_amount": "Billed ($)",
            "claim_status": "Status"
        })
        unmatched_disp["Billed ($)"] = unmatched_disp["Billed ($)"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(unmatched_disp, use_container_width=True, hide_index=True)

        unmatched_csv = unmatched_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="Download Unmatched Claims for Chart Audit",
            data=unmatched_csv,
            file_name="unmatched_claims_documentation_audit.csv",
            mime="text/csv"
        )
