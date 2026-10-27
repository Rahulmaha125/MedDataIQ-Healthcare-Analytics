-- =====================================================================
-- MedDataIQ — Relational Database Schema (PostgreSQL 18 / ANSI SQL)
-- Star / Snowflake Schema for Healthcare Analytics & Billing Quality Audit
-- =====================================================================

-- -------------------------------------------------------------
-- 1. DIMENSION TABLES
-- -------------------------------------------------------------

-- Patients Dimension
CREATE TABLE IF NOT EXISTS dim_patients (
    patient_id VARCHAR(64) PRIMARY KEY,
    birth_date DATE NOT NULL,
    death_date DATE,
    ssn VARCHAR(20),
    drivers_license VARCHAR(30),
    passport VARCHAR(30),
    prefix VARCHAR(20),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    suffix VARCHAR(20),
    maiden_name VARCHAR(100),
    marital_status VARCHAR(10),
    race VARCHAR(50),
    ethnicity VARCHAR(50),
    gender VARCHAR(10) CHECK (gender IN ('M', 'F', 'OTHER')),
    birthplace VARCHAR(255),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    county VARCHAR(100),
    zip_code VARCHAR(20),
    latitude NUMERIC(10, 4),
    longitude NUMERIC(10, 4),
    lifetime_healthcare_expenses NUMERIC(12, 2) DEFAULT 0.0,
    lifetime_healthcare_coverage NUMERIC(12, 2) DEFAULT 0.0,
    annual_income NUMERIC(12, 2),
    is_deceased BOOLEAN DEFAULT FALSE,
    age NUMERIC(5, 1) CHECK (age >= 0 AND age <= 125)
);

-- Organizations (Hospitals & Facilities) Dimension
CREATE TABLE IF NOT EXISTS dim_organizations (
    organization_id VARCHAR(64) PRIMARY KEY,
    organization_name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    latitude NUMERIC(10, 4),
    longitude NUMERIC(10, 4),
    phone VARCHAR(50),
    revenue NUMERIC(15, 2),
    utilization_rate NUMERIC(5, 2)
);

-- Providers (Physicians & Clinicians) Dimension
CREATE TABLE IF NOT EXISTS dim_providers (
    provider_id VARCHAR(64) PRIMARY KEY,
    organization_id VARCHAR(64) REFERENCES dim_organizations(organization_id),
    provider_name VARCHAR(255) NOT NULL,
    gender VARCHAR(10),
    specialty VARCHAR(100),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    latitude NUMERIC(10, 4),
    longitude NUMERIC(10, 4)
);

-- Payers (Insurance Companies) Dimension
CREATE TABLE IF NOT EXISTS dim_payers (
    payer_id VARCHAR(64) PRIMARY KEY,
    payer_name VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    phone VARCHAR(50)
);

-- -------------------------------------------------------------
-- 2. FACT TABLES
-- -------------------------------------------------------------

-- Encounters (Clinical Visits) Fact Table
CREATE TABLE IF NOT EXISTS fact_encounters (
    encounter_id VARCHAR(64) PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    stop_time TIMESTAMP NOT NULL,
    patient_id VARCHAR(64) NOT NULL REFERENCES dim_patients(patient_id),
    organization_id VARCHAR(64) NOT NULL REFERENCES dim_organizations(organization_id),
    provider_id VARCHAR(64) NOT NULL REFERENCES dim_providers(provider_id),
    payer_id VARCHAR(64) NOT NULL REFERENCES dim_payers(payer_id),
    encounter_class VARCHAR(50) NOT NULL,
    encounter_code VARCHAR(50),
    encounter_description VARCHAR(255),
    base_encounter_cost NUMERIC(12, 2) DEFAULT 0.0 CHECK (base_encounter_cost >= 0),
    total_claim_cost NUMERIC(12, 2) DEFAULT 0.0 CHECK (total_claim_cost >= 0),
    payer_coverage NUMERIC(12, 2) DEFAULT 0.0 CHECK (payer_coverage >= 0),
    reason_code VARCHAR(50),
    reason_description VARCHAR(255),
    duration_minutes NUMERIC(10, 1) CHECK (duration_minutes >= 0),
    encounter_date DATE NOT NULL,
    patient_cost NUMERIC(12, 2) DEFAULT 0.0
);

