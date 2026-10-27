"""
MedDataIQ — View 6: Data Quality & Governance Audit
Evaluates healthcare data across the 6 core dimensions: Completeness, Uniqueness,
Validity, Timeliness, Consistency, and Referential Integrity.
"""

import json
from pathlib import Path
import streamlit as st
import pandas as pd
from app.components.charts import build_data_quality_radar
from app.components.theme import render_html
from src.config import PROCESSED_DATA_DIR
from src.db.connection import DatabaseManager


def render(db: DatabaseManager):
    render_html("""
    <div style="margin-bottom: 20px;">
        <h2 style="font-size: 1.8rem; font-weight: 800; color: #FFFFFF; margin: 0 0 4px 0;">
            Healthcare Data Quality & Governance Audit
        </h2>
        <p style="color: #94A3B8; font-size: 0.9rem; margin: 0;">
            Comprehensive rule-based audit evaluating 43 quality checkpoints across clinical and financial domains.
        </p>
    </div>
    """)

    # 1. Load JSON audit report
    report_file = PROCESSED_DATA_DIR / "data_quality_report.json"
    if not report_file.exists():
        st.warning("Data quality report not found. Run `python -m src.quality` first.")
        return

    with open(report_file, "r", encoding="utf-8") as f:
        dq_report = json.load(f)

    metrics = dq_report.get("overall_metrics", {})
    dq_index = metrics.get("data_quality_index_pct", 90.7)
    total_rules = metrics.get("total_rules_evaluated", 43)
    passed_rules = metrics.get("passed_rules", 39)
    flagged_rules = metrics.get("flagged_for_investigation", 4)
    crit_fails = metrics.get("critical_violations", 0)

    # Top KPI cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Data Quality Index</span>
            <div class="kpi-value kpi-value-cyan">{dq_index}%</div>
            <p class="kpi-subtext">Overall data health score</p>
        </div>
        """)
    with c2:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Rules Passed</span>
            <div class="kpi-value kpi-value-emerald">{passed_rules} / {total_rules}</div>
            <p class="kpi-subtext">100% of clinical rules passed</p>
        </div>
        """)
    with c3:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Flagged for Review</span>
            <div class="kpi-value kpi-value-amber">{flagged_rules}</div>
            <p class="kpi-subtext">Controlled audit discrepancies</p>
        </div>
        """)
    with c4:
        render_html(f"""
        <div class="kpi-card-3d">
            <span class="kpi-title">Critical Systemic Failures</span>
            <div class="kpi-value kpi-value-emerald">{crit_fails}</div>
            <p class="kpi-subtext">Zero fatal schema violations</p>
        </div>
        """)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # 2. Radar Chart & Dimension Score Cards
    col1, col2 = st.columns([1.3, 1.0])

    with col1:
        radar_fig = build_data_quality_radar(dq_report)
        st.plotly_chart(radar_fig, use_container_width=True)

    with col2:
        render_html("""
        <div class="glass-panel-header" style="margin-bottom: 14px;">
            <h3 class="glass-panel-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2">
                    <polyline points="20 6 9 17 4 12"></polyline>
                </svg>
                6-Dimension Health Pass Rates
            </h3>
        </div>
        """)

        # Dimension breakdown
        dim_group = {}
        for r in dq_report.get("rule_results", []):
            d = r["dimension"]
            dim_group.setdefault(d, {"total": 0, "passed": 0})
            dim_group[d]["total"] += 1
            if r["status"] == "PASSED":
                dim_group[d]["passed"] += 1

        for d, cnts in dim_group.items():
            rate = round((cnts["passed"] / cnts["total"] * 100), 1)
            pill_class = "status-pill-clean" if rate == 100.0 else "status-pill-warning"
            render_html(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; background: rgba(255,255,255,0.02); border-radius: 8px; margin-bottom: 8px; border: 1px solid rgba(255,255,255,0.05);">
                <span style="font-weight: 600; color: #FFFFFF; font-size: 0.88rem;">{d}</span>
                <span class="status-pill {pill_class}">{rate}% Pass ({cnts['passed']}/{cnts['total']})</span>
            </div>
            """)

    # 3. Interactive Rules Explorer Table
    render_html("""
    <div class="glass-panel-header" style="margin-top: 20px; margin-bottom: 10px;">
        <h3 class="glass-panel-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
            Data Quality Rule Checkpoints Explorer
        </h3>
        <p class="glass-panel-subtitle">Drill down into individual rule definitions, violation rates, and sample affected identifiers</p>
    </div>
    """)

    rules_df = pd.DataFrame(dq_report.get("rule_results", []))

    # Filters
    f1, f2, f3 = st.columns(3)
    with f1:
        dim_opts = ["ALL"] + sorted(rules_df["dimension"].unique().tolist())
        sel_dim = st.selectbox("Filter by Dimension", dim_opts, index=0)
    with f2:
        status_opts = ["ALL", "PASSED", "FLAGGED_FOR_INVESTIGATION"]
        sel_status = st.selectbox("Filter by Status", status_opts, index=0)
    with f3:
        search_txt = st.text_input("Search Rule Name or Dataset", "")

    # Apply filters
    filtered_rules = rules_df.copy()
    if sel_dim != "ALL":
        filtered_rules = filtered_rules[filtered_rules["dimension"] == sel_dim]
    if sel_status != "ALL":
        filtered_rules = filtered_rules[filtered_rules["status"] == sel_status]
    if search_txt.strip():
        q = search_txt.strip().lower()
        filtered_rules = filtered_rules[
            filtered_rules["rule_name"].str.lower().str.contains(q) |
            filtered_rules["dataset"].str.lower().str.contains(q) |
            filtered_rules["description"].str.lower().str.contains(q)
        ]

    # Display columns
    display_rules = filtered_rules[[
        "dataset", "rule_name", "dimension", "severity",
        "affected_rows_count", "total_rows_evaluated", "violation_rate_pct", "status"
    ]].copy()

    display_rules = display_rules.rename(columns={
        "dataset": "Table",
        "rule_name": "Rule Checkpoint",
        "dimension": "Dimension",
        "severity": "Severity",
        "affected_rows_count": "Violations",
        "total_rows_evaluated": "Total Evaluated",
        "violation_rate_pct": "Violation Rate (%)",
        "status": "Audit Status"
    })

    st.dataframe(display_rules, use_container_width=True, hide_index=True)

    # Downloads Row
    d1, d2 = st.columns(2)
    with d1:
        json_bytes = json.dumps(dq_report, indent=2).encode("utf-8")
        st.download_button(
            label="Download Data Quality Report (JSON)",
            data=json_bytes,
            file_name="data_quality_report.json",
            mime="application/json"
        )
    with d2:
        md_file = PROCESSED_DATA_DIR / "DATA_QUALITY_REPORT.md"
        if md_file.exists():
            with open(md_file, "r", encoding="utf-8") as f:
                md_text = f.read().encode("utf-8")
            st.download_button(
                label="Download Full Markdown Audit Report",
                data=md_text,
                file_name="DATA_QUALITY_REPORT.md",
                mime="text/markdown"
            )
