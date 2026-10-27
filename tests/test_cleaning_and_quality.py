"""
MedDataIQ — Automated Unit Tests for Data Cleaning & Data Quality Engine
Phase 2: Verifies cleaning transformations, type standardizations,
duplicate detection without record deletion, and the 6 quality dimensions.
"""

import json
import unittest
from pathlib import Path
import pandas as pd

from src.config import PROCESSED_DATA_DIR, RAW_DATA_DIR
from src.cleaning import clean_patients, clean_encounters, clean_billing_claims, run_cleaning_pipeline
from src.quality import DataQualityAudit


class TestDataCleaning(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Load raw sample data
        cls.raw_patients = pd.read_csv(RAW_DATA_DIR / "patients.csv")
        cls.raw_encounters = pd.read_csv(RAW_DATA_DIR / "encounters.csv")
        cls.raw_claims = pd.read_csv(RAW_DATA_DIR / "billing_claims.csv")

    def test_patients_cleaning_and_derived_fields(self):
        cleaned = clean_patients(self.raw_patients.head(50))
        # Verify standardized column names
        self.assertIn("patient_id", cleaned.columns)
        self.assertIn("is_deceased", cleaned.columns)
        self.assertIn("age", cleaned.columns)
        # Verify age is non-negative
        self.assertTrue((cleaned["age"] >= 0).all())
        # Verify living patients are preserved with death_date null
        living = cleaned[cleaned["is_deceased"] == False]
        self.assertTrue(living["death_date"].isnull().all())

    def test_encounters_cleaning_and_duration(self):
        cleaned = clean_encounters(self.raw_encounters.head(50))
        self.assertIn("duration_minutes", cleaned.columns)
        self.assertIn("patient_cost", cleaned.columns)
        # Duration must be non-negative
        self.assertTrue((cleaned["duration_minutes"] >= 0).all())
        # Patient cost = total_claim_cost - payer_coverage
        expected_patient_cost = (cleaned["total_claim_cost"] - cleaned["payer_coverage"]).round(2)
        pd.testing.assert_series_equal(cleaned["patient_cost"], expected_patient_cost, check_names=False)

    def test_duplicate_claims_flagged_without_deletion(self):
        initial_count = len(self.raw_claims)
        cleaned = clean_billing_claims(self.raw_claims)
        # Must not delete any rows
        self.assertEqual(len(cleaned), initial_count)
        self.assertIn("is_duplicate_claim", cleaned.columns)
        # Duplicates exist in the raw dataset, verify that they are properly flagged
        flagged_dups = cleaned[cleaned["is_duplicate_claim"] == True]
        self.assertGreater(len(flagged_dups), 0)


class TestDataQualityAudit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = DataQualityAudit(processed_dir=PROCESSED_DATA_DIR)
        cls.results = cls.audit.run_all_checks()

    def test_six_dimensions_evaluated(self):
        evaluated_dims = set(r["dimension"] for r in self.results)
        expected_dims = {
            "Completeness", "Uniqueness", "Validity",
            "Timeliness", "Consistency", "Referential Integrity"
        }
        self.assertEqual(evaluated_dims, expected_dims)

    def test_completeness_passes_for_core_clinical_fields(self):
        completeness_results = [r for r in self.results if r["dimension"] == "Completeness"]
        self.assertGreater(len(completeness_results), 0)
        for r in completeness_results:
            self.assertEqual(r["status"], "PASSED", f"Rule {r['rule_name']} failed unexpectedly.")

    def test_clinical_referential_integrity(self):
        # Patient to encounter foreign key must be 100% clean
        fk_enc_pt = next(r for r in self.results if r["rule_name"] == "fk_encounter_patient")
        self.assertEqual(fk_enc_pt["status"], "PASSED")
        self.assertEqual(fk_enc_pt["affected_rows_count"], 0)

    def test_detected_audit_discrepancies_flagged(self):
        # Orphan billing claims should be caught and flagged with category POTENTIAL_ORPHAN_BILLING_CLAIM
        orphan_rule = next(r for r in self.results if r["rule_name"] == "fk_claim_to_clinical_encounter")
        self.assertEqual(orphan_rule["status"], "FLAGGED_FOR_INVESTIGATION")
        self.assertEqual(orphan_rule["affected_rows_count"], 40)
        self.assertEqual(orphan_rule["category"], "POTENTIAL_ORPHAN_BILLING_CLAIM")

    def test_report_generation(self):
        reports = self.audit.generate_reports()
        self.assertIn("overall_metrics", reports)
        self.assertTrue((PROCESSED_DATA_DIR / "data_quality_report.json").exists())
        self.assertTrue((PROCESSED_DATA_DIR / "DATA_QUALITY_REPORT.md").exists())


if __name__ == "__main__":
    unittest.main()
