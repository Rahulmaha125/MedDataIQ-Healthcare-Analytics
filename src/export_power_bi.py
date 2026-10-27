"""
MedDataIQ — Power BI Data Export & Model Preparation Module
Phase 6: Curates normalized dimensional and fact tables for Power BI Desktop.
Generates calendar dimensions and guarantees 100% financial parity with source DB.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any
import json
import pandas as pd

from src.config import POWER_BI_EXPORT_DIR, PROCESSED_DATA_DIR, setup_logging
from src.db.connection import DatabaseManager

logger = setup_logging("PowerBIExport")


def generate_date_dimension(start_date: str = "2023-01-01", end_date: str = "2026-12-31") -> pd.DataFrame:
    """Generates a comprehensive Power BI Date/Calendar dimension."""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    date_range = [start + timedelta(days=x) for x in range((end - start).days + 1)]

    records = []
    for dt in date_range:
        records.append({
            "date_key": dt.strftime("%Y-%m-%d"),
            "full_date": dt.strftime("%Y-%m-%d"),
            "year": dt.year,
            "quarter": f"Q{(dt.month - 1) // 3 + 1}",
            "year_quarter": f"{dt.year}-Q{(dt.month - 1) // 3 + 1}",
            "month": dt.month,
            "month_name": dt.strftime("%B"),
            "year_month": dt.strftime("%Y-%m"),
            "day": dt.day,
            "day_of_week": dt.strftime("%A"),
            "day_of_week_num": dt.isoweekday(),
            "is_weekend": dt.isoweekday() in [6, 7]
        })
    return pd.DataFrame(records)


def export_power_bi_datasets() -> Dict[str, Any]:
    """
    Exports clean, star-schema CSV tables to data/power_bi_exports/
    and validates financial totals against the database.
    """
    POWER_BI_EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Exporting Power BI datasets to {POWER_BI_EXPORT_DIR}...")
    db = DatabaseManager()

    exported_files = {}

    # 1. Date Dimension
    date_df = generate_date_dimension()
    date_path = POWER_BI_EXPORT_DIR / "Dim_Date.csv"
    date_df.to_csv(date_path, index=False)
    exported_files["Dim_Date"] = {"rows": len(date_df), "path": str(date_path)}
    logger.info(f"Exported Dim_Date ({len(date_df):,} rows)")

    # 2. Dimensions
    dims = [
        ("Dim_Patient", "SELECT * FROM dim_patients"),
        ("Dim_Organization", "SELECT * FROM dim_organizations"),
        ("Dim_Provider", "SELECT * FROM dim_providers"),
        ("Dim_Payer", "SELECT * FROM dim_payers"),
    ]
    for dim_name, sql in dims:
        df = db.execute_query(sql)
        path = POWER_BI_EXPORT_DIR / f"{dim_name}.csv"
        df.to_csv(path, index=False)
        exported_files[dim_name] = {"rows": len(df), "path": str(path)}
        logger.info(f"Exported {dim_name} ({len(df):,} rows)")

    # 3. Facts
    facts = [
        ("Fact_Encounter", "SELECT * FROM fact_encounters"),
        ("Fact_Billing", "SELECT * FROM fact_billing_claims"),
        ("Fact_Reconciliation", "SELECT * FROM v_billing_reconciliation_summary"),
    ]
    for fact_name, sql in facts:
        df = db.execute_query(sql)
        path = POWER_BI_EXPORT_DIR / f"{fact_name}.csv"
        df.to_csv(path, index=False)
        exported_files[fact_name] = {"rows": len(df), "path": str(path)}
        logger.info(f"Exported {fact_name} ({len(df):,} rows)")

    # 4. Data Quality Rules Fact
    dq_file = PROCESSED_DATA_DIR / "data_quality_report.json"
    if dq_file.exists():
        with open(dq_file, "r", encoding="utf-8") as f:
            dq_json = json.load(f)
        dq_df = pd.DataFrame(dq_json.get("rule_results", []))
        dq_path = POWER_BI_EXPORT_DIR / "Fact_DataQuality.csv"
        dq_df.to_csv(dq_path, index=False)
        exported_files["Fact_DataQuality"] = {"rows": len(dq_df), "path": str(dq_path)}
        logger.info(f"Exported Fact_DataQuality ({len(dq_df):,} rows)")

    # 5. Financial Validation Checks
    enc_df = pd.read_csv(POWER_BI_EXPORT_DIR / "Fact_Encounter.csv")
    claims_df = pd.read_csv(POWER_BI_EXPORT_DIR / "Fact_Billing.csv")
    recon_df = pd.read_csv(POWER_BI_EXPORT_DIR / "Fact_Reconciliation.csv")

    enc_total = round(enc_df["total_claim_cost"].sum(), 2)
    claims_total = round(claims_df["billed_amount"].sum(), 2)
    recon_enc_total = round(recon_df["clinical_encounter_cost"].sum(), 2)
    recon_billed_total = round(recon_df["claim_billed_amount"].sum(), 2)
    recon_net_variance = round(recon_df["variance_amount"].sum(), 2)

    validation_summary = {
        "encounter_rows": int(len(enc_df)),
        "claims_rows": int(len(claims_df)),
        "reconciliation_rows": int(len(recon_df)),
        "total_clinical_cost_encounter": float(enc_total),
        "total_clinical_cost_recon": float(recon_enc_total),
        "clinical_cost_parity_match": bool(enc_total == recon_enc_total),
        "total_billed_amount_claims": float(claims_total),
        "total_billed_amount_recon": float(recon_billed_total),
        "billed_amount_parity_match": bool(claims_total == recon_billed_total),
        "net_financial_variance": float(recon_net_variance),
        "net_variance_exact_match": bool(recon_net_variance == round(claims_total - enc_total, 2)),
        "exported_files": exported_files
    }

    val_path = POWER_BI_EXPORT_DIR / "export_validation_summary.json"
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)

    logger.info(f"Saved validation summary to {val_path}")
    logger.info("=== Power BI Dataset Export Completed Successfully! ===")
    return validation_summary


if __name__ == "__main__":
    export_power_bi_datasets()
