"""
MedDataIQ — Healthcare Service-to-Billing Reconciliation Engine
Phase 4: Performs automated cross-table auditing between clinical encounters
and billing claims, quantifying financial variances, risk tiers, and investigation queues.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
import pandas as pd

from src.config import PROCESSED_DATA_DIR, setup_logging
from src.db.connection import DatabaseManager

logger = setup_logging("ReconciliationEngine")


class ReconciliationEngine:
    """
    Core reconciliation auditor comparing clinical service delivery against billing claims.
    Flags discrepancies for investigation without presuming confirmed fraud.
    """

    def __init__(self, db_manager: DatabaseManager = None):
        self.db = db_manager or DatabaseManager()
        self.processed_dir = PROCESSED_DATA_DIR

    def load_reconciliation_data(self) -> pd.DataFrame:
        """Loads reconciled records from the analytical SQL view."""
        query = """
        SELECT 
            reconciliation_key,
            encounter_id,
            claim_id,
            claim_number,
            patient_id,
            provider_id,
            service_date,
            encounter_class,
            clinical_encounter_cost,
            claim_billed_amount,
            claim_paid_amount,
            variance_amount,
            claim_status,
            audit_category,
            is_duplicate_claim,
            claim_seq,
            reconciliation_status
        FROM v_billing_reconciliation_summary
        """
        return self.db.execute_query(query)

    def calculate_kpis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculates executive reconciliation metrics."""
        total_records = len(df)
        clean_records = len(df[df["reconciliation_status"] == "CLEAN_MATCH"])
        discrepancies = total_records - clean_records
        parity_rate = round((clean_records / total_records * 100), 2) if total_records > 0 else 0.0

        total_clinical = round(float(df["clinical_encounter_cost"].sum()), 2)
        total_billed = round(float(df["claim_billed_amount"].sum()), 2)
        total_paid = round(float(df["claim_paid_amount"].sum()), 2)
        net_variance = round(float(df["variance_amount"].sum()), 2)

        # Financial exposure: sum of absolute dollar variances across all discrepancies
        discrepancy_df = df[df["reconciliation_status"] != "CLEAN_MATCH"]
        total_financial_exposure = round(float(discrepancy_df["variance_amount"].abs().sum()), 2)

        return {
            "total_audited_records": total_records,
            "clean_parity_records": clean_records,
            "flagged_discrepancy_records": discrepancies,
            "clean_parity_rate_pct": parity_rate,
            "discrepancy_rate_pct": round(100.0 - parity_rate, 2),
            "total_clinical_cost": total_clinical,
            "total_billed_amount": total_billed,
            "total_paid_amount": total_paid,
            "net_variance": net_variance,
            "total_financial_exposure_at_risk": total_financial_exposure
        }

    def get_category_breakdown(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Summarizes records by reconciliation status."""
        breakdown = []
        grouped = df.groupby("reconciliation_status")

        for status, group in grouped:
            rec_count = len(group)
            pct = round((rec_count / len(df) * 100), 2)
            c_cost = round(float(group["clinical_encounter_cost"].sum()), 2)
            b_amt = round(float(group["claim_billed_amount"].sum()), 2)
            p_amt = round(float(group["claim_paid_amount"].sum()), 2)
            var_amt = round(float(group["variance_amount"].sum()), 2)

            risk_tier_map = {
                "CLEAN_MATCH": ("LOW", "Service and billing amounts match within acceptable threshold."),
                "AMOUNT_VARIANCE": ("MEDIUM", "Billed amount deviates from clinical encounter total cost."),
                "TIMING_SKEW": ("MEDIUM", "Submission date occurs prematurely or exceeds 120-day limit."),
                "DUPLICATE_CLAIM": ("HIGH", "Multiple claims submitted for identical service; voiding recommended."),
                "UNBILLED_SERVICE": ("HIGH", "Clinical service completed but no claim filed; potential revenue leakage."),
                "UNMATCHED_BILL": ("HIGH", "Billed claim exists with no clinical encounter in EHR; audit documentation.")
            }
            tier, audit_guidance = risk_tier_map.get(status, ("LOW", "Standard review"))

            breakdown.append({
                "reconciliation_status": status,
                "record_count": rec_count,
                "percentage_of_total": pct,
                "total_clinical_cost": c_cost,
                "total_billed_amount": b_amt,
                "total_paid_amount": p_amt,
                "total_variance": var_amt,
                "risk_tier": tier,
                "audit_guidance": audit_guidance
            })

        return sorted(breakdown, key=lambda x: abs(x["total_variance"]), reverse=True)

    def generate_investigation_queue(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Creates an actionable investigation queue table for billing compliance analysts.
        Prioritizes high-risk discrepancies (Unbilled, Duplicates, Unmatched, Amount Variances).
        """
        queue = df[df["reconciliation_status"] != "CLEAN_MATCH"].copy()

        def assign_action(row):
            status = row["reconciliation_status"]
            if status == "UNBILLED_SERVICE":
                return "URGENT: Review patient chart and submit claim before payer timely-filing window expires."
            elif status == "DUPLICATE_CLAIM":
                return "COMPLIANCE: Retract/void duplicate submission to prevent overpayment recoupment and penalties."
            elif status == "UNMATCHED_BILL":
                return "INVESTIGATE: Check external service logs or cross-reference patient chart for missing encounter entry."
            elif status == "AMOUNT_VARIANCE":
                diff = row["variance_amount"]
                direction = "Overbilled" if diff > 0 else "Underbilled"
                return f"AUDIT: {direction} by ${abs(diff):,.2f}. Verify fee schedule modifiers and contracted rate."
            elif status == "TIMING_SKEW":
                return "BILLING: Review filing date sequence against payer authorization guidelines."
            return "MONITOR: Routine audit."

        queue["recommended_action"] = queue.apply(assign_action, axis=1)

        # Risk prioritization
        def assign_priority(row):
            if row["reconciliation_status"] in ["UNBILLED_SERVICE", "DUPLICATE_CLAIM", "UNMATCHED_BILL"]:
                return "HIGH"
            elif abs(row["variance_amount"]) > 500:
                return "HIGH"
            return "MEDIUM"

        queue["investigation_priority"] = queue.apply(assign_priority, axis=1)

        # Sort by priority and variance magnitude
        queue = queue.sort_values(by=["investigation_priority", "variance_amount"], ascending=[True, False])
        return queue

    def run_reconciliation_audit(self) -> Dict[str, Any]:
        """Executes full reconciliation pipeline and writes reports to disk."""
        logger.info("Executing Healthcare Service-to-Billing Reconciliation Audit...")
        df = self.load_reconciliation_data()

        kpis = self.calculate_kpis(df)
        breakdown = self.get_category_breakdown(df)
        queue = self.generate_investigation_queue(df)

        # 1. Save Queue to CSV
        queue_csv = self.processed_dir / "audit_investigation_queue.csv"
        queue.to_csv(queue_csv, index=False)
        logger.info(f"Saved {len(queue):,} flagged records to {queue_csv}")

        # 2. Save JSON Report
        report_data = {
            "audit_title": "MedDataIQ Service-to-Billing Reconciliation Audit",
            "execution_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "executive_kpis": kpis,
            "category_breakdown": breakdown
        }
        json_path = self.processed_dir / "reconciliation_summary.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        logger.info(f"Saved JSON reconciliation summary to {json_path}")

        # 3. Save Markdown Report
        md_path = self.processed_dir / "RECONCILIATION_REPORT.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# MedDataIQ — Healthcare Service-to-Billing Reconciliation Report\n\n")
            f.write(f"**Audit Execution Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            f.write(f"**Clean Parity Rate:** `{kpis['clean_parity_rate_pct']}%` | **Discrepancy Rate:** `{kpis['discrepancy_rate_pct']}%`  \n")
            f.write(f"**Total Records Audited:** `{kpis['total_audited_records']:,}` | **Clean Matches:** `{kpis['clean_parity_records']:,}` | **Flagged for Review:** `{kpis['flagged_discrepancy_records']:,}`\n\n")

            f.write("## 1. Executive Financial Reconciliation\n\n")
            f.write("| Financial Metric | Amount ($) | Description |\n")
            f.write("| :--- | :---: | :--- |\n")
            f.write(f"| **Total Clinical Encounter Cost** | `${kpis['total_clinical_cost']:,.2f}` | Baseline cost of clinical services rendered in EHR. |\n")
            f.write(f"| **Total Claim Amount Billed** | `${kpis['total_billed_amount']:,.2f}` | Total charges submitted to payers on billing claims. |\n")
            f.write(f"| **Total Insurance Paid Amount** | `${kpis['total_paid_amount']:,.2f}` | Total reimbursement received from payers. |\n")
            f.write(f"| **Net Overall Financial Variance** | `${kpis['net_variance']:,.2f}` | Mathematical variance (`Total Billed - Total Clinical`). |\n")
            f.write(f"| **Total Financial Exposure at Risk** | `${kpis['total_financial_exposure_at_risk']:,.2f}` | Cumulative absolute dollar variance across all flagged categories. |\n\n")

            f.write("## 2. Discrepancy Category Breakdown\n\n")
            f.write("| Reconciliation Status | Records | Share (%) | Clinical Cost ($) | Billed Amount ($) | Variance ($) | Risk Tier |\n")
            f.write("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |\n")
            for b in breakdown:
                f.write(f"| **`{b['reconciliation_status']}`** | {b['record_count']:,} | {b['percentage_of_total']}% | ${b['total_clinical_cost']:,.2f} | ${b['total_billed_amount']:,.2f} | ${b['total_variance']:,.2f} | `{b['risk_tier']}` |\n")

            f.write("\n## 3. Investigation Triage Guidance\n\n")
            for b in breakdown:
                if b["reconciliation_status"] != "CLEAN_MATCH":
                    f.write(f"### {b['reconciliation_status']} ({b['record_count']:,} records — {b['percentage_of_total']}%)\n")
                    f.write(f"- **Risk Tier:** `{b['risk_tier']}`\n")
                    f.write(f"- **Financial Impact:** Net Variance of `${b['total_variance']:,.2f}`\n")
                    f.write(f"- **Recommended Audit Guidance:** {b['audit_guidance']}\n\n")

        logger.info(f"Saved Markdown reconciliation report to {md_path}")
        return report_data


if __name__ == "__main__":
    engine = ReconciliationEngine()
    engine.run_reconciliation_audit()
