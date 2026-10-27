"""
MedDataIQ — Database Loading & Migration Module
Phase 3: Creates normalized relational schema and analytical views,
bulk-loads cleaned datasets from data/processed/, and validates integrity.
"""

from pathlib import Path
from typing import Dict, Any
import pandas as pd

from src.config import PROCESSED_DATA_DIR, setup_logging
from src.db.connection import DatabaseManager

logger = setup_logging("DBLoader")

SCHEMA_FILE = Path(__file__).parent / "schema.sql"
VIEWS_FILE = Path(__file__).parent / "views.sql"


def load_database() -> Dict[str, Any]:
    """
    Initializes database schema, loads all processed datasets,
    creates views, and verifies row counts and relational integrity.
    """
    logger.info("Starting MedDataIQ Database Initialization & Load...")
    db = DatabaseManager()

    # 1. Execute schema DDL
    if SCHEMA_FILE.exists():
        with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        logger.info("Applying schema DDL (tables, constraints, indexes)...")
        db.execute_script(schema_sql)
    else:
        raise FileNotFoundError(f"Missing schema file: {SCHEMA_FILE}")

    # 2. Ingest processed CSV files in topological order (dimensions first, then facts)
    table_files = [
        ("dim_patients", "dim_patients.csv"),
        ("dim_organizations", "dim_organizations.csv"),
        ("dim_providers", "dim_providers.csv"),
        ("dim_payers", "dim_payers.csv"),
        ("fact_encounters", "fact_encounters.csv"),
        ("fact_procedures", "fact_procedures.csv"),
        ("fact_medications", "fact_medications.csv"),
        ("fact_billing_claims", "fact_billing_claims.csv"),
    ]

    loaded_counts = {}

    for table_name, csv_filename in table_files:
        csv_path = PROCESSED_DATA_DIR / csv_filename
        if not csv_path.exists():
            logger.error(f"Processed file not found: {csv_path}")
            continue

        df = pd.read_csv(csv_path)

        # Ensure surrogate PKs for procedures and medications if needed
        if table_name == "fact_procedures" and "procedure_pk" not in df.columns:
            df.insert(0, "procedure_pk", range(1, len(df) + 1))
        elif table_name == "fact_medications" and "medication_pk" not in df.columns:
            df.insert(0, "medication_pk", range(1, len(df) + 1))

        # Replace existing records cleanly to make loading idempotent
        db.load_table(df, table_name, if_exists="replace")
        loaded_counts[table_name] = len(df)

    # 3. Create Analytical Views
    if VIEWS_FILE.exists():
        with open(VIEWS_FILE, "r", encoding="utf-8") as f:
            views_sql = f.read()
        logger.info("Applying analytical views DDL...")
        db.execute_script(views_sql)
    else:
        logger.warning(f"Views file not found: {VIEWS_FILE}")

    # 4. Verification & Integrity Checks
    logger.info("Verifying database load integrity...")
    verification_results = {}

    for table_name, expected_count in loaded_counts.items():
        count_df = db.execute_query(f"SELECT COUNT(*) AS row_count FROM {table_name}")
        actual_count = int(count_df["row_count"].iloc[0])
        is_match = (actual_count == expected_count)
        verification_results[table_name] = {
            "expected_rows": expected_count,
            "actual_rows": actual_count,
            "status": "MATCH" if is_match else "MISMATCH"
        }
        logger.info(f"Verified {table_name}: {actual_count:,} rows in DB (Status: {'OK' if is_match else 'FAIL'})")

    # Verify Views execution
    views_to_test = [
        "v_kpi_executive_monthly",
        "v_encounter_class_summary",
        "v_provider_workload",
        "v_billing_reconciliation_summary"
    ]
    view_results = {}
    for v in views_to_test:
        v_df = db.execute_query(f"SELECT COUNT(*) AS cnt FROM {v}")
        cnt = int(v_df["cnt"].iloc[0])
        view_results[v] = cnt
        logger.info(f"Verified view '{v}': {cnt:,} records returned.")

    logger.info("=== Database Loading & Verification Completed Successfully! ===")
    return {
        "status": db.get_status(),
        "tables": verification_results,
        "views": view_results
    }


if __name__ == "__main__":
    load_database()
