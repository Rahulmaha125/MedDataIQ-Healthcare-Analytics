"""
MedDataIQ — Automated Unit Tests for Reconciliation Engine (Phase 4)
Verifies KPI calculation, discrepancy categorizations, financial parity,
and investigation queue generation.
"""

import json
import unittest
from pathlib import Path
import pandas as pd

from src.config import PROCESSED_DATA_DIR
from src.db.connection import DatabaseManager
from src.reconciliation import ReconciliationEngine


class TestReconciliationEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = DatabaseManager()
        cls.engine = ReconciliationEngine(db_manager=cls.db)
        cls.report = cls.engine.run_reconciliation_audit()
        cls.recon_df = cls.engine.load_reconciliation_data()

    def test_total_record_and_category_counts(self):
        self.assertEqual(len(self.recon_df), 6010)
        counts = self.recon_df["reconciliation_status"].value_counts().to_dict()
        self.assertEqual(counts["CLEAN_MATCH"], 4567)
        self.assertEqual(counts["AMOUNT_VARIANCE"], 539)
        self.assertEqual(counts["TIMING_SKEW"], 384)
        self.assertEqual(counts["UNBILLED_SERVICE"], 240)
        self.assertEqual(counts["DUPLICATE_CLAIM"], 240)
        self.assertEqual(counts["UNMATCHED_BILL"], 40)

    def test_exact_financial_parity(self):
        kpis = self.report["executive_kpis"]
        # Total clinical cost must match fact_encounters
        enc_cost = float(self.db.execute_query("SELECT SUM(total_claim_cost) AS s FROM fact_encounters")["s"].iloc[0])
        self.assertAlmostEqual(kpis["total_clinical_cost"], round(enc_cost, 2), places=2)

        # Total billed amount must match fact_billing_claims
        claims_billed = float(self.db.execute_query("SELECT SUM(billed_amount) AS s FROM fact_billing_claims")["s"].iloc[0])
        self.assertAlmostEqual(kpis["total_billed_amount"], round(claims_billed, 2), places=2)

        # Net variance must equal claims_billed - enc_cost
        expected_var = round(claims_billed - enc_cost, 2)
        self.assertAlmostEqual(kpis["net_variance"], expected_var, places=2)

    def test_investigation_queue_export(self):
        queue_file = PROCESSED_DATA_DIR / "audit_investigation_queue.csv"
        self.assertTrue(queue_file.exists())
        queue_df = pd.read_csv(queue_file)
        self.assertEqual(len(queue_df), 1443)  # 6010 - 4567 clean matches
        self.assertIn("recommended_action", queue_df.columns)
        self.assertIn("investigation_priority", queue_df.columns)
        self.assertNotIn("CLEAN_MATCH", queue_df["reconciliation_status"].values)

    def test_audit_reports_generated(self):
        json_file = PROCESSED_DATA_DIR / "reconciliation_summary.json"
        md_file = PROCESSED_DATA_DIR / "RECONCILIATION_REPORT.md"
        self.assertTrue(json_file.exists())
        self.assertTrue(md_file.exists())
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertIn("executive_kpis", data)
        self.assertIn("category_breakdown", data)


if __name__ == "__main__":
    unittest.main()
