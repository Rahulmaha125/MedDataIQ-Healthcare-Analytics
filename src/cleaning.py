"""
MedDataIQ — Healthcare Data Cleaning & Standardization Module
Phase 2: Cleans raw datasets, standardizes dates, numeric fields, and schemas,
handles missing values carefully, and flags duplicates without deletion.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from src.config import PROCESSED_DATA_DIR, RAW_DATA_DIR, setup_logging

logger = setup_logging("CleaningModule")

SIMULATION_DATE = datetime(2026, 10, 27)


def clean_patients(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes the patients demographic dataset."""
    df = df.copy()

    # Column renaming to standard snake_case
    rename_map = {
        "Id": "patient_id",
        "BIRTHDATE": "birth_date",
        "DEATHDATE": "death_date",
        "SSN": "ssn",
        "DRIVERS": "drivers_license",
        "PASSPORT": "passport",
        "PREFIX": "prefix",
        "FIRST": "first_name",
        "LAST": "last_name",
        "SUFFIX": "suffix",
        "MAIDEN": "maiden_name",
        "MARITAL": "marital_status",
        "RACE": "race",
        "ETHNICITY": "ethnicity",
        "GENDER": "gender",
        "BIRTHPLACE": "birthplace",
        "ADDRESS": "address",
        "CITY": "city",
        "STATE": "state",
        "COUNTY": "county",
        "ZIP": "zip_code",
        "LAT": "latitude",
        "LON": "longitude",
        "HEALTHCARE_EXPENSES": "lifetime_healthcare_expenses",
        "HEALTHCARE_COVERAGE": "lifetime_healthcare_coverage",
        "INCOME": "annual_income"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Standardize string fields
    string_cols = ["first_name", "last_name", "prefix", "suffix", "maiden_name",
                   "marital_status", "race", "ethnicity", "gender", "city", "state", "county", "zip_code"]
    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "None": None, "": None})

    # Standardize dates
    df["birth_date"] = pd.to_datetime(df["birth_date"], errors="coerce")
    df["death_date"] = pd.to_datetime(df["death_date"], errors="coerce")

    # Add explicit boolean indicator for mortality
    df["is_deceased"] = df["death_date"].notnull()

    # Calculate patient age (as of death date or simulation date)
    ref_date = df["death_date"].fillna(pd.Timestamp(SIMULATION_DATE))
    df["age"] = ((ref_date - df["birth_date"]).dt.days / 365.25).round(1)

    # Standardize numerics
    for col in ["latitude", "longitude", "lifetime_healthcare_expenses", "lifetime_healthcare_coverage", "annual_income"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Format dates as ISO string for clean CSV export
    df["birth_date"] = df["birth_date"].dt.strftime("%Y-%m-%d")
    df["death_date"] = df["death_date"].dt.strftime("%Y-%m-%d")

    return df


def clean_encounters(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes clinical encounters."""
    df = df.copy()

    rename_map = {
        "Id": "encounter_id",
        "START": "start_time",
        "STOP": "stop_time",
        "PATIENT": "patient_id",
        "ORGANIZATION": "organization_id",
        "PROVIDER": "provider_id",
        "PAYER": "payer_id",
        "ENCOUNTERCLASS": "encounter_class",
        "CODE": "encounter_code",
        "DESCRIPTION": "encounter_description",
        "BASE_ENCOUNTER_COST": "base_encounter_cost",
        "TOTAL_CLAIM_COST": "total_claim_cost",
        "PAYER_COVERAGE": "payer_coverage",
        "REASONCODE": "reason_code",
        "REASONDESCRIPTION": "reason_description"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Standardize strings
    for col in ["encounter_class", "encounter_description", "reason_description"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.lower()

    # Standardize timestamps
    start_dt = pd.to_datetime(df["start_time"], errors="coerce")
    stop_dt = pd.to_datetime(df["stop_time"], errors="coerce")

    # Calculate clinical encounter duration in minutes
    df["duration_minutes"] = ((stop_dt - start_dt).dt.total_seconds() / 60.0).round(1)
    df["encounter_date"] = start_dt.dt.strftime("%Y-%m-%d")

    # Standardize cost numerics
    for col in ["base_encounter_cost", "total_claim_cost", "payer_coverage"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # Calculate patient out-of-pocket responsibility
    df["patient_cost"] = (df["total_claim_cost"] - df["payer_coverage"]).round(2)

    # Format timestamps
    df["start_time"] = start_dt.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["stop_time"] = stop_dt.dt.strftime("%Y-%m-%d %H:%M:%S")

    return df


def clean_procedures(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes clinical procedures."""
    df = df.copy()

    rename_map = {
        "START": "start_time",
        "STOP": "stop_time",
        "PATIENT": "patient_id",
        "ENCOUNTER": "encounter_id",
        "CODE": "procedure_code",
        "DESCRIPTION": "procedure_description",
        "BASE_COST": "base_cost",
        "REASONCODE": "reason_code",
        "REASONDESCRIPTION": "reason_description"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    start_dt = pd.to_datetime(df["start_time"], errors="coerce")
    stop_dt = pd.to_datetime(df["stop_time"], errors="coerce")

    df["procedure_date"] = start_dt.dt.strftime("%Y-%m-%d")
    df["start_time"] = start_dt.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["stop_time"] = stop_dt.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["base_cost"] = pd.to_numeric(df["base_cost"], errors="coerce").round(2)

    return df


def clean_medications(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes prescription medications."""
    df = df.copy()

    rename_map = {
        "START": "start_time",
        "STOP": "stop_time",
        "PATIENT": "patient_id",
        "PAYER": "payer_id",
        "ENCOUNTER": "encounter_id",
        "CODE": "medication_code",
        "DESCRIPTION": "medication_description",
        "BASE_COST": "base_cost",
        "PAYER_COVERAGE": "payer_coverage",
        "DISPENSES": "dispenses",
        "TOTAL_COST": "total_cost",
        "REASONCODE": "reason_code",
        "REASONDESCRIPTION": "reason_description"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    start_dt = pd.to_datetime(df["start_time"], errors="coerce")
    stop_dt = pd.to_datetime(df["stop_time"], errors="coerce")

    df["prescription_date"] = start_dt.dt.strftime("%Y-%m-%d")
    df["start_time"] = start_dt.dt.strftime("%Y-%m-%d %H:%M:%S")
    df["stop_time"] = stop_dt.dt.strftime("%Y-%m-%d %H:%M:%S")

    for col in ["base_cost", "payer_coverage", "total_cost"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    df["dispenses"] = pd.to_numeric(df["dispenses"], errors="coerce").fillna(1).astype(int)
    return df


def clean_organizations(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes healthcare organization facilities."""
    df = df.copy()
    rename_map = {
        "Id": "organization_id",
        "NAME": "organization_name",
        "ADDRESS": "address",
        "CITY": "city",
        "STATE": "state",
        "ZIP": "zip_code",
        "LAT": "latitude",
        "LON": "longitude",
        "PHONE": "phone",
        "REVENUE": "revenue",
        "UTILIZATION": "utilization_rate"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").round(2)
    df["utilization_rate"] = pd.to_numeric(df["utilization_rate"], errors="coerce").round(1)
    return df


def clean_providers(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes clinician providers."""
    df = df.copy()
    rename_map = {
        "Id": "provider_id",
        "ORGANIZATION": "organization_id",
        "NAME": "provider_name",
        "GENDER": "gender",
        "SPECIALITY": "specialty",
        "ADDRESS": "address",
        "CITY": "city",
        "STATE": "state",
        "ZIP": "zip_code",
        "LAT": "latitude",
        "LON": "longitude"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


def clean_payers(df: pd.DataFrame) -> pd.DataFrame:
    """Cleans and standardizes insurance payers."""
    df = df.copy()
    rename_map = {
        "Id": "payer_id",
        "NAME": "payer_name",
        "ADDRESS": "address",
        "CITY": "city",
        "STATE_HEADQUARTERS": "state",
        "ZIP": "zip_code",
        "PHONE": "phone"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
    return df


def clean_billing_claims(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans and standardizes billing claims.
    Detects duplicate claims without deleting them, marking them via `is_duplicate_claim`.
    """
    df = df.copy()

    # Ensure standard types
    df["service_date"] = pd.to_datetime(df["service_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["claim_submission_date"] = pd.to_datetime(df["claim_submission_date"], errors="coerce").dt.strftime("%Y-%m-%d")

    for col in ["billed_amount", "allowed_amount", "paid_amount", "patient_responsibility"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").round(2)

    # Flag duplicate claims based on business key (patient + provider + service_date + billed_amount)
    business_cols = ["patient_id", "provider_id", "service_date", "billed_amount"]
    df["is_duplicate_claim"] = df.duplicated(subset=business_cols, keep=False)

    return df


def run_cleaning_pipeline(raw_dir: Path = RAW_DATA_DIR, processed_dir: Path = PROCESSED_DATA_DIR) -> Dict[str, pd.DataFrame]:
    """
    Executes the full cleaning pipeline and writes cleaned datasets to data/processed/.
    Preserves all data/raw/ files untouched.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Starting MedDataIQ Cleaning Pipeline...")

    cleaners = {
        "patients.csv": ("dim_patients", clean_patients),
        "encounters.csv": ("fact_encounters", clean_encounters),
        "procedures.csv": ("fact_procedures", clean_procedures),
        "medications.csv": ("fact_medications", clean_medications),
        "organizations.csv": ("dim_organizations", clean_organizations),
        "providers.csv": ("dim_providers", clean_providers),
        "payers.csv": ("dim_payers", clean_payers),
        "billing_claims.csv": ("fact_billing_claims", clean_billing_claims),
    }

    cleaned_dfs = {}

    for raw_filename, (processed_name, clean_func) in cleaners.items():
        raw_path = raw_dir / raw_filename
        if not raw_path.exists():
            logger.warning(f"File {raw_filename} not found in {raw_dir}, skipping.")
            continue

        raw_df = pd.read_csv(raw_path)
        logger.info(f"Cleaning {raw_filename} ({len(raw_df)} rows)...")

        cleaned_df = clean_func(raw_df)
        cleaned_dfs[processed_name] = cleaned_df

        # Save to processed/ as CSV
        csv_out = processed_dir / f"{processed_name}.csv"
        cleaned_df.to_csv(csv_out, index=False)

        # Save to processed/ as Parquet for fast analytics
        try:
            parquet_out = processed_dir / f"{processed_name}.parquet"
            cleaned_df.to_parquet(parquet_out, index=False)
        except Exception as e:
            logger.debug(f"Parquet export skipped: {e}")

        logger.info(f"Saved {processed_name} ({len(cleaned_df)} rows, {len(cleaned_df.columns)} cols) to {csv_out}")

    logger.info("Cleaning pipeline completed successfully!")
    return cleaned_dfs


if __name__ == "__main__":
    run_cleaning_pipeline()
