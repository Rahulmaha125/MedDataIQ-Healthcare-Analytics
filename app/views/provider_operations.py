"""
MedDataIQ — View 5: Provider & Hospital Operations
Clinician workload, specialty performance, and healthcare facility capacity utilization.
"""

import streamlit as st
import pandas as pd
from app.components.charts import build_provider_workload_bar
from app.components.theme import format_currency, format_number, render_html
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0;">
            Provider & Hospital Operations Intelligence
        </h2>
        <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
            Evaluates physician volume, clinical intensity, and facility utilization across healthcare networks.
        </p>
    </div>
    """)

    # 1. Fetch Hospital Facility Summary
    hosp_df = db.execute_query("""
        SELECT 
            o.organization_name,
            o.city,
            o.utilization_rate,
            COUNT(DISTINCT p.provider_id) AS active_physicians,
            COUNT(e.encounter_id) AS total_encounters,
            ROUND(SUM(e.total_claim_cost), 2) AS total_revenue
        FROM dim_organizations o
        LEFT JOIN dim_providers p ON o.organization_id = p.organization_id
        LEFT JOIN fact_encounters e ON p.provider_id = e.provider_id
        GROUP BY o.organization_id, o.organization_name, o.city, o.utilization_rate
        ORDER BY total_encounters DESC
    """)

    # 2. Fetch Provider Workload View
    prov_df = db.execute_query("SELECT * FROM v_provider_workload ORDER BY total_encounters DESC")

    col1, col2 = st.columns([1.5, 1.0])

    with col1:
        top_n = st.slider("Select Top Clinicians to Display", 5, 25, 10)
        p_fig = build_provider_workload_bar(prov_df, top_n=top_n)
        st.plotly_chart(p_fig, use_container_width=True)

    with col2:
        render_html("""
        <div class="glass-panel-header" style="margin-bottom: 14px;">
            <h3 class="glass-panel-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                    <polyline points="9 22 9 12 15 12 15 22"></polyline>
                </svg>
                Facility Utilization Matrix
            </h3>
        </div>
        """)

        for _, row in hosp_df.iterrows():
            render_html(f"""
            <div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 12px 14px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 700; font-size: 0.9rem; color: #FFFFFF;">{row['organization_name']}</span>
                    <span class="status-pill status-pill-clean">{row['utilization_rate']}% Bed Cap</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: #94A3B8;">
                    <span>City: {row['city']} • {row['active_physicians']} Doctors</span>
                    <span style="color: #00F2FE; font-weight: 600;">{row['total_encounters']:,} Visits</span>
                </div>
            </div>
            """)

    # 3. Comprehensive Clinician Directory Table
    render_html("""
    <div class="glass-panel-header" style="margin-top: 20px; margin-bottom: 10px;">
        <h3 class="glass-panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2">
                <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                <circle cx="9" cy="7" r="4"></circle>
            </svg>
            Clinician Workload & Revenue Attribution Directory
        </h3>
        <p class="glass-panel-subtitle">Provider metrics across clinical encounters, patient volumes, and revenue attribution</p>
    </div>
    """)

    # Filter by specialty
    specs = ["ALL"] + sorted(prov_df["specialty"].unique().tolist())
    sel_spec = st.selectbox("Filter by Medical Specialty", specs, index=0)

    filtered_prov = prov_df if sel_spec == "ALL" else prov_df[prov_df["specialty"] == sel_spec]

    p_disp = filtered_prov[[
        "provider_name", "specialty", "organization_name",
        "total_encounters", "unique_patients_treated",
        "total_revenue_generated", "high_intensity_visits",
        "avg_encounter_duration_mins"
    ]].copy()

    p_disp = p_disp.rename(columns={
        "provider_name": "Doctor",
        "specialty": "Specialty",
        "organization_name": "Hospital Network",
        "total_encounters": "Encounters",
        "unique_patients_treated": "Patients",
        "total_revenue_generated": "Attributed Revenue ($)",
        "high_intensity_visits": "Acute Visits",
        "avg_encounter_duration_mins": "Avg Mins"
    })
    p_disp["Attributed Revenue ($)"] = p_disp["Attributed Revenue ($)"].apply(lambda x: f"${x:,.2f}")
    for c in ["Encounters", "Patients", "Acute Visits"]:
        p_disp[c] = p_disp[c].apply(lambda x: f"{x:,}")

    st.dataframe(p_disp, use_container_width=True, hide_index=True)

    # CSV Download
    p_csv = filtered_prov.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Provider Workload CSV",
        data=p_csv,
        file_name="provider_workload_metrics.csv",
        mime="text/csv"
    )
