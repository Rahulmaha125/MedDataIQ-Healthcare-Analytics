"""
MedDataIQ — View 1: Executive Overview
High-level operational KPIs, monthly clinical expenditure vs billing, and clinical class mix.
"""

import streamlit as st
import pandas as pd
from app.components.header import render_hero_header
from app.components.kpi_cards import render_kpi_cards
from app.components.charts import build_monthly_trend_chart, build_reconciliation_donut
from app.components.theme import format_currency, format_number, render_html
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    # Load Key Metrics
    status = db.get_status()
    render_hero_header(status)

    # 1. Fetch Executive KPIs
    kpi_query = """
    SELECT 
        (SELECT COUNT(*) FROM dim_patients) AS total_patients,
        (SELECT COUNT(*) FROM fact_encounters) AS total_encounters,
        (SELECT ROUND(SUM(total_claim_cost), 2) FROM fact_encounters) AS total_clinical_cost,
        (SELECT ROUND(SUM(billed_amount), 2) FROM fact_billing_claims) AS total_billed_amount,
        (SELECT ROUND(SUM(variance_amount), 2) FROM v_billing_reconciliation_summary) AS net_variance,
        (SELECT ROUND(SUM(claim_billed_amount), 2) FROM v_billing_reconciliation_summary WHERE reconciliation_status = 'DUPLICATE_CLAIM') AS duplicate_exposure
    """
    metrics = db.execute_query(kpi_query).iloc[0].to_dict()

    # Render 3D KPI Cards
    render_kpi_cards(metrics)

    # 2. Main Visualizations Row
    col1, col2 = st.columns([1.6, 1.0])

    with col1:
        with st.container():
            render_html("""
            <div class="glass-panel-header">
                <h3 class="glass-panel-title">Monthly Clinical Cost vs. Billed Charges</h3>
                <p class="glass-panel-subtitle">Historical cash-flow trajectory and margin tracking across months</p>
            </div>
            """)
            monthly_df = db.execute_query("SELECT * FROM v_kpi_executive_monthly ORDER BY year_month")
            trend_fig = build_monthly_trend_chart(monthly_df)
            st.plotly_chart(trend_fig, use_container_width=True)

    with col2:
        with st.container():
            render_html("""
            <div class="glass-panel-header">
                <h3 class="glass-panel-title">Audit Reconciliation Mix</h3>
                <p class="glass-panel-subtitle">Proportion of clean parity vs. flagged audit records</p>
            </div>
            """)
            recon_breakdown = db.execute_query("""
                SELECT reconciliation_status, COUNT(*) as record_count 
                FROM v_billing_reconciliation_summary 
                GROUP BY reconciliation_status
            """)
            donut_fig = build_reconciliation_donut(recon_breakdown)
            st.plotly_chart(donut_fig, use_container_width=True)

    # 3. Clinical Encounter Mix Breakdown
    render_html("""
    <div class="glass-panel-header" style="margin-top: 20px; margin-bottom: 10px;">
        <h3 class="glass-panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
            </svg>
            Clinical Encounter Class Performance Summary
        </h3>
        <p class="glass-panel-subtitle">Volume distribution, average length of stay (ALOS), and cost intensity across hospital service lines</p>
    </div>
    """)

    class_df = db.execute_query("SELECT * FROM v_encounter_class_summary ORDER BY encounter_count DESC")

    # Format table for display
    display_df = class_df.copy()
    display_df = display_df.rename(columns={
        "encounter_class": "Encounter Class",
        "encounter_count": "Total Visits",
        "volume_share_pct": "Share (%)",
        "unique_patients": "Unique Patients",
        "avg_duration_minutes": "Avg Duration (Mins)",
        "total_cost": "Total Spend ($)",
        "avg_cost_per_encounter": "Avg Cost ($)",
        "total_payer_coverage": "Payer Paid ($)",
        "total_patient_cost": "Patient Copay ($)"
    })

    # Apply currency and number formatting
    for c in ["Total Spend ($)", "Avg Cost ($)", "Payer Paid ($)", "Patient Copay ($)"]:
        display_df[c] = display_df[c].apply(lambda x: f"${x:,.2f}")
    for c in ["Total Visits", "Unique Patients"]:
        display_df[c] = display_df[c].apply(lambda x: f"{x:,}")
    display_df["Share (%)"] = display_df["Share (%)"].apply(lambda x: f"{x:.1f}%")

    st.dataframe(display_df, use_container_width=True, hide_index=True)
