"""
MedDataIQ — View 3: Revenue Leakage Analysis
Identifies unbilled clinical encounters (clinical services delivered with 0 claims billed).
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from app.components.theme import apply_dark_theme, COLORS, format_currency, render_html
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0;">
            Revenue Leakage & Unbilled Services
        </h2>
        <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
            Detects completed patient encounters in the EHR that have zero matching insurance claims filed.
        </p>
    </div>
    """)

    # 1. Fetch unbilled encounters
    unbilled_q = """
    SELECT 
        e.encounter_id,
        e.patient_id,
        e.encounter_date,
        e.encounter_class,
        e.encounter_description,
        e.reason_description,
        e.duration_minutes,
        e.total_claim_cost AS unbilled_amount,
        p.provider_name,
        p.specialty,
        o.organization_name
    FROM fact_encounters e
    JOIN dim_providers p ON e.provider_id = p.provider_id
    JOIN dim_organizations o ON e.organization_id = o.organization_id
    WHERE e.encounter_id NOT IN (
        SELECT DISTINCT encounter_id FROM fact_billing_claims WHERE encounter_id IS NOT NULL
    )
    ORDER BY e.total_claim_cost DESC
    """
    unbilled_df = db.execute_query(unbilled_q)

    total_unbilled_records = len(unbilled_df)
    total_unbilled_revenue = unbilled_df["unbilled_amount"].sum()
    avg_unbilled_per_visit = unbilled_df["unbilled_amount"].mean() if total_unbilled_records > 0 else 0

    # Metric Tiles
    c1, c2, c3 = st.columns(3)
    with c1:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Unbilled Encounters</span>
            <div class="kpi-value kpi-value-rose">{total_unbilled_records:,}</div>
            <p class="kpi-subtext">3.99% of total clinical visits</p>
        </div>
        """)
    with c2:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Total Unbilled Revenue at Risk</span>
            <div class="kpi-value kpi-value-rose">{format_currency(total_unbilled_revenue)}</div>
            <p class="kpi-subtext">Potential revenue leakage to recover</p>
        </div>
        """)
    with c3:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Average Value Per Unbilled Visit</span>
            <div class="kpi-value kpi-value-amber">{format_currency(avg_unbilled_per_visit)}</div>
            <p class="kpi-subtext">Weighted across visit intensities</p>
        </div>
        """)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Charts: Unbilled Exposure by Encounter Class and Facility
    ch1, ch2 = st.columns(2)

    with ch1:
        class_grp = unbilled_df.groupby("encounter_class")["unbilled_amount"].sum().reset_index()
        fig_class = go.Figure(go.Bar(
            x=class_grp["encounter_class"],
            y=class_grp["unbilled_amount"],
            marker=dict(color=COLORS["rose"], line=dict(color="rgba(255,255,255,0.15)", width=1)),
            hovertemplate="<b>%{x}</b><br>Unbilled: $%{y:,.2f}<extra></extra>"
        ))
        fig_class = apply_dark_theme(fig_class, title="Unbilled Revenue by Clinical Class ($)", height=340)
        fig_class.update_layout(xaxis_title="Encounter Class", yaxis_title="Unbilled Dollars ($)")
        st.plotly_chart(fig_class, use_container_width=True)

    with ch2:
        org_grp = unbilled_df.groupby("organization_name")["unbilled_amount"].sum().reset_index().sort_values(by="unbilled_amount", ascending=True)
        fig_org = go.Figure(go.Bar(
            y=org_grp["organization_name"],
            x=org_grp["unbilled_amount"],
            orientation="h",
            marker=dict(color=COLORS["amber"], line=dict(color="rgba(255,255,255,0.15)", width=1)),
            hovertemplate="<b>%{y}</b><br>Unbilled: $%{x:,.2f}<extra></extra>"
        ))
        fig_org = apply_dark_theme(fig_org, title="Unbilled Revenue by Hospital Network ($)", height=340)
        fig_org.update_layout(xaxis_title="Unbilled Dollars ($)", yaxis_title=None)
        st.plotly_chart(fig_org, use_container_width=True)

    # 3. Actionable Table
    render_html("""
    <div class="glass-panel-header" style="margin-top: 20px; margin-bottom: 10px;">
        <h3 class="glass-panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#F43F5E" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="8" x2="12" y2="12"></line>
                <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
            Unbilled Clinical Encounters Triage Table
        </h3>
        <p class="glass-panel-subtitle">Prioritized list of unbilled patient visits for immediate revenue cycle filing</p>
    </div>
    """)

    # Filter controls
    classes = ["ALL"] + sorted(unbilled_df["encounter_class"].unique().tolist())
    sel_class = st.selectbox("Filter by Clinical Class", classes, index=0)

    filtered_unbilled = unbilled_df if sel_class == "ALL" else unbilled_df[unbilled_df["encounter_class"] == sel_class]

    disp = filtered_unbilled[[
        "encounter_date", "encounter_class", "organization_name",
        "provider_name", "reason_description", "unbilled_amount"
    ]].copy()

    disp = disp.rename(columns={
        "encounter_date": "Date",
        "encounter_class": "Class",
        "organization_name": "Hospital",
        "provider_name": "Physician",
        "reason_description": "Clinical Reason",
        "unbilled_amount": "Revenue at Risk ($)"
    })
    disp["Revenue at Risk ($)"] = disp["Revenue at Risk ($)"].apply(lambda x: f"${x:,.2f}")

    st.dataframe(disp, use_container_width=True, hide_index=True)

    # CSV Download
    csv_bytes = filtered_unbilled.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Unbilled Encounters CSV for Billing",
        data=csv_bytes,
        file_name="unbilled_encounters_recovery.csv",
        mime="text/csv"
    )
