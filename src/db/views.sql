-- =====================================================================
-- MedDataIQ — Analytical SQL Views (PostgreSQL 18 / ANSI SQL)
-- Reusable views for Streamlit dashboards and Power BI reporting
-- =====================================================================

-- -------------------------------------------------------------
-- 1. EXECUTIVE MONTHLY KPI VIEW
-- -------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_kpi_executive_monthly AS
SELECT 
    SUBSTR(e.encounter_date, 1, 7) AS year_month,
    COUNT(DISTINCT e.encounter_id) AS total_encounters,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    COUNT(DISTINCT e.provider_id) AS active_providers,
    ROUND(SUM(e.total_claim_cost), 2) AS total_billed_cost,
    ROUND(SUM(e.payer_coverage), 2) AS total_payer_coverage,
    ROUND(SUM(e.patient_cost), 2) AS total_patient_out_of_pocket,
    ROUND(AVG(e.duration_minutes), 1) AS avg_duration_minutes,
    ROUND(
        (SUM(e.payer_coverage) * 100.0) / NULLIF(SUM(e.total_claim_cost), 0), 
        2
    ) AS payer_coverage_rate_pct
FROM fact_encounters e
GROUP BY SUBSTR(e.encounter_date, 1, 7);

-- -------------------------------------------------------------
-- 2. ENCOUNTER CLASS & CLINICAL MIX SUMMARY
-- -------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_encounter_class_summary AS
SELECT 
    e.encounter_class,
    COUNT(e.encounter_id) AS encounter_count,
    ROUND(
        (COUNT(e.encounter_id) * 100.0) / (SELECT COUNT(*) FROM fact_encounters), 
        2
    ) AS volume_share_pct,
    COUNT(DISTINCT e.patient_id) AS unique_patients,
    ROUND(AVG(e.duration_minutes), 1) AS avg_duration_minutes,
    ROUND(SUM(e.total_claim_cost), 2) AS total_cost,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_cost_per_encounter,
    ROUND(SUM(e.payer_coverage), 2) AS total_payer_coverage,
    ROUND(SUM(e.patient_cost), 2) AS total_patient_cost
FROM fact_encounters e
GROUP BY e.encounter_class;

-- -------------------------------------------------------------
-- 3. PROVIDER WORKLOAD & REVENUE ATTRIBUTION
-- -------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_provider_workload AS
SELECT 
    p.provider_id,
    p.provider_name,
    p.specialty,
    o.organization_name,
    COUNT(e.encounter_id) AS total_encounters,
    COUNT(DISTINCT e.patient_id) AS unique_patients_treated,
    ROUND(SUM(e.total_claim_cost), 2) AS total_revenue_generated,
    ROUND(AVG(e.total_claim_cost), 2) AS avg_revenue_per_encounter,
    ROUND(AVG(e.duration_minutes), 1) AS avg_encounter_duration_mins,
    SUM(CASE WHEN e.encounter_class IN ('emergency', 'inpatient') THEN 1 ELSE 0 END) AS high_intensity_visits
FROM dim_providers p
LEFT JOIN dim_organizations o ON p.organization_id = o.organization_id
LEFT JOIN fact_encounters e ON p.provider_id = e.provider_id
GROUP BY p.provider_id, p.provider_name, p.specialty, o.organization_name;

-- -------------------------------------------------------------
-- 4. SERVICE-TO-BILLING RECONCILIATION AUDIT VIEW
-- Full outer join between clinical encounters and billing claims
-- Uses window function ranking to prevent clinical cost double-counting on duplicate claims.
-- -------------------------------------------------------------
DROP VIEW IF EXISTS v_billing_reconciliation_summary;

CREATE VIEW v_billing_reconciliation_summary AS
WITH ranked_claims AS (
    SELECT 
        c.*,
        ROW_NUMBER() OVER (
            PARTITION BY c.encounter_id 
            ORDER BY 
                CASE 
                    WHEN c.audit_category = 'DUPLICATE_CLAIM' OR c.claim_number LIKE '%-DUP' THEN 2 
                    ELSE 1 
                END, 
                c.claim_number
        ) AS claim_seq
    FROM fact_billing_claims c
)
SELECT 
    COALESCE(c.claim_id, e.encounter_id) AS reconciliation_key,
    e.encounter_id,
    c.claim_id,
    c.claim_number,
    COALESCE(e.patient_id, c.patient_id) AS patient_id,
    COALESCE(e.provider_id, c.provider_id) AS provider_id,
    COALESCE(e.encounter_date, c.service_date) AS service_date,
    e.encounter_class,
    -- Attribute clinical encounter cost ONLY to the primary claim (claim_seq = 1) or unbilled encounter
    ROUND(
        CASE 
            WHEN c.claim_seq > 1 THEN 0.0 
            ELSE COALESCE(e.total_claim_cost, 0.0) 
        END, 
        2
    ) AS clinical_encounter_cost,
    ROUND(COALESCE(c.billed_amount, 0.0), 2) AS claim_billed_amount,
    ROUND(COALESCE(c.paid_amount, 0.0), 2) AS claim_paid_amount,
    ROUND(
        COALESCE(c.billed_amount, 0.0) - 
        (CASE WHEN c.claim_seq > 1 THEN 0.0 ELSE COALESCE(e.total_claim_cost, 0.0) END), 
        2
    ) AS variance_amount,
    c.claim_status,
    c.audit_category,
    c.is_duplicate_claim,
    c.claim_seq,
    CASE 
        WHEN c.claim_id IS NULL THEN 'UNBILLED_SERVICE'
        WHEN e.encounter_id IS NULL THEN 'UNMATCHED_BILL'
        WHEN c.claim_seq > 1 OR c.audit_category = 'DUPLICATE_CLAIM' THEN 'DUPLICATE_CLAIM'
        WHEN ABS(COALESCE(c.billed_amount, 0.0) - COALESCE(e.total_claim_cost, 0.0)) > 1.0 THEN 'AMOUNT_VARIANCE'
        WHEN c.audit_category = 'TIMING_SKEW' THEN 'TIMING_SKEW'
        ELSE 'CLEAN_MATCH'
    END AS reconciliation_status
FROM fact_encounters e
LEFT JOIN ranked_claims c ON e.encounter_id = c.encounter_id

UNION ALL

-- Catch orphan claims (claims that reference an encounter_id not present in fact_encounters)
SELECT 
    c.claim_id AS reconciliation_key,
    NULL AS encounter_id,
    c.claim_id,
    c.claim_number,
    c.patient_id,
    c.provider_id,
    c.service_date,
    NULL AS encounter_class,
    0.0 AS clinical_encounter_cost,
    ROUND(c.billed_amount, 2) AS claim_billed_amount,
    ROUND(c.paid_amount, 2) AS claim_paid_amount,
    ROUND(c.billed_amount, 2) AS variance_amount,
    c.claim_status,
    c.audit_category,
    c.is_duplicate_claim,
    1 AS claim_seq,
    'UNMATCHED_BILL' AS reconciliation_status
FROM fact_billing_claims c
WHERE c.encounter_id NOT IN (SELECT encounter_id FROM fact_encounters);
