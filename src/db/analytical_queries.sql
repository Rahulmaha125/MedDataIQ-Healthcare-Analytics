-- =====================================================================
-- MedDataIQ — Advanced Analytical SQL Queries
-- Demonstrating CTEs, Window Functions, Multi-Table Joins, and Healthcare KPIs
-- =====================================================================

-- -------------------------------------------------------------
-- QUERY 1: Provider Performance & Specialty Ranking
-- Concept: CTEs + Window Functions (DENSE_RANK, SUM OVER PARTITION)
-- Purpose: Identifies top clinicians per medical specialty and their 
--          percentage contribution to departmental revenue.
-- -------------------------------------------------------------
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
    organization_name,
    total_encounters,
    unique_patients,
    total_revenue,
    DENSE_RANK() OVER (
        PARTITION BY specialty 
        ORDER BY total_revenue DESC
    ) AS rank_within_specialty,
    ROUND(
        (total_revenue * 100.0) / SUM(total_revenue) OVER (PARTITION BY specialty), 
        2
    ) AS specialty_revenue_share_pct
FROM provider_metrics
ORDER BY specialty, rank_within_specialty;


-- -------------------------------------------------------------
-- QUERY 2: 30-Day Hospital Readmission Rate Analysis
-- Concept: Window Functions (LAG, OVER PARTITION BY patient)
-- Purpose: Analyzes time interval between successive hospital/emergency visits
--          to identify patients readmitted within 30 days (clinical quality KPI).
-- -------------------------------------------------------------
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
        patient_id,
        encounter_id,
        encounter_date,
        previous_visit_date,
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
    COUNT(encounter_id) AS total_acute_visits,
    SUM(CASE WHEN days_since_last_visit BETWEEN 1 AND 30 THEN 1 ELSE 0 END) AS readmissions_within_30d,
    ROUND(
        (SUM(CASE WHEN days_since_last_visit BETWEEN 1 AND 30 THEN 1 ELSE 0 END) * 100.0) / COUNT(encounter_id), 
        2
    ) AS readmission_rate_pct,
    ROUND(AVG(CASE WHEN days_since_last_visit BETWEEN 1 AND 30 THEN total_claim_cost END), 2) AS avg_readmission_cost
FROM readmission_intervals
GROUP BY encounter_class;


-- -------------------------------------------------------------
-- QUERY 3: Service-to-Billing Reconciliation & Financial Exposure
-- Concept: Full outer reconciliation analysis + Risk Categorization
-- Purpose: Quantifies unbilled clinical revenue, overbilled charges,
--          and potential financial leakage across clinical departments.
-- -------------------------------------------------------------
WITH reconciliation_detail AS (
    SELECT 
        reconciliation_status,
        COUNT(*) AS record_count,
        ROUND(SUM(clinical_encounter_cost), 2) AS total_clinical_cost,
        ROUND(SUM(claim_billed_amount), 2) AS total_billed_amount,
        ROUND(SUM(variance_amount), 2) AS total_variance,
        ROUND(AVG(ABS(variance_amount)), 2) AS avg_absolute_variance
    FROM v_billing_reconciliation_summary
    GROUP BY reconciliation_status
)
SELECT 
    reconciliation_status,
    record_count,
    ROUND((record_count * 100.0) / (SELECT SUM(record_count) FROM reconciliation_detail), 2) AS pct_of_total_records,
    total_clinical_cost,
    total_billed_amount,
    total_variance,
    avg_absolute_variance,
    CASE 
        WHEN reconciliation_status = 'UNBILLED_SERVICE' THEN 'REVENUE_LEAKAGE_RISK'
        WHEN reconciliation_status = 'UNMATCHED_BILL' THEN 'COMPLIANCE_DOCUMENTATION_RISK'
        WHEN reconciliation_status = 'DUPLICATE_CLAIM' THEN 'OVERBILLING_DENIAL_RISK'
        WHEN reconciliation_status = 'AMOUNT_VARIANCE' THEN 'REIMBURSEMENT_DISCREPANCY'
        WHEN reconciliation_status = 'TIMING_SKEW' THEN 'TIMELY_FILING_DENIAL_RISK'
        ELSE 'LOW_RISK_PARITY'
    END AS audit_risk_tier
FROM reconciliation_detail
ORDER BY ABS(total_variance) DESC;


-- -------------------------------------------------------------
-- QUERY 4: High-Cost Patient Cohort (Pareto 80/20 Analysis)
-- Concept: Window Functions (NTILE decile segmentation, Cumulative Sum)
-- Purpose: Validates whether a small cohort of patients accounts for a
--          disproportionate share of lifetime healthcare expenditure.
-- -------------------------------------------------------------
WITH patient_deciles AS (
    SELECT 
        p.patient_id,
        p.first_name || ' ' || p.last_name AS patient_name,
        p.gender,
        p.age,
        p.lifetime_healthcare_expenses,
        p.lifetime_healthcare_coverage,
        (p.lifetime_healthcare_expenses + p.lifetime_healthcare_coverage) AS total_spend,
        NTILE(10) OVER (
            ORDER BY (p.lifetime_healthcare_expenses + p.lifetime_healthcare_coverage) DESC
        ) AS spend_decile
    FROM dim_patients p
)
SELECT 
    spend_decile,
    COUNT(patient_id) AS patient_count,
    ROUND(AVG(age), 1) AS avg_patient_age,
    ROUND(SUM(total_spend), 2) AS decile_total_spend,
    ROUND(
        (SUM(total_spend) * 100.0) / (SELECT SUM(total_spend) FROM patient_deciles), 
        2
    ) AS pct_of_total_healthcare_spend
FROM patient_deciles
GROUP BY spend_decile
ORDER BY spend_decile ASC;


-- -------------------------------------------------------------
-- QUERY 5: Hospital Facility Workload & Bed Utilization Efficiency
-- Concept: Multi-table JOINs, Density Aggregation
-- Purpose: Evaluates clinical volume per active doctor across hospital networks.
-- -------------------------------------------------------------
SELECT 
    o.organization_name,
    o.city,
    o.utilization_rate,
    COUNT(DISTINCT p.provider_id) AS active_physicians,
    COUNT(e.encounter_id) AS total_encounters,
    ROUND(COUNT(e.encounter_id) * 1.0 / NULLIF(COUNT(DISTINCT p.provider_id), 0), 1) AS visits_per_physician,
    ROUND(SUM(e.total_claim_cost), 2) AS total_billed_revenue,
    ROUND(SUM(e.total_claim_cost) / NULLIF(COUNT(DISTINCT p.provider_id), 0), 2) AS revenue_per_physician
FROM dim_organizations o
LEFT JOIN dim_providers p ON o.organization_id = p.organization_id
LEFT JOIN fact_encounters e ON p.provider_id = e.provider_id
GROUP BY o.organization_id, o.organization_name, o.city, o.utilization_rate
ORDER BY total_encounters DESC;
