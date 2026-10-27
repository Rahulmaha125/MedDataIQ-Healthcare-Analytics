"""
MedDataIQ — 3D-Inspired Glassmorphic KPI Cards
Renders 6 executive healthtech metric cards with depth, glowing borders, and icons.
"""

from typing import Dict, Any
import streamlit as st
from app.components.theme import format_currency, format_number, render_html


def render_kpi_cards(metrics: Dict[str, Any]):
    """
    Renders the six executive 3D KPI cards.
    Values are dynamically derived from database aggregations.
    """
    pts = format_number(metrics.get("total_patients", 1000))
    encs = format_number(metrics.get("total_encounters", 5730))
    clin_cost = format_currency(metrics.get("total_clinical_cost", 4501299.15), compact=True)
    billed_amt = format_currency(metrics.get("total_billed_amount", 4560904.11), compact=True)
    net_var = format_currency(metrics.get("net_variance", 59604.96), compact=True)
    dup_exp = format_currency(metrics.get("duplicate_exposure", 189343.57), compact=True)

    kpi_html = f"""
    <div class="kpi-grid">
        <!-- 1. Total Patients -->
        <div class="kpi-card-3d">
            <div class="kpi-card-top">
                <span class="kpi-title">Total Patients</span>
                <div class="kpi-icon-badge" style="background: rgba(0, 242, 254, 0.08); border-color: rgba(0, 242, 254, 0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00F2FE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                    </svg>
                </div>
            </div>
            <div class="kpi-value kpi-value-cyan">{pts}</div>
            <p class="kpi-subtext">Active cohort demographics in EHR</p>
        </div>

        <!-- 2. Total Encounters -->
        <div class="kpi-card-3d">
            <div class="kpi-card-top">
                <span class="kpi-title">Total Encounters</span>
                <div class="kpi-icon-badge" style="background: rgba(59, 130, 246, 0.08); border-color: rgba(59, 130, 246, 0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3B82F6" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
                        <line x1="16" y1="2" x2="16" y2="6"></line>
                        <line x1="8" y1="2" x2="8" y2="6"></line>
                        <line x1="3" y1="10" x2="21" y2="10"></line>
                    </svg>
                </div>
            </div>
            <div class="kpi-value kpi-value-cyan">{encs}</div>
            <p class="kpi-subtext">Wellness, urgent, acute & inpatient</p>
        </div>

        <!-- 3. Total Clinical Cost -->
        <div class="kpi-card-3d">
            <div class="kpi-card-top">
                <span class="kpi-title">Clinical Cost</span>
                <div class="kpi-icon-badge" style="background: rgba(16, 185, 129, 0.08); border-color: rgba(16, 185, 129, 0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#10B981" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="12" y1="1" x2="12" y2="23"></line>
                        <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
                    </svg>
                </div>
            </div>
            <div class="kpi-value kpi-value-emerald">{clin_cost}</div>
            <p class="kpi-subtext">True clinical service delivery baseline</p>
        </div>

        <!-- 4. Total Billed Amount -->
        <div class="kpi-card-3d">
            <div class="kpi-card-top">
                <span class="kpi-title">Billed Amount</span>
                <div class="kpi-icon-badge" style="background: rgba(99, 102, 241, 0.08); border-color: rgba(99, 102, 241, 0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#818CF8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="16" y1="13" x2="8" y2="13"></line>
                        <line x1="16" y1="17" x2="8" y2="17"></line>
                        <polyline points="10 9 9 9 8 9"></polyline>
                    </svg>
                </div>
            </div>
            <div class="kpi-value">{billed_amt}</div>
            <p class="kpi-subtext">Gross claims submitted across payers</p>
        </div>

        <!-- 5. Net Financial Variance -->
        <div class="kpi-card-3d">
            <div class="kpi-card-top">
                <span class="kpi-title">Net Variance</span>
                <div class="kpi-icon-badge" style="background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                        <polyline points="17 6 23 6 23 12"></polyline>
                    </svg>
                </div>
            </div>
            <div class="kpi-value kpi-value-amber">{net_var}</div>
            <p class="kpi-subtext">Net differential (Billed vs. Clinical)</p>
        </div>

        <!-- 6. Duplicate Claim Exposure -->
        <div class="kpi-card-3d">
            <div class="kpi-card-top">
                <span class="kpi-title">Duplicate Exposure</span>
                <div class="kpi-icon-badge" style="background: rgba(244, 63, 94, 0.08); border-color: rgba(244, 63, 94, 0.25);">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#F43F5E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                        <line x1="12" y1="9" x2="12" y2="13"></line>
                        <line x1="12" y1="17" x2="12.01" y2="17"></line>
                    </svg>
                </div>
            </div>
            <div class="kpi-value kpi-value-rose">{dup_exp}</div>
            <p class="kpi-subtext">240 redundant claims requiring void</p>
        </div>
    </div>
    """
    render_html(kpi_html)
