"""
MedDataIQ — Automated Tests for Phase 5 Streamlit Dashboard Views & Visualizations
Verifies that all 7 dashboard view modules load data, calculate metrics,
and generate Plotly figures cleanly without errors.
"""

import unittest
import pandas as pd

from src.db.connection import DatabaseManager
from app.components.theme import apply_dark_theme, format_currency, format_number
from app.components.charts import (
    build_monthly_trend_chart,
    build_reconciliation_donut,
    build_variance_exposure_bar,
    build_provider_workload_bar,
    build_data_quality_radar
)


class TestDashboardViewsAndComponents(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()

    def test_theme_formatters(self):
        self.assertEqual(format_currency(1234.56), "$1,234.56")
        self.assertEqual(format_currency(4500000, compact=True), "$4.50M")
        self.assertEqual(format_currency(59600, compact=True), "$59.6K")
        self.assertEqual(format_number(1000), "1,000")

    def test_monthly_trend_chart_generation(self):
        df = self.db.execute_query("SELECT * FROM v_kpi_executive_monthly ORDER BY year_month")
        fig = build_monthly_trend_chart(df)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 2)  # Two traces: clinical cost and payer coverage

    def test_reconciliation_donut_generation(self):
        df = self.db.execute_query("""
            SELECT reconciliation_status, COUNT(*) as record_count 
            FROM v_billing_reconciliation_summary 
            GROUP BY reconciliation_status
        """)
        fig = build_reconciliation_donut(df)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)
        self.assertEqual(len(fig.data[0].labels), 6)  # 6 reconciliation categories

    def test_variance_exposure_bar_chart(self):
        df = self.db.execute_query("""
            SELECT 
                reconciliation_status,
                ROUND(SUM(variance_amount), 2) as total_variance
            FROM v_billing_reconciliation_summary
            GROUP BY reconciliation_status
        """)
        fig = build_variance_exposure_bar(df)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 1)

    def test_provider_workload_chart(self):
        df = self.db.execute_query("SELECT * FROM v_provider_workload ORDER BY total_encounters DESC")
        fig = build_provider_workload_bar(df, top_n=10)
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data[0].x), 10)

    def test_data_quality_radar_chart(self):
        import json
        from src.config import PROCESSED_DATA_DIR
        report_file = PROCESSED_DATA_DIR / "data_quality_report.json"
        self.assertTrue(report_file.exists())
        with open(report_file, "r", encoding="utf-8") as f:
            dq_data = json.load(f)
        fig = build_data_quality_radar(dq_data)
        self.assertIsNotNone(fig)
        # Radar should have 6 dimensions plus closed loop = 7 theta points
        self.assertEqual(len(fig.data[0].theta), 7)

    def test_unbilled_services_query(self):
        unbilled_df = self.db.execute_query("""
            SELECT COUNT(*) as cnt, SUM(total_claim_cost) as total_unbilled
            FROM fact_encounters
            WHERE encounter_id NOT IN (
                SELECT DISTINCT encounter_id FROM fact_billing_claims WHERE encounter_id IS NOT NULL
            )
        """)
        cnt = int(unbilled_df["cnt"].iloc[0])
        unbilled_sum = float(unbilled_df["total_unbilled"].iloc[0])
        self.assertEqual(cnt, 240)
        self.assertAlmostEqual(unbilled_sum, 224443.42, places=2)

    def test_duplicate_claims_query(self):
        dup_df = self.db.execute_query("""
            SELECT COUNT(*) as cnt, SUM(billed_amount) as total_billed
            FROM fact_billing_claims
            WHERE audit_category = 'DUPLICATE_CLAIM' OR claim_number LIKE '%-DUP'
        """)
        cnt = int(dup_df["cnt"].iloc[0])
        dup_sum = float(dup_df["total_billed"].iloc[0])
        self.assertEqual(cnt, 240)
        self.assertAlmostEqual(dup_sum, 189343.57, places=2)

    def test_unmatched_claims_query(self):
        unmatched_df = self.db.execute_query("""
            SELECT COUNT(*) as cnt, SUM(billed_amount) as total_billed
            FROM fact_billing_claims
            WHERE encounter_id NOT IN (SELECT encounter_id FROM fact_encounters)
        """)
        cnt = int(unmatched_df["cnt"].iloc[0])
        unmatched_sum = float(unmatched_df["total_billed"].iloc[0])
        self.assertEqual(cnt, 40)
        self.assertAlmostEqual(unmatched_sum, 36700.33, places=2)

    def test_hospital_connect_mart_summary(self):
        from app.views.hospital_connect import test_socket_connection
        summary = self.db.execute_query("""
            SELECT 
                (SELECT COUNT(*) FROM dim_organizations) as facility_count,
                (SELECT COUNT(*) FROM dim_providers) as provider_count,
                (SELECT COUNT(*) FROM fact_encounters) as encounter_count,
                (SELECT COUNT(*) FROM fact_billing_claims) as claims_count,
                (SELECT ROUND(SUM(total_claim_cost), 2) FROM fact_encounters) as clinical_spend,
                (SELECT ROUND(SUM(billed_amount), 2) FROM fact_billing_claims) as billed_spend
            """).iloc[0].to_dict()

        self.assertEqual(int(summary["facility_count"]), 6)
        self.assertEqual(int(summary["provider_count"]), 30)
        self.assertEqual(int(summary["encounter_count"]), 5730)
        self.assertEqual(int(summary["claims_count"]), 5770)
        self.assertAlmostEqual(float(summary["clinical_spend"]), 4501299.15, places=2)
        self.assertAlmostEqual(float(summary["billed_spend"]), 4560904.11, places=2)

        # Test socket connection function handling on closed port safely
        success, latency, msg = test_socket_connection("127.0.0.1", 59999, timeout=0.2)
        self.assertIsInstance(success, bool)
        self.assertIsInstance(latency, float)
        self.assertIsInstance(msg, str)


if __name__ == "__main__":
    unittest.main()
