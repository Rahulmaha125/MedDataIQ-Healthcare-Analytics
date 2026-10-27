"""
MedDataIQ — View 2: Service-to-Billing Reconciliation Hub
Comprehensive parity auditing between clinical service encounters and submitted claims.
"""

import streamlit as st
import pandas as pd
from app.components.charts import build_variance_exposure_bar
from app.components.theme import format_currency, format_number, render_html
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0;">
            Service-to-Billing Reconciliation Hub
        </h2>
        <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
            Automated cross-table audit comparing EHR encounters against submitted insurance claims to detect mismatches.
        </p>
    </div>
    """)

    # 1. Reconciliation Overview Metrics
    summary_df = db.execute_query("""
        SELECT 
            reconciliation_status,
            COUNT(*) as record_count,
            ROUND(SUM(clinical_encounter_cost), 2) as total_clinical_cost,
            ROUND(SUM(claim_billed_amount), 2) as total_billed_amount,
            ROUND(SUM(variance_amount), 2) as total_variance
        FROM v_billing_reconciliation_summary
        GROUP BY reconciliation_status
        ORDER BY ABS(total_variance) DESC
    """)

    total_audited = summary_df["record_count"].sum()
    clean_count = summary_df[summary_df["reconciliation_status"] == "CLEAN_MATCH"]["record_count"].sum()
    flagged_count = total_audited - clean_count
    clean_pct = round((clean_count / total_audited * 100), 2)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Audited Records</span>
            <div class="kpi-value kpi-value-cyan">{total_audited:,}</div>
            <p class="kpi-subtext">Total encounters & claims reconciled</p>
        </div>
        """)
    with col2:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Clean Parity Rate</span>
            <div class="kpi-value kpi-value-emerald">{clean_pct}%</div>
            <p class="kpi-subtext">{clean_count:,} records in perfect alignment</p>
        </div>
        """)
    with col3:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Discrepancy Rate</span>
            <div class="kpi-value kpi-value-amber">{100.0 - clean_pct:.2f}%</div>
            <p class="kpi-subtext">{flagged_count:,} records flagged for audit</p>
        </div>
        """)
    with col4:
        net_var = summary_df["total_variance"].sum()
        var_color = "kpi-value-amber" if net_var >= 0 else "kpi-value-rose"
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Net Financial Variance</span>
            <div class="kpi-value {var_color}">{format_currency(net_var, compact=True)}</div>
            <p class="kpi-subtext">Overall mathematical variance</p>
        </div>
        """)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # 2. Financial Variance Distribution Chart
    with st.container():
        render_html("""
        <div class="glass-panel-header">
            <h3 class="glass-panel-title">Net Financial Exposure by Audit Category</h3>
            <p class="glass-panel-subtitle">Total dollar risk breakdown across unbilled services, amount variances, and duplicate claims</p>
        </div>
        """)
        var_fig = build_variance_exposure_bar(summary_df)
        st.plotly_chart(var_fig, use_container_width=True)

    # 3. Interactive Reconciled Records Table with Filters
    render_html("""
    <div class="glass-panel-header" style="margin-top: 20px; margin-bottom: 10px;">
        <h3 class="glass-panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            Reconciled Transactions Explorer
        </h3>
        <p class="glass-panel-subtitle">Filter by audit discrepancy category, claim status, or search by claim or encounter ID</p>
    </div>
    """)

    # Filter Controls
    f_col1, f_col2, f_col3 = st.columns([1.5, 1.2, 1.3])
    with f_col1:
        category_options = ["ALL"] + sorted(summary_df["reconciliation_status"].unique().tolist())
        selected_category = st.selectbox("Reconciliation Category", category_options, index=0)
    with f_col2:
        status_options = ["ALL", "PAID", "DENIED", "PENDING_REVIEW", "APPEALED"]
        selected_status = st.selectbox("Claim Adjudication Status", status_options, index=0)
    with f_col3:
        search_query = st.text_input("Search (Claim # or UUID)", "")

    # Query Data
    base_sql = "SELECT * FROM v_billing_reconciliation_summary WHERE 1=1"
    params = []
    if selected_category != "ALL":
        base_sql += " AND reconciliation_status = ?"
        params.append(selected_category)
    if selected_status != "ALL":
        base_sql += " AND claim_status = ?"
        params.append(selected_status)
    if search_query.strip():
        base_sql += " AND (claim_number LIKE ? OR encounter_id LIKE ? OR patient_id LIKE ?)"
        q_term = f"%{search_query.strip()}%"
        params.extend([q_term, q_term, q_term])

    base_sql += " ORDER BY ABS(variance_amount) DESC LIMIT 500"
    records_df = db.execute_query(base_sql, params=tuple(params) if params else None)

    st.write(f"Showing **{len(records_df):,}** matching transactions (sorted by variance magnitude):")

    # Format Display Columns
    table_display = records_df[[
        "claim_number", "reconciliation_status", "service_date",
        "encounter_class", "clinical_encounter_cost", "claim_billed_amount",
        "variance_amount", "claim_status"
    ]].copy()

    table_display = table_display.rename(columns={
        "claim_number": "Claim #",
        "reconciliation_status": "Audit Category",
        "service_date": "Service Date",
        "encounter_class": "Class",
        "clinical_encounter_cost": "Clinical Cost ($)",
        "claim_billed_amount": "Billed ($)",
        "variance_amount": "Variance ($)",
        "claim_status": "Status"
    })

    for col in ["Clinical Cost ($)", "Billed ($)", "Variance ($)"]:
        table_display[col] = table_display[col].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")

    st.dataframe(table_display, use_container_width=True, hide_index=True)

    # Download Button
    csv_bytes = records_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download Filtered Reconciliation CSV",
        data=csv_bytes,
        file_name="meddataiq_reconciliation_export.csv",
        mime="text/csv"
    )
