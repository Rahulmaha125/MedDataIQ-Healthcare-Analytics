"""
MedDataIQ — Healthcare Data Quality Audit Engine
Phase 2: Evaluates six core dimensions of healthcare data quality:
1. Completeness
2. Uniqueness
3. Validity
4. Timeliness / Temporal Logic
5. Consistency
6. Referential Integrity

Generates JSON and Markdown audit reports distinguishing detected issues from confirmed errors.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.config import PROCESSED_DATA_DIR, setup_logging

logger = setup_logging("QualityEngine")


class DataQualityAudit:
    def __init__(self, processed_dir: Path = PROCESSED_DATA_DIR):
        self.processed_dir = processed_dir
        self.results: List[Dict[str, Any]] = []
        self.dfs: Dict[str, pd.DataFrame] = {}
        self.load_datasets()

    def load_datasets(self):
        """Loads all processed tables into memory for validation."""
        required = [
            "dim_patients", "fact_encounters", "fact_procedures",
            "fact_medications", "dim_organizations", "dim_providers",
            "dim_payers", "fact_billing_claims"
        ]
        for name in required:
            csv_path = self.processed_dir / f"{name}.csv"
            if csv_path.exists():
                self.dfs[name] = pd.read_csv(csv_path)
            else:
                logger.warning(f"File {csv_path} not found. Some checks may fail.")

    def add_result(
        self,
        dimension: str,
        dataset: str,
        rule_name: str,
        description: str,
        severity: str,
        total_rows: int,
        affected_rows: int,
        examples: List[Any],
        category: str = "DETECTED_ISSUE"
    ):
        """Records the outcome of a quality evaluation rule."""
        violation_rate = round((affected_rows / total_rows * 100), 2) if total_rows > 0 else 0.0
        status = "PASSED" if affected_rows == 0 else "FLAGGED_FOR_INVESTIGATION"

        record = {
            "dimension": dimension,
            "dataset": dataset,
            "rule_name": rule_name,
            "description": description,
            "severity": severity,  # CRITICAL, WARNING, INFO
            "status": status,
            "category": "CONFIRMED_CLEAN" if affected_rows == 0 else category,
            "total_rows_evaluated": total_rows,
            "affected_rows_count": affected_rows,
            "violation_rate_pct": violation_rate,
            "examples": [str(x) for x in examples[:5]]
        }
        self.results.append(record)

    # -------------------------------------------------------------
    # DIMENSION 1: COMPLETENESS
    # -------------------------------------------------------------
    def check_completeness(self):
        logger.info("Evaluating Completeness...")

        # Patients
        df = self.dfs.get("dim_patients")
        if df is not None:
            for col in ["patient_id", "birth_date", "first_name", "last_name", "gender", "zip_code"]:
                nulls = df[df[col].isnull()]
                self.add_result(
                    dimension="Completeness",
                    dataset="dim_patients",
                    rule_name=f"mandatory_field_{col}",
                    description=f"Mandatory demographic field '{col}' must not be null.",
                    severity="CRITICAL",
                    total_rows=len(df),
                    affected_rows=len(nulls),
                    examples=nulls["patient_id"].tolist() if len(nulls) > 0 else []
                )

        # Encounters
        df = self.dfs.get("fact_encounters")
        if df is not None:
            for col in ["encounter_id", "patient_id", "provider_id", "start_time", "total_claim_cost"]:
                nulls = df[df[col].isnull()]
                self.add_result(
                    dimension="Completeness",
                    dataset="fact_encounters",
                    rule_name=f"mandatory_field_{col}",
                    description=f"Mandatory encounter field '{col}' must not be null.",
                    severity="CRITICAL",
                    total_rows=len(df),
                    affected_rows=len(nulls),
                    examples=nulls["encounter_id"].tolist() if len(nulls) > 0 else []
                )

        # Billing Claims
        df = self.dfs.get("fact_billing_claims")
        if df is not None:
            for col in ["claim_id", "patient_id", "billed_amount", "claim_status"]:
                nulls = df[df[col].isnull()]
                self.add_result(
                    dimension="Completeness",
                    dataset="fact_billing_claims",
                    rule_name=f"mandatory_field_{col}",
                    description=f"Mandatory claim field '{col}' must not be null.",
                    severity="CRITICAL",
                    total_rows=len(df),
                    affected_rows=len(nulls),
                    examples=nulls["claim_id"].tolist() if len(nulls) > 0 else []
                )

    # -------------------------------------------------------------
    # DIMENSION 2: UNIQUENESS
    # -------------------------------------------------------------
    def check_uniqueness(self):
        logger.info("Evaluating Uniqueness...")

        # Primary Key Checks
        pk_targets = [
            ("dim_patients", "patient_id"),
            ("fact_encounters", "encounter_id"),
            ("dim_providers", "provider_id"),
            ("dim_organizations", "organization_id"),
            ("dim_payers", "payer_id"),
            ("fact_billing_claims", "claim_id")
        ]

        for table, pk in pk_targets:
            df = self.dfs.get(table)
            if df is not None:
                dups = df[df.duplicated(subset=[pk], keep=False)]
                self.add_result(
                    dimension="Uniqueness",
                    dataset=table,
                    rule_name=f"pk_uniqueness_{pk}",
                    description=f"Primary key '{pk}' in {table} must be strictly unique.",
                    severity="CRITICAL",
                    total_rows=len(df),
                    affected_rows=len(dups),
                    examples=dups[pk].tolist() if len(dups) > 0 else []
                )

        # Business Duplicate Detection on Claims
        claims = self.dfs.get("fact_billing_claims")
        if claims is not None:
            dup_claims = claims[claims["is_duplicate_claim"] == True]
            self.add_result(
                dimension="Uniqueness",
                dataset="fact_billing_claims",
                rule_name="duplicate_claim_submissions",
                description="Flags multiple claims with identical patient, provider, service date, and amount.",
                severity="WARNING",
                total_rows=len(claims),
                affected_rows=len(dup_claims),
                examples=dup_claims["claim_number"].tolist() if len(dup_claims) > 0 else [],
                category="POTENTIAL_DUPLICATE_CLAIM"
            )

    # -------------------------------------------------------------
    # DIMENSION 3: VALIDITY
    # -------------------------------------------------------------
    def check_validity(self):
        logger.info("Evaluating Validity...")

        # Gender validity
        patients = self.dfs.get("dim_patients")
        if patients is not None:
            invalid_gender = patients[~patients["gender"].isin(["M", "F"])]
            self.add_result(
                dimension="Validity",
                dataset="dim_patients",
                rule_name="gender_domain_validity",
                description="Gender must be standard category 'M' or 'F'.",
                severity="WARNING",
                total_rows=len(patients),
                affected_rows=len(invalid_gender),
                examples=invalid_gender["gender"].tolist() if len(invalid_gender) > 0 else []
            )

            # Age range validity
            invalid_age = patients[(patients["age"] < 0) | (patients["age"] > 125)]
            self.add_result(
                dimension="Validity",
                dataset="dim_patients",
                rule_name="age_physiological_range",
                description="Patient age must be physiologically valid (between 0 and 125 years).",
                severity="CRITICAL",
                total_rows=len(patients),
                affected_rows=len(invalid_age),
                examples=invalid_age["age"].tolist() if len(invalid_age) > 0 else []
            )

        # Encounter Cost Validity
        enc = self.dfs.get("fact_encounters")
        if enc is not None:
            invalid_cost = enc[enc["total_claim_cost"] < 0]
            self.add_result(
                dimension="Validity",
                dataset="fact_encounters",
                rule_name="non_negative_encounter_cost",
                description="Encounter total claim cost cannot be negative.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(invalid_cost),
                examples=invalid_cost["total_claim_cost"].tolist() if len(invalid_cost) > 0 else []
            )

            valid_classes = ["wellness", "ambulatory", "outpatient", "urgentcare", "emergency", "inpatient"]
            invalid_class = enc[~enc["encounter_class"].isin(valid_classes)]
            self.add_result(
                dimension="Validity",
                dataset="fact_encounters",
                rule_name="encounter_class_domain",
                description=f"Encounter class must belong to standard set: {valid_classes}.",
                severity="WARNING",
                total_rows=len(enc),
                affected_rows=len(invalid_class),
                examples=invalid_class["encounter_class"].tolist() if len(invalid_class) > 0 else []
            )

        # Billing Claims validity
        claims = self.dfs.get("fact_billing_claims")
        if claims is not None:
            zero_or_neg_bills = claims[claims["billed_amount"] <= 0]
            self.add_result(
                dimension="Validity",
                dataset="fact_billing_claims",
                rule_name="positive_billed_amount",
                description="Claim billed amount must be greater than zero.",
                severity="CRITICAL",
                total_rows=len(claims),
                affected_rows=len(zero_or_neg_bills),
                examples=zero_or_neg_bills["billed_amount"].tolist() if len(zero_or_neg_bills) > 0 else []
            )

    # -------------------------------------------------------------
    # DIMENSION 4: TIMELINESS & TEMPORAL LOGIC
    # -------------------------------------------------------------
    def check_timeliness(self):
        logger.info("Evaluating Timeliness & Temporal Logic...")

        enc = self.dfs.get("fact_encounters")
        if enc is not None:
            # Duration validity (stop >= start)
            neg_dur = enc[enc["duration_minutes"] < 0]
            self.add_result(
                dimension="Timeliness",
                dataset="fact_encounters",
                rule_name="encounter_duration_logical",
                description="Encounter stop time must not precede start time.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(neg_dur),
                examples=neg_dur["duration_minutes"].tolist() if len(neg_dur) > 0 else []
            )

            # Future date check
            future_enc = enc[enc["encounter_date"] > "2026-10-27"]
            self.add_result(
                dimension="Timeliness",
                dataset="fact_encounters",
                rule_name="no_future_encounters",
                description="Encounter date must not exceed current simulation cutoff.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(future_enc),
                examples=future_enc["encounter_date"].tolist() if len(future_enc) > 0 else []
            )

        # Claim Submission Timing
        claims = self.dfs.get("fact_billing_claims")
        if claims is not None:
            # Submission before service date
            sub_dt = pd.to_datetime(claims["claim_submission_date"])
            srv_dt = pd.to_datetime(claims["service_date"])
            early_sub = claims[sub_dt < srv_dt]
            self.add_result(
                dimension="Timeliness",
                dataset="fact_billing_claims",
                rule_name="claim_submitted_after_service",
                description="Claim submission date should not occur prior to the date service was rendered.",
                severity="WARNING",
                total_rows=len(claims),
                affected_rows=len(early_sub),
                examples=early_sub["claim_number"].tolist() if len(early_sub) > 0 else [],
                category="POTENTIAL_PREMATURE_BILLING"
            )

            # Stale claims (>120 days)
            days_diff = (sub_dt - srv_dt).dt.days
            stale_claims = claims[days_diff > 120]
            self.add_result(
                dimension="Timeliness",
                dataset="fact_billing_claims",
                rule_name="timely_filing_limit_120d",
                description="Claims submitted more than 120 days after service are flagged for timely-filing review.",
                severity="INFO",
                total_rows=len(claims),
                affected_rows=len(stale_claims),
                examples=stale_claims["claim_number"].tolist() if len(stale_claims) > 0 else [],
                category="POTENTIAL_STALE_CLAIM"
            )

    # -------------------------------------------------------------
    # DIMENSION 5: CONSISTENCY
    # -------------------------------------------------------------
    def check_consistency(self):
        logger.info("Evaluating Consistency...")

        # Encounter financial consistency: Payer Coverage <= Total Cost
        enc = self.dfs.get("fact_encounters")
        if enc is not None:
            over_cov = enc[enc["payer_coverage"] > (enc["total_claim_cost"] + 0.01)]
            self.add_result(
                dimension="Consistency",
                dataset="fact_encounters",
                rule_name="payer_coverage_within_claim_total",
                description="Payer coverage amount cannot logically exceed total encounter claim cost.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(over_cov),
                examples=over_cov[["total_claim_cost", "payer_coverage"]].to_dict(orient="records") if len(over_cov) > 0 else []
            )

        # Claim financial consistency: Paid <= Allowed <= Billed
        claims = self.dfs.get("fact_billing_claims")
        if claims is not None:
            excess_allowed = claims[claims["allowed_amount"] > (claims["billed_amount"] + 0.01)]
            self.add_result(
                dimension="Consistency",
                dataset="fact_billing_claims",
                rule_name="allowed_amount_within_billed",
                description="Contractually allowed amount cannot exceed total billed charge.",
                severity="CRITICAL",
                total_rows=len(claims),
                affected_rows=len(excess_allowed),
                examples=excess_allowed["claim_number"].tolist() if len(excess_allowed) > 0 else []
            )

            excess_paid = claims[claims["paid_amount"] > (claims["allowed_amount"] + 0.01)]
            self.add_result(
                dimension="Consistency",
                dataset="fact_billing_claims",
                rule_name="paid_amount_within_allowed",
                description="Insurance paid amount cannot exceed contractually allowed amount.",
                severity="CRITICAL",
                total_rows=len(claims),
                affected_rows=len(excess_paid),
                examples=excess_paid["claim_number"].tolist() if len(excess_paid) > 0 else []
            )

        # Patient Life Consistency
        patients = self.dfs.get("dim_patients")
        if patients is not None:
            dec = patients[patients["is_deceased"] == True]
            b_dt = pd.to_datetime(dec["birth_date"])
            d_dt = pd.to_datetime(dec["death_date"])
            inconsistent_life = dec[d_dt < b_dt]
            self.add_result(
                dimension="Consistency",
                dataset="dim_patients",
                rule_name="death_date_after_birth_date",
                description="Death date cannot precede birth date.",
                severity="CRITICAL",
                total_rows=len(dec),
                affected_rows=len(inconsistent_life),
                examples=inconsistent_life["patient_id"].tolist() if len(inconsistent_life) > 0 else []
            )

    # -------------------------------------------------------------
    # DIMENSION 6: REFERENTIAL INTEGRITY
    # -------------------------------------------------------------
    def check_referential_integrity(self):
        logger.info("Evaluating Referential Integrity...")

        patients = self.dfs.get("dim_patients")
        enc = self.dfs.get("fact_encounters")
        proc = self.dfs.get("fact_procedures")
        med = self.dfs.get("fact_medications")
        prov = self.dfs.get("dim_providers")
        orgs = self.dfs.get("dim_organizations")
        payers = self.dfs.get("dim_payers")
        claims = self.dfs.get("fact_billing_claims")

        if enc is not None and patients is not None:
            orphan_pts = enc[~enc["patient_id"].isin(set(patients["patient_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_encounters",
                rule_name="fk_encounter_patient",
                description="Encounter patient_id must exist in dim_patients.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(orphan_pts),
                examples=orphan_pts["patient_id"].tolist() if len(orphan_pts) > 0 else []
            )

        if enc is not None and prov is not None:
            orphan_prov = enc[~enc["provider_id"].isin(set(prov["provider_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_encounters",
                rule_name="fk_encounter_provider",
                description="Encounter provider_id must exist in dim_providers.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(orphan_prov),
                examples=orphan_prov["provider_id"].tolist() if len(orphan_prov) > 0 else []
            )

        if enc is not None and orgs is not None:
            orphan_orgs = enc[~enc["organization_id"].isin(set(orgs["organization_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_encounters",
                rule_name="fk_encounter_organization",
                description="Encounter organization_id must exist in dim_organizations.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(orphan_orgs),
                examples=orphan_orgs["organization_id"].tolist() if len(orphan_orgs) > 0 else []
            )

        if enc is not None and payers is not None:
            orphan_payers = enc[~enc["payer_id"].isin(set(payers["payer_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_encounters",
                rule_name="fk_encounter_payer",
                description="Encounter payer_id must exist in dim_payers.",
                severity="CRITICAL",
                total_rows=len(enc),
                affected_rows=len(orphan_payers),
                examples=orphan_payers["payer_id"].tolist() if len(orphan_payers) > 0 else []
            )

        if proc is not None and enc is not None:
            orphan_procs = proc[~proc["encounter_id"].isin(set(enc["encounter_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_procedures",
                rule_name="fk_procedure_encounter",
                description="Procedure encounter_id must exist in fact_encounters.",
                severity="CRITICAL",
                total_rows=len(proc),
                affected_rows=len(orphan_procs),
                examples=orphan_procs["encounter_id"].tolist() if len(orphan_procs) > 0 else []
            )

        if med is not None and enc is not None:
            orphan_meds = med[~med["encounter_id"].isin(set(enc["encounter_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_medications",
                rule_name="fk_medication_encounter",
                description="Medication encounter_id must exist in fact_encounters.",
                severity="CRITICAL",
                total_rows=len(med),
                affected_rows=len(orphan_meds),
                examples=orphan_meds["encounter_id"].tolist() if len(orphan_meds) > 0 else []
            )

        # Service-to-Billing Cross Reference Check:
        # Evaluates billing claims linked to non-existent encounter IDs (Orphan / Unmatched bills)
        if claims is not None and enc is not None:
            orphan_bills = claims[~claims["encounter_id"].isin(set(enc["encounter_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_billing_claims",
                rule_name="fk_claim_to_clinical_encounter",
                description="Billing claim encounter_id should map to a valid clinical visit. Orphan bills are flagged for investigation.",
                severity="WARNING",
                total_rows=len(claims),
                affected_rows=len(orphan_bills),
                examples=orphan_bills["claim_number"].tolist() if len(orphan_bills) > 0 else [],
                category="POTENTIAL_ORPHAN_BILLING_CLAIM"
            )

            orphan_bill_patients = claims[~claims["patient_id"].isin(set(patients["patient_id"]))]
            self.add_result(
                dimension="Referential Integrity",
                dataset="fact_billing_claims",
                rule_name="fk_claim_patient",
                description="Claim patient_id must exist in dim_patients.",
                severity="CRITICAL",
                total_rows=len(claims),
                affected_rows=len(orphan_bill_patients),
                examples=orphan_bill_patients["claim_id"].tolist() if len(orphan_bill_patients) > 0 else []
            )

    # -------------------------------------------------------------
    # EXECUTION & REPORT GENERATION
    # -------------------------------------------------------------
    def run_all_checks(self) -> List[Dict[str, Any]]:
        self.results = []
        self.check_completeness()
        self.check_uniqueness()
        self.check_validity()
        self.check_timeliness()
        self.check_consistency()
        self.check_referential_integrity()
        return self.results

    def generate_reports(self, output_dir: Path = PROCESSED_DATA_DIR):
        """Generates structured JSON and comprehensive Markdown reports."""
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        total_rules = len(self.results)
        passed_rules = sum(1 for r in self.results if r["status"] == "PASSED")
        flagged_rules = total_rules - passed_rules
        critical_issues = sum(1 for r in self.results if r["severity"] == "CRITICAL" and r["status"] != "PASSED")
        dq_index = round((passed_rules / total_rules * 100), 2) if total_rules > 0 else 0.0

        report_summary = {
            "report_title": "MedDataIQ Data Quality Audit Report",
            "audit_timestamp": timestamp,
            "overall_metrics": {
                "total_rules_evaluated": total_rules,
                "passed_rules": passed_rules,
                "flagged_for_investigation": flagged_rules,
                "critical_violations": critical_issues,
                "data_quality_index_pct": dq_index
            },
            "dimensions_evaluated": [
                "Completeness", "Uniqueness", "Validity",
                "Timeliness", "Consistency", "Referential Integrity"
            ],
            "rule_results": self.results
        }

        # 1. JSON Report
        json_path = output_dir / "data_quality_report.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_summary, f, indent=2)
        logger.info(f"Saved JSON quality report to {json_path}")

        # 2. Markdown Report
        md_path = output_dir / "DATA_QUALITY_REPORT.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# MedDataIQ — Healthcare Data Quality Audit Report\n\n")
            f.write(f"**Audit Execution Timestamp:** {timestamp}  \n")
            f.write(f"**Overall Data Quality Index:** `{dq_index}%`  \n")
            f.write(f"**Total Rules Evaluated:** `{total_rules}` | **Passed:** `{passed_rules}` | **Flagged for Review:** `{flagged_rules}` | **Critical Failures:** `{critical_issues}`\n\n")
            f.write("> [!NOTE]\n")
            f.write("> Detected discrepancies reflect real-world healthcare operational noise and controlled audit scenarios (e.g. duplicate claims, late filings, unmatched bills). They are labeled as **flagged issues for investigation** rather than confirmed systemic errors.\n\n")

            f.write("## 1. Executive Dimension Summary\n\n")
            f.write("| Dimension | Total Rules | Passed | Flagged | Pass Rate |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: |\n")

            dim_group = {}
            for r in self.results:
                dim = r["dimension"]
                dim_group.setdefault(dim, {"total": 0, "passed": 0})
                dim_group[dim]["total"] += 1
                if r["status"] == "PASSED":
                    dim_group[dim]["passed"] += 1

            for dim, counts in dim_group.items():
                p_rate = round(counts["passed"] / counts["total"] * 100, 1)
                flagged = counts["total"] - counts["passed"]
                f.write(f"| **{dim}** | {counts['total']} | {counts['passed']} | {flagged} | {p_rate}% |\n")

            f.write("\n## 2. Detailed Rule Evaluation Table\n\n")
            f.write("| Dataset | Rule Name | Dimension | Severity | Affected Rows | Rate | Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :---: | :---: | :--- |\n")
            for r in self.results:
                status_badge = "✅ PASSED" if r["status"] == "PASSED" else "⚠️ FLAGGED"
                f.write(f"| `{r['dataset']}` | `{r['rule_name']}` | {r['dimension']} | {r['severity']} | {r['affected_rows_count']:,} / {r['total_rows_evaluated']:,} | {r['violation_rate_pct']}% | {status_badge} |\n")

            f.write("\n## 3. Discrepancy Investigation Drill-Down\n\n")
            flagged_items = [r for r in self.results if r["status"] != "PASSED"]
            if not flagged_items:
                f.write("No data quality discrepancies were detected. All datasets meet high-grade clinical benchmarks.\n")
            else:
                for idx, r in enumerate(flagged_items, 1):
                    f.write(f"### {idx}. {r['rule_name']} ({r['dataset']})\n")
                    f.write(f"- **Dimension:** {r['dimension']}\n")
                    f.write(f"- **Severity:** `{r['severity']}` | **Category:** `{r['category']}`\n")
                    f.write(f"- **Description:** {r['description']}\n")
                    f.write(f"- **Affected Records:** `{r['affected_rows_count']:,}` out of `{r['total_rows_evaluated']:,}` ({r['violation_rate_pct']}%)\n")
                    f.write(f"- **Sample Examples:** `{', '.join(r['examples'])}`\n\n")

        logger.info(f"Saved Markdown quality report to {md_path}")
        return report_summary


def run_quality_pipeline():
    audit = DataQualityAudit()
    audit.run_all_checks()
    return audit.generate_reports()


if __name__ == "__main__":
    run_quality_pipeline()
