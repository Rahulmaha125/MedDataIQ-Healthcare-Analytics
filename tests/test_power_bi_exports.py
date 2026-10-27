"""
MedDataIQ — Automated Unit Tests for Power BI Layer (Phase 6)
Verifies exported dimensional and fact tables, primary/foreign key integrity,
financial parity guarantees, duplicate protection, and Power BI assets.
"""

import json
import unittest
from pathlib import Path
import pandas as pd

from src.config import POWER_BI_EXPORT_DIR


class TestPowerBIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.export_dir = POWER_BI_EXPORT_DIR
        cls.dim_date = pd.read_csv(cls.export_dir / "Dim_Date.csv")
        cls.dim_patient = pd.read_csv(cls.export_dir / "Dim_Patient.csv")
        cls.dim_org = pd.read_csv(cls.export_dir / "Dim_Organization.csv")
        cls.dim_provider = pd.read_csv(cls.export_dir / "Dim_Provider.csv")
        cls.dim_payer = pd.read_csv(cls.export_dir / "Dim_Payer.csv")
        cls.fact_enc = pd.read_csv(cls.export_dir / "Fact_Encounter.csv")
        cls.fact_billing = pd.read_csv(cls.export_dir / "Fact_Billing.csv")
        cls.fact_recon = pd.read_csv(cls.export_dir / "Fact_Reconciliation.csv")
        cls.fact_dq = pd.read_csv(cls.export_dir / "Fact_DataQuality.csv")

    def test_file_existence(self):
        expected_files = [
            "Dim_Date.csv",
            "Dim_Patient.csv",
            "Dim_Organization.csv",
            "Dim_Provider.csv",
            "Dim_Payer.csv",
            "Fact_Encounter.csv",
            "Fact_Billing.csv",
            "Fact_Reconciliation.csv",
            "Fact_DataQuality.csv",
            "export_validation_summary.json"
        ]
        for fname in expected_files:
            p = self.export_dir / fname
            self.assertTrue(p.exists(), f"Missing export file: {fname}")
            self.assertGreater(p.stat().st_size, 0, f"File is empty: {fname}")

    def test_row_counts(self):
        self.assertEqual(len(self.dim_date), 1461)
        self.assertEqual(len(self.dim_patient), 1000)
        self.assertEqual(len(self.dim_org), 6)
        self.assertEqual(len(self.dim_provider), 30)
        self.assertEqual(len(self.dim_payer), 7)
        self.assertEqual(len(self.fact_enc), 5730)
        self.assertEqual(len(self.fact_billing), 5770)
        self.assertEqual(len(self.fact_recon), 6010)
        self.assertEqual(len(self.fact_dq), 43)

    def test_primary_key_uniqueness_and_nulls(self):
        pks = [
            (self.dim_date, "date_key"),
            (self.dim_patient, "patient_id"),
            (self.dim_org, "organization_id"),
            (self.dim_provider, "provider_id"),
            (self.dim_payer, "payer_id"),
            (self.fact_enc, "encounter_id"),
            (self.fact_billing, "claim_id"),
            (self.fact_recon, "reconciliation_key")
        ]
        for df, col in pks:
            self.assertEqual(df[col].isna().sum(), 0, f"Found nulls in PK {col}")
            self.assertEqual(df[col].nunique(), len(df), f"PK {col} is not unique")

    def test_exact_financial_parity(self):
        enc_cost = round(self.fact_enc["total_claim_cost"].sum(), 2)
        recon_enc_cost = round(self.fact_recon["clinical_encounter_cost"].sum(), 2)
        self.assertEqual(enc_cost, 4501299.15)
        self.assertEqual(recon_enc_cost, 4501299.15)
        self.assertEqual(enc_cost, recon_enc_cost)

        billed_claims = round(self.fact_billing["billed_amount"].sum(), 2)
        recon_billed = round(self.fact_recon["claim_billed_amount"].sum(), 2)
        self.assertEqual(billed_claims, 4560904.11)
        self.assertEqual(recon_billed, 4560904.11)
        self.assertEqual(billed_claims, recon_billed)

        net_variance = round(self.fact_recon["variance_amount"].sum(), 2)
        self.assertEqual(net_variance, 59604.96)
        self.assertEqual(net_variance, round(billed_claims - enc_cost, 2))

    def test_duplicate_claims_no_double_counting(self):
        dup_rows = self.fact_recon[self.fact_recon["reconciliation_status"] == "DUPLICATE_CLAIM"]
        self.assertEqual(len(dup_rows), 240)
        # Clinical cost for duplicate claims must be strictly 0.00 to prevent double-counting
        self.assertEqual(round(dup_rows["clinical_encounter_cost"].sum(), 2), 0.00)
        # Duplicate exposure is the exact sum of billed amounts for these duplicate claims
        self.assertEqual(round(dup_rows["claim_billed_amount"].sum(), 2), 189343.57)

    def test_unbilled_and_unmatched_records_preserved(self):
        unbilled = self.fact_recon[self.fact_recon["reconciliation_status"] == "UNBILLED_SERVICE"]
        self.assertEqual(len(unbilled), 240)
        self.assertTrue(unbilled["claim_id"].isna().all())
        self.assertEqual(round(unbilled["claim_billed_amount"].sum(), 2), 0.00)
        self.assertEqual(round(unbilled["clinical_encounter_cost"].sum(), 2), 224443.42)

        unmatched = self.fact_recon[self.fact_recon["reconciliation_status"] == "UNMATCHED_BILL"]
        self.assertEqual(len(unmatched), 40)
        self.assertTrue(unmatched["encounter_id"].isna().all())
        self.assertEqual(round(unmatched["clinical_encounter_cost"].sum(), 2), 0.00)
        self.assertEqual(round(unmatched["claim_billed_amount"].sum(), 2), 36700.33)

    def test_foreign_key_referential_integrity(self):
        # Patient FKs
        patient_keys = set(self.dim_patient["patient_id"])
        self.assertTrue(set(self.fact_enc["patient_id"]).issubset(patient_keys))
        self.assertTrue(set(self.fact_billing["patient_id"]).issubset(patient_keys))
        recon_patients = set(self.fact_recon["patient_id"].dropna())
        self.assertTrue(recon_patients.issubset(patient_keys))

        # Provider FKs
        provider_keys = set(self.dim_provider["provider_id"])
        self.assertTrue(set(self.fact_enc["provider_id"]).issubset(provider_keys))
        self.assertTrue(set(self.fact_billing["provider_id"]).issubset(provider_keys))

        # Date dimension FKs
        date_keys = set(self.dim_date["date_key"])
        self.assertTrue(set(self.fact_enc["encounter_date"]).issubset(date_keys))
        self.assertTrue(set(self.fact_billing["service_date"]).issubset(date_keys))
        self.assertTrue(set(self.fact_recon["service_date"]).issubset(date_keys))

    def test_power_bi_theme_and_docs_assets(self):
        base_dir = Path("D:/MedDataIQ/power_bi")
        theme_path = base_dir / "meddataiq_theme.json"
        dax_path = base_dir / "DAX_MEASURES.md"
        guide_path = base_dir / "POWER_BI_GUIDE.md"

        self.assertTrue(theme_path.exists())
        self.assertTrue(dax_path.exists())
        self.assertTrue(guide_path.exists())

        with open(theme_path, "r", encoding="utf-8") as f:
            theme_json = json.load(f)
        self.assertIn("name", theme_json)
        self.assertIn("dataColors", theme_json)
        self.assertEqual(theme_json["name"], "MedDataIQ Futuristic Dark")


if __name__ == "__main__":
    unittest.main()
