"""
MedDataIQ — Phase 1 Dataset & Environment Verification Script
Validates file presence, column schemas, record counts, and relational integrity.
"""
import sys
from pathlib import Path
import pandas as pd

from src.config import RAW_DATA_DIR, setup_logging

logger = setup_logging("Phase1Verification")

EXPECTED_FILES = {
    "patients.csv": ["Id", "BIRTHDATE", "GENDER", "RACE", "ETHNICITY", "CITY", "STATE", "ZIP", "HEALTHCARE_EXPENSES", "HEALTHCARE_COVERAGE"],
    "encounters.csv": ["Id", "START", "STOP", "PATIENT", "ORGANIZATION", "PROVIDER", "PAYER", "ENCOUNTERCLASS", "CODE", "DESCRIPTION", "TOTAL_CLAIM_COST"],
    "procedures.csv": ["START", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION", "BASE_COST"],
    "medications.csv": ["START", "PATIENT", "PAYER", "ENCOUNTER", "CODE", "DESCRIPTION", "BASE_COST", "TOTAL_COST"],
    "organizations.csv": ["Id", "NAME", "CITY", "STATE", "ZIP", "UTILIZATION"],
    "providers.csv": ["Id", "ORGANIZATION", "NAME", "SPECIALITY", "GENDER", "CITY"],
    "payers.csv": ["Id", "NAME", "PHONE"],
    "billing_claims.csv": ["claim_id", "claim_number", "encounter_id", "patient_id", "provider_id", "payer_id", "billed_amount", "claim_status", "audit_category"]
}


def verify_dataset():
    logger.info("Starting Phase 1 Verification...")
    all_passed = True
    summary = []

    for filename, required_cols in EXPECTED_FILES.items():
        file_path = RAW_DATA_DIR / filename
        if not file_path.exists():
            logger.error(f"[FAIL] Missing required file: {filename}")
            all_passed = False
            continue

        df = pd.read_csv(file_path)
        missing_cols = [c for c in required_cols if c not in df.columns]

        if missing_cols:
            logger.error(f"[FAIL] {filename} is missing required columns: {missing_cols}")
            all_passed = False
        else:
            logger.info(f"[PASS] {filename} ({len(df):,} records, {len(df.columns)} columns) - Schema valid.")
            summary.append({
                "File": filename,
                "Records": len(df),
                "Columns": len(df.columns),
                "Status": "VALID"
            })

    # Relational Integrity Check
    try:
        patients = pd.read_csv(RAW_DATA_DIR / "patients.csv")
        encounters = pd.read_csv(RAW_DATA_DIR / "encounters.csv")
        claims = pd.read_csv(RAW_DATA_DIR / "billing_claims.csv")

        # Check encounter patients exist in patients.csv
        patient_ids = set(patients["Id"])
        orphan_enc_patients = encounters[~encounters["PATIENT"].isin(patient_ids)]
        if len(orphan_enc_patients) == 0:
            logger.info("[PASS] Relational check: 100% of encounter patients exist in patients.csv")
        else:
            logger.warning(f"[WARN] {len(orphan_enc_patients)} encounters have orphan patient IDs.")

        # Check billing claim reconciliation categories
        cat_counts = claims["audit_category"].value_counts().to_dict()
        logger.info(f"[PASS] Billing Claims audit categories distribution: {cat_counts}")

    except Exception as e:
        logger.error(f"Integrity check failed with error: {e}")
        all_passed = False

    if all_passed:
        logger.info("=== Phase 1 Verification SUCCEEDED! All files and schemas verified. ===")
    else:
        logger.error("=== Phase 1 Verification FAILED. Please review above errors. ===")
        sys.exit(1)


if __name__ == "__main__":
    verify_dataset()
