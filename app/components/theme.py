"""
MedDataIQ — Chart Theming & Formatting Helpers
Provides custom dark Plotly templates, color constants, and formatters.
"""

from typing import Dict, Any
import plotly.graph_objects as go
import plotly.io as pio

# Theme Colors
COLORS = {
    "cyan": "#00F2FE",
    "blue": "#3B82F6",
    "emerald": "#10B981",
    "amber": "#F59E0B",
    "rose": "#F43F5E",
    "indigo": "#6366F1",
    "teal": "#14B8A6",
    "purple": "#8B5CF6",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
    "border_subtle": "rgba(255, 255, 255, 0.08)",
    "grid_color": "rgba(255, 255, 255, 0.06)",
}

# Category Color Mapping
STATUS_COLORS = {
    "CLEAN_MATCH": "#10B981",       # Emerald
    "AMOUNT_VARIANCE": "#F59E0B",   # Amber
    "TIMING_SKEW": "#3B82F6",       # Electric Blue
    "DUPLICATE_CLAIM": "#F43F5E",   # Rose
    "UNBILLED_SERVICE": "#EC4899",  # Pink
    "UNMATCHED_BILL": "#8B5CF6",    # Violet
}


def apply_dark_theme(fig: go.Figure, title: str = None, height: int = 380) -> go.Figure:
    """Applies high-end dark glassmorphism styling to any Plotly figure."""
    layout_update: Dict[str, Any] = {
        "paper_bgcolor": "rgba(0, 0, 0, 0)",
        "plot_bgcolor": "rgba(0, 0, 0, 0)",
        "height": height,
        "margin": dict(l=40, r=30, t=50 if title else 20, b=40),
        "font": dict(
            family="Plus Jakarta Sans, -apple-system, sans-serif",
            color=COLORS["text_secondary"],
            size=12
        ),
        "hoverlabel": dict(
            bgcolor="#0F172A",
            bordercolor="rgba(0, 242, 254, 0.4)",
            font=dict(
                family="Plus Jakarta Sans, sans-serif",
                color="#FFFFFF",
                size=12
            )
        ),
        "xaxis": dict(
            showgrid=True,
            gridcolor=COLORS["grid_color"],
            zeroline=False,
            color=COLORS["text_secondary"],
            tickfont=dict(size=11)
        ),
        "yaxis": dict(
            showgrid=True,
            gridcolor=COLORS["grid_color"],
            zeroline=False,
            color=COLORS["text_secondary"],
            tickfont=dict(size=11)
        ),
        "legend": dict(
            bgcolor="rgba(15, 23, 42, 0.5)",
            bordercolor=COLORS["border_subtle"],
            borderwidth=1,
            font=dict(color=COLORS["text_secondary"], size=11)
        )
    }

    if title:
        layout_update["title"] = dict(
            text=f"<b>{title}</b>",
            font=dict(color="#FFFFFF", size=15),
            x=0.02,
            y=0.96
        )

    fig.update_layout(**layout_update)
    return fig


def format_currency(value: float, compact: bool = False) -> str:
    """Formats numeric values to currency format."""
    if value is None:
        return "$0.00"
    if compact:
        abs_v = abs(value)
        sign = "-" if value < 0 else ""
        if abs_v >= 1_000_000:
            return f"{sign}${abs_v / 1_000_000:.2f}M"
        elif abs_v >= 1_000:
            return f"{sign}${abs_v / 1_000:.1f}K"
        return f"{sign}${abs_v:,.2f}"
    return f"${value:,.2f}"


def format_number(value: Any) -> str:
    """Formats integers with thousands separators cleanly without trailing .0."""
    if value is None:
        return "0"
    try:
        return f"{int(round(float(value))):,}"
    except (ValueError, TypeError):
        return str(value)


def render_html(html_str: str):
    """
    Renders custom HTML safely without Markdown treating 4+ space indents as code blocks.
    Prefers native st.html; falls back to dedented st.markdown if unavailable.
    """
    import textwrap
    import streamlit as st
    cleaned = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(cleaned)
    else:
        st.markdown(cleaned, unsafe_allow_html=True)

