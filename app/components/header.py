"""
MedDataIQ — Hero Header Component
Renders the 3D-inspired glassmorphic header banner with live engine status.
"""

from datetime import datetime
import streamlit as st
from app.components.theme import render_html
from src.db.connection import DatabaseManager


def render_hero_header(db_status: dict = None):
    """Renders the executive dashboard hero banner."""
    if not db_status:
        db = DatabaseManager()
        db_status = db.get_status()

    engine_name = "PostgreSQL 18" if db_status.get("postgresql_reachable") else "SQLite Data Mart"
    refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    hero_html = f"""
    <div class="hero-container">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 20px;">
            <div>
                <div class="hero-title">
                    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                    </svg>
                    <span>MedDataIQ</span>
                    <span style="font-size: 1.1rem; font-weight: 500; color: #38BDF8; margin-left: 4px;">HealthTech SaaS</span>
                </div>
                <p class="hero-subtitle">
                    Clinical Operations • Revenue Integrity • Service-to-Billing Reconciliation
                </p>
            </div>
            <div style="display: flex; flex-direction: column; align-items: flex-end; gap: 8px;">
                <div class="system-badge">
                    <span class="status-pulse-dot"></span>
                    <span>ENGINE: {engine_name}</span>
                </div>
                <div style="font-size: 0.76rem; color: #64748B; font-weight: 500;">
                    Data Mart Synced: <span style="color: #94A3B8; font-family: monospace;">{refresh_time}</span>
                </div>
            </div>
        </div>
    </div>
    """
    render_html(hero_html)
