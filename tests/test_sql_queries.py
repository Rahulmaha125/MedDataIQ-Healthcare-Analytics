"""
MedDataIQ — Automated Tests for Database Loading & Analytical SQL Queries
Phase 3: Verifies table loads, row counts, view execution,
and executes all 5 advanced analytical queries (CTEs, Window Functions, Joins).
"""

import unittest
from src.db.connection import DatabaseManager
from src.db.load_data import load_database


class TestDatabaseAndSQLAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure database is loaded
        cls.load_summary = load_database()
        cls.db = DatabaseManager()

    def test_table_row_counts_parity(self):
        expected_counts = {
            "dim_patients": 1000,
            "dim_organizations": 6,
            "dim_providers": 30,
            "dim_payers": 7,
            "fact_encounters": 5730,
            "fact_procedures": 3171,
            "fact_medications": 2529,
            "fact_billing_claims": 5770
        }
        for table, expected in expected_counts.items():
            df = self.db.execute_query(f"SELECT COUNT(*) AS cnt FROM {table}")
            actual = int(df["cnt"].iloc[0])
            self.assertEqual(actual, expected, f"Row mismatch for {table}: expected {expected}, got {actual}")

    def test_analytical_views_execution(self):
        # 1. Executive Monthly KPIs
        kpi_df = self.db.execute_query("SELECT * FROM v_kpi_executive_monthly")
        self.assertGreater(len(kpi_df), 0)
        self.assertIn("total_encounters", kpi_df.columns)
        self.assertIn("payer_coverage_rate_pct", kpi_df.columns)

        # 2. Encounter Class Summary
        enc_class_df = self.db.execute_query("SELECT * FROM v_encounter_class_summary")
        self.assertEqual(len(enc_class_df), 6)
        self.assertIn("encounter_class", enc_class_df.columns)
        self.assertIn("volume_share_pct", enc_class_df.columns)

        # 3. Provider Workload
        prov_df = self.db.execute_query("SELECT * FROM v_provider_workload")
        self.assertEqual(len(prov_df), 30)
        self.assertIn("total_revenue_generated", prov_df.columns)

        # 4. Billing Reconciliation Summary
        recon_df = self.db.execute_query("SELECT * FROM v_billing_reconciliation_summary")
        self.assertGreater(len(recon_df), 0)
        self.assertIn("reconciliation_status", recon_df.columns)
        self.assertIn("variance_amount", recon_df.columns)

    def test_query_1_provider_ranking_window_function(self):
        sql = """
        WITH provider_metrics AS (
            SELECT 
                p.provider_id,
                p.provider_name,
                p.specialty,
                o.organization_name,
                COUNT(e.encounter_id) AS total_encounters,
                COUNT(DISTINCT e.patient_id) AS unique_patients,
                ROUND(SUM(e.total_claim_cost), 2) AS total_revenue,
                ROUND(AVG(e.duration_minutes), 1) AS avg_visit_mins
            FROM dim_providers p
            JOIN dim_organizations o ON p.organization_id = o.organization_id
            JOIN fact_encounters e ON p.provider_id = e.provider_id
            GROUP BY p.provider_id, p.provider_name, p.specialty, o.organization_name
        )
        SELECT 
            specialty,
            provider_name,
            total_revenue,
            DENSE_RANK() OVER (PARTITION BY specialty ORDER BY total_revenue DESC) AS rank_within_specialty,
            ROUND((total_revenue * 100.0) / SUM(total_revenue) OVER (PARTITION BY specialty), 2) AS specialty_revenue_share_pct
        FROM provider_metrics
        ORDER BY specialty, rank_within_specialty;
        """
        df = self.db.execute_query(sql)
        self.assertEqual(len(df), 30)
        # Verify DENSE_RANK starts at 1 for each specialty
        first_ranks = df.groupby("specialty")["rank_within_specialty"].min()
        self.assertTrue((first_ranks == 1).all())

    def test_query_2_readmission_analysis_window_function(self):
        sql = """
        WITH patient_encounters AS (
            SELECT 
                e.patient_id,
                e.encounter_id,
                e.encounter_date,
                e.encounter_class,
                e.total_claim_cost,
                LAG(e.encounter_date, 1) OVER (
                    PARTITION BY e.patient_id 
                    ORDER BY e.encounter_date
                ) AS previous_visit_date
            FROM fact_encounters e
            WHERE e.encounter_class IN ('inpatient', 'emergency', 'urgentcare')
        ),
        readmission_intervals AS (
            SELECT 
                encounter_class,
                total_claim_cost,
                CASE 
                    WHEN previous_visit_date IS NOT NULL 
                    THEN CAST((JULIANDAY(encounter_date) - JULIANDAY(previous_visit_date)) AS INTEGER)
                    ELSE NULL 
                END AS days_since_last_visit
            FROM patient_encounters
        )
        SELECT 
            encounter_class,
            COUNT(*) AS total_acute_visits,
            SUM(CASE WHEN days_since_last_visit BETWEEN 1 AND 30 THEN 1 ELSE 0 END) AS readmissions_within_30d,
            ROUND((SUM(CASE WHEN days_since_last_visit BETWEEN 1 AND 30 THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 2) AS readmission_rate_pct
        FROM readmission_intervals
        GROUP BY encounter_class;
        """
        df = self.db.execute_query(sql)
        self.assertGreater(len(df), 0)
        self.assertIn("readmission_rate_pct", df.columns)

    def test_query_3_reconciliation_financial_exposure(self):
        sql = """
        WITH reconciliation_detail AS (
            SELECT 
                reconciliation_status,
                COUNT(*) AS record_count,
                ROUND(SUM(clinical_encounter_cost), 2) AS total_clinical_cost,
                ROUND(SUM(claim_billed_amount), 2) AS total_billed_amount,
                ROUND(SUM(variance_amount), 2) AS total_variance
            FROM v_billing_reconciliation_summary
            GROUP BY reconciliation_status
        )
        SELECT 
            reconciliation_status,
            record_count,
            total_clinical_cost,
            total_billed_amount,
            total_variance
        FROM reconciliation_detail
        ORDER BY ABS(total_variance) DESC;
        """
        df = self.db.execute_query(sql)
        self.assertGreater(len(df), 0)
        statuses = set(df["reconciliation_status"])
        self.assertIn("CLEAN_MATCH", statuses)
        self.assertIn("AMOUNT_VARIANCE", statuses)
        self.assertIn("UNBILLED_SERVICE", statuses)
        self.assertIn("UNMATCHED_BILL", statuses)
        self.assertIn("DUPLICATE_CLAIM", statuses)

    def test_reconciliation_row_and_category_counts(self):
        """Verifies exact category counts in the corrected reconciliation view."""
        df = self.db.execute_query("""
            SELECT reconciliation_status, COUNT(*) as cnt 
            FROM v_billing_reconciliation_summary 
            GROUP BY reconciliation_status
        """)
        counts = dict(zip(df["reconciliation_status"], df["cnt"]))
        expected_counts = {
            "CLEAN_MATCH": 4567,
            "AMOUNT_VARIANCE": 539,
            "TIMING_SKEW": 384,
            "UNBILLED_SERVICE": 240,
            "DUPLICATE_CLAIM": 240,
            "UNMATCHED_BILL": 40
        }
        self.assertEqual(counts, expected_counts)
        self.assertEqual(sum(counts.values()), 6010)

    def test_reconciliation_financial_parity_without_double_counting(self):
        """
        Verifies that total clinical cost and total billed amount in the reconciliation view
        match the underlying tables exactly to the penny (no double counting).
        """
        enc_total = float(self.db.execute_query("SELECT SUM(total_claim_cost) AS s FROM fact_encounters")["s"].iloc[0])
        claims_total = float(self.db.execute_query("SELECT SUM(billed_amount) AS s FROM fact_billing_claims")["s"].iloc[0])

        recon_df = self.db.execute_query("""
            SELECT 
                ROUND(SUM(clinical_encounter_cost), 2) AS recon_enc_cost,
                ROUND(SUM(claim_billed_amount), 2) AS recon_billed_amount,
                ROUND(SUM(variance_amount), 2) AS recon_net_variance
            FROM v_billing_reconciliation_summary
        """)
        recon_enc = float(recon_df["recon_enc_cost"].iloc[0])
        recon_billed = float(recon_df["recon_billed_amount"].iloc[0])
        recon_var = float(recon_df["recon_net_variance"].iloc[0])

        # Exact parity assertions
        self.assertAlmostEqual(recon_enc, enc_total, places=2)
        self.assertAlmostEqual(recon_billed, claims_total, places=2)
        self.assertAlmostEqual(recon_var, claims_total - enc_total, places=2)

    def test_duplicate_claims_excess_billed_isolated(self):
        """
        Verifies that secondary duplicate claims are attributed $0 clinical encounter cost
        and their billed amount is correctly treated as pure financial exposure.
        """
        df = self.db.execute_query("""
            SELECT 
                COUNT(*) as cnt,
                ROUND(SUM(clinical_encounter_cost), 2) as sum_enc_cost,
                ROUND(SUM(claim_billed_amount), 2) as sum_billed,
                ROUND(SUM(variance_amount), 2) as sum_variance
            FROM v_billing_reconciliation_summary
            WHERE reconciliation_status = 'DUPLICATE_CLAIM'
        """)
        self.assertEqual(int(df["cnt"].iloc[0]), 240)
        self.assertEqual(float(df["sum_enc_cost"].iloc[0]), 0.0)  # No double-counting!
        self.assertEqual(float(df["sum_billed"].iloc[0]), 189343.57)
        self.assertEqual(float(df["sum_variance"].iloc[0]), 189343.57)

    def test_unbilled_and_unmatched_claims_visibility(self):
        """Verifies unbilled services and orphan claims are properly isolated."""
        df = self.db.execute_query("""
            SELECT 
                reconciliation_status,
                COUNT(*) as cnt,
                ROUND(SUM(variance_amount), 2) as sum_variance
            FROM v_billing_reconciliation_summary
            WHERE reconciliation_status IN ('UNBILLED_SERVICE', 'UNMATCHED_BILL')
            GROUP BY reconciliation_status
        """)
        summary = dict(zip(df["reconciliation_status"], zip(df["cnt"], df["sum_variance"])))
        # Unbilled service: negative variance (leakage)
        self.assertEqual(summary["UNBILLED_SERVICE"][0], 240)
        self.assertEqual(summary["UNBILLED_SERVICE"][1], -224443.42)
        # Unmatched bill: positive variance (ghost claim)
        self.assertEqual(summary["UNMATCHED_BILL"][0], 40)
        self.assertEqual(summary["UNMATCHED_BILL"][1], 36700.33)

    def test_preserved_audit_records(self):
        # 1. Flagged duplicate claims must be preserved in fact_billing_claims
        dup_df = self.db.execute_query("SELECT COUNT(*) AS cnt FROM fact_billing_claims WHERE is_duplicate_claim = 1")
        dup_cnt = int(dup_df["cnt"].iloc[0])
        self.assertEqual(dup_cnt, 480, f"Expected 480 duplicate records, found {dup_cnt}")

        # 2. Unmatched ghost claims must be preserved in fact_billing_claims
        orphan_df = self.db.execute_query("""
            SELECT COUNT(*) AS cnt 
            FROM fact_billing_claims 
            WHERE encounter_id NOT IN (SELECT encounter_id FROM fact_encounters)
        """)
        orphan_cnt = int(orphan_df["cnt"].iloc[0])
        self.assertEqual(orphan_cnt, 40, f"Expected 40 orphan claims, found {orphan_cnt}")


if __name__ == "__main__":
    unittest.main()