-- Procedures Fact Table
CREATE TABLE IF NOT EXISTS fact_procedures (
    procedure_pk INTEGER PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    stop_time TIMESTAMP,
    patient_id VARCHAR(64) NOT NULL REFERENCES dim_patients(patient_id),
    encounter_id VARCHAR(64) NOT NULL REFERENCES fact_encounters(encounter_id),
    procedure_code VARCHAR(50) NOT NULL,
    procedure_description VARCHAR(255),
    base_cost NUMERIC(12, 2) DEFAULT 0.0,
    reason_code VARCHAR(50),
    reason_description VARCHAR(255),
    procedure_date DATE NOT NULL
);

-- Medications Fact Table
CREATE TABLE IF NOT EXISTS fact_medications (
    medication_pk INTEGER PRIMARY KEY,
    start_time TIMESTAMP NOT NULL,
    stop_time TIMESTAMP,
    patient_id VARCHAR(64) NOT NULL REFERENCES dim_patients(patient_id),
    payer_id VARCHAR(64) NOT NULL REFERENCES dim_payers(payer_id),
    encounter_id VARCHAR(64) NOT NULL REFERENCES fact_encounters(encounter_id),
    medication_code VARCHAR(50) NOT NULL,
    medication_description VARCHAR(255),
    base_cost NUMERIC(12, 2) DEFAULT 0.0,
    payer_coverage NUMERIC(12, 2) DEFAULT 0.0,
    dispenses INTEGER DEFAULT 1,
    total_cost NUMERIC(12, 2) DEFAULT 0.0,
    reason_code VARCHAR(50),
    reason_description VARCHAR(255),
    prescription_date DATE NOT NULL
);

-- Billing Claims Fact Table
-- Note: encounter_id is intentionally unconstrained by a hard FK so that unmatched/ghost
-- billing claims (e.g. claims billed without a clinical visit) are preserved for audit.
CREATE TABLE IF NOT EXISTS fact_billing_claims (
    claim_id VARCHAR(64) PRIMARY KEY,
    claim_number VARCHAR(100) NOT NULL,
    encounter_id VARCHAR(64),
    patient_id VARCHAR(64) NOT NULL REFERENCES dim_patients(patient_id),
    provider_id VARCHAR(64) NOT NULL REFERENCES dim_providers(provider_id),
    payer_id VARCHAR(64) NOT NULL REFERENCES dim_payers(payer_id),
    service_date DATE NOT NULL,
    claim_submission_date DATE NOT NULL,
    billed_amount NUMERIC(12, 2) NOT NULL CHECK (billed_amount > 0),
    allowed_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    paid_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    patient_responsibility NUMERIC(12, 2) NOT NULL DEFAULT 0.0,
    claim_status VARCHAR(50) NOT NULL,
    audit_category VARCHAR(50) NOT NULL,
    is_duplicate_claim BOOLEAN DEFAULT FALSE
);

-- -------------------------------------------------------------
-- 3. PERFORMANCE INDEXES
-- -------------------------------------------------------------

CREATE INDEX IF NOT EXISTS idx_enc_patient ON fact_encounters(patient_id);
CREATE INDEX IF NOT EXISTS idx_enc_provider ON fact_encounters(provider_id);
CREATE INDEX IF NOT EXISTS idx_enc_org ON fact_encounters(organization_id);
CREATE INDEX IF NOT EXISTS idx_enc_date ON fact_encounters(encounter_date);
CREATE INDEX IF NOT EXISTS idx_enc_class ON fact_encounters(encounter_class);

CREATE INDEX IF NOT EXISTS idx_proc_encounter ON fact_procedures(encounter_id);
CREATE INDEX IF NOT EXISTS idx_med_encounter ON fact_medications(encounter_id);

CREATE INDEX IF NOT EXISTS idx_claims_encounter ON fact_billing_claims(encounter_id);
CREATE INDEX IF NOT EXISTS idx_claims_patient ON fact_billing_claims(patient_id);
CREATE INDEX IF NOT EXISTS idx_claims_service_date ON fact_billing_claims(service_date);
CREATE INDEX IF NOT EXISTS idx_claims_audit_cat ON fact_billing_claims(audit_category);
CREATE INDEX IF NOT EXISTS idx_claims_status ON fact_billing_claims(claim_status);
