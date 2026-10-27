"""
MedDataIQ — Interactive Plotly Charts
Renders dark-themed, glassmorphic healthcare analytics visualizations:
- Monthly Clinical Cost vs Billed Amount
- Billing Reconciliation Donut & Exposure Waterfall
- Duplicate & Unbilled Exposure
- Provider Workload & Specialty Ranking
- 6-Dimension Data Quality Radar / Bullet Chart
"""

from typing import List, Dict, Any
import pandas as pd
import plotly.graph_objects as go
from app.components.theme import apply_dark_theme, COLORS, STATUS_COLORS


def build_monthly_trend_chart(monthly_df: pd.DataFrame) -> go.Figure:
    """Monthly clinical cost vs billed amount trend."""
    fig = go.Figure()

    df = monthly_df.sort_values(by="year_month")

    # Clinical Cost Area
    fig.add_trace(go.Scatter(
        x=df["year_month"],
        y=df["total_billed_cost"],
        name="Clinical Encounter Cost",
        mode="lines",
        line=dict(color=COLORS["cyan"], width=3),
        fill="tozeroy",
        fillcolor="rgba(0, 242, 254, 0.08)",
        hovertemplate="<b>%{x}</b><br>Clinical Cost: $%{y:,.2f}<extra></extra>"
    ))

    # Payer Coverage Line
    fig.add_trace(go.Scatter(
        x=df["year_month"],
        y=df["total_payer_coverage"],
        name="Insurance Coverage",
        mode="lines+markers",
        line=dict(color=COLORS["emerald"], width=2.5, dash="dot"),
        marker=dict(size=5, color=COLORS["emerald"]),
        hovertemplate="<b>%{x}</b><br>Payer Coverage: $%{y:,.2f}<extra></extra>"
    ))

    fig = apply_dark_theme(fig, title="Monthly Clinical Volume & Reimbursement Trend", height=380)
    fig.update_layout(
        xaxis_title="Billing Period (Year-Month)",
        yaxis_title="Total Financial Value ($)",
        hovermode="x unified"
    )
    return fig


def build_reconciliation_donut(breakdown_df: pd.DataFrame) -> go.Figure:
    """Reconciliation category distribution donut chart."""
    colors = [STATUS_COLORS.get(status, COLORS["blue"]) for status in breakdown_df["reconciliation_status"]]

    fig = go.Figure(data=[go.Pie(
        labels=breakdown_df["reconciliation_status"],
        values=breakdown_df["record_count"],
        hole=0.62,
        marker=dict(colors=colors, line=dict(color="#0F172A", width=2)),
        textinfo="percent+label",
        textposition="outside",
        hovertemplate="<b>%{label}</b><br>Records: %{value:,}<br>Share: %{percent}<extra></extra>"
    )])

    fig = apply_dark_theme(fig, title="Audit Discrepancy Distribution", height=380)
    fig.update_layout(
        showlegend=False,
        annotations=[dict(
            text="<b>6,010</b><br><span style='font-size:11px;color:#94A3B8'>Audited Rows</span>",
            x=0.5, y=0.5, font_size=16, showarrow=False, font_color="#FFFFFF"
        )]
    )
    return fig


def build_variance_exposure_bar(breakdown_df: pd.DataFrame) -> go.Figure:
    """Net dollar variance across discrepancy categories."""
    df = breakdown_df.sort_values(by="total_variance", ascending=True)
    colors = [COLORS["emerald"] if v >= 0 else COLORS["rose"] for v in df["total_variance"]]

    fig = go.Figure(go.Bar(
        y=df["reconciliation_status"],
        x=df["total_variance"],
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color="rgba(255,255,255,0.15)", width=1)
        ),
        hovertemplate="<b>%{y}</b><br>Financial Variance: $%{x:,.2f}<extra></extra>"
    ))

    fig = apply_dark_theme(fig, title="Net Financial Variance by Audit Category ($)", height=380)
    fig.update_layout(
        xaxis_title="Dollar Variance ($)",
        yaxis_title=None,
        xaxis=dict(zeroline=True, zerolinecolor="rgba(255, 255, 255, 0.2)")
    )
    return fig


def build_provider_workload_bar(provider_df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """Top providers ranked by total clinical encounters or revenue."""
    df = provider_df.sort_values(by="total_encounters", ascending=True).tail(top_n)

    fig = go.Figure(go.Bar(
        y=df["provider_name"],
        x=df["total_encounters"],
        orientation="h",
        marker=dict(
            color=COLORS["blue"],
            line=dict(color=COLORS["cyan"], width=1)
        ),
        text=df["specialty"],
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color="#FFFFFF", size=10),
        hovertemplate="<b>%{y}</b><br>Specialty: %{text}<br>Encounters: %{x:,}<extra></extra>"
    ))

    fig = apply_dark_theme(fig, title=f"Top {top_n} Clinicians by Clinical Workload", height=400)
    fig.update_layout(
        xaxis_title="Encounter Volume",
        yaxis_title=None
    )
    return fig


def build_data_quality_radar(dq_report: dict) -> go.Figure:
    """Visualizes Data Quality Health Index across the 6 core dimensions."""
    dimensions = ["Completeness", "Uniqueness", "Validity", "Timeliness", "Consistency", "Referential Integrity"]
    
    # Calculate pass rate per dimension from JSON audit report
    dim_scores = {}
    for r in dq_report.get("rule_results", []):
        dim = r["dimension"]
        dim_scores.setdefault(dim, {"total": 0, "passed": 0})
        dim_scores[dim]["total"] += 1
        if r["status"] == "PASSED":
            dim_scores[dim]["passed"] += 1

    scores = [
        round((dim_scores[d]["passed"] / dim_scores[d]["total"] * 100), 1) if d in dim_scores and dim_scores[d]["total"] > 0 else 100.0
        for d in dimensions
    ]

    # Close the radar loop
    radar_dims = dimensions + [dimensions[0]]
    radar_scores = scores + [scores[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=radar_scores,
        theta=radar_dims,
        fill="toself",
        fillcolor="rgba(0, 242, 254, 0.15)",
        line=dict(color=COLORS["cyan"], width=2.5),
        marker=dict(size=6, color=COLORS["cyan"]),
        hovertemplate="<b>%{theta}</b><br>DQ Score: %{r}%<extra></extra>"
    ))

    fig = apply_dark_theme(fig, title="6-Dimension Healthcare Data Quality Radar (%)", height=380)
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0, 0, 0, 0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                color=COLORS["text_secondary"],
                gridcolor=COLORS["grid_color"]
            ),
            angularaxis=dict(
                color=COLORS["text_primary"],
                gridcolor=COLORS["grid_color"]
            )
        ),
        showlegend=False
    )
    return fig
