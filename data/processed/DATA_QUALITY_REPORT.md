# MedDataIQ — Healthcare Data Quality Audit Report

**Audit Execution Timestamp:** 2026-10-27 19:50:44  
**Overall Data Quality Index:** `90.7%`  
**Total Rules Evaluated:** `43` | **Passed:** `39` | **Flagged for Review:** `4` | **Critical Failures:** `0`

> [!NOTE]
> Detected discrepancies reflect real-world healthcare operational noise and controlled audit scenarios (e.g. duplicate claims, late filings, unmatched bills). They are labeled as **flagged issues for investigation** rather than confirmed systemic errors.

## 1. Executive Dimension Summary

| Dimension | Total Rules | Passed | Flagged | Pass Rate |
| :--- | :---: | :---: | :---: | :---: |
| **Completeness** | 15 | 15 | 0 | 100.0% |
| **Uniqueness** | 7 | 6 | 1 | 85.7% |
| **Validity** | 5 | 5 | 0 | 100.0% |
| **Timeliness** | 4 | 2 | 2 | 50.0% |
| **Consistency** | 4 | 4 | 0 | 100.0% |
| **Referential Integrity** | 8 | 7 | 1 | 87.5% |

## 2. Detailed Rule Evaluation Table

| Dataset | Rule Name | Dimension | Severity | Affected Rows | Rate | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :--- |
| `dim_patients` | `mandatory_field_patient_id` | Completeness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `dim_patients` | `mandatory_field_birth_date` | Completeness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `dim_patients` | `mandatory_field_first_name` | Completeness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `dim_patients` | `mandatory_field_last_name` | Completeness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `dim_patients` | `mandatory_field_gender` | Completeness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `dim_patients` | `mandatory_field_zip_code` | Completeness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `fact_encounters` | `mandatory_field_encounter_id` | Completeness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `mandatory_field_patient_id` | Completeness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `mandatory_field_provider_id` | Completeness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `mandatory_field_start_time` | Completeness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `mandatory_field_total_claim_cost` | Completeness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `mandatory_field_claim_id` | Completeness | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `mandatory_field_patient_id` | Completeness | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `mandatory_field_billed_amount` | Completeness | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `mandatory_field_claim_status` | Completeness | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `dim_patients` | `pk_uniqueness_patient_id` | Uniqueness | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `fact_encounters` | `pk_uniqueness_encounter_id` | Uniqueness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `dim_providers` | `pk_uniqueness_provider_id` | Uniqueness | CRITICAL | 0 / 30 | 0.0% | ✅ PASSED |
| `dim_organizations` | `pk_uniqueness_organization_id` | Uniqueness | CRITICAL | 0 / 6 | 0.0% | ✅ PASSED |
| `dim_payers` | `pk_uniqueness_payer_id` | Uniqueness | CRITICAL | 0 / 7 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `pk_uniqueness_claim_id` | Uniqueness | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `duplicate_claim_submissions` | Uniqueness | WARNING | 480 / 5,770 | 8.32% | ⚠️ FLAGGED |
| `dim_patients` | `gender_domain_validity` | Validity | WARNING | 0 / 1,000 | 0.0% | ✅ PASSED |
| `dim_patients` | `age_physiological_range` | Validity | CRITICAL | 0 / 1,000 | 0.0% | ✅ PASSED |
| `fact_encounters` | `non_negative_encounter_cost` | Validity | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `encounter_class_domain` | Validity | WARNING | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `positive_billed_amount` | Validity | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `fact_encounters` | `encounter_duration_logical` | Timeliness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `no_future_encounters` | Timeliness | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `claim_submitted_after_service` | Timeliness | WARNING | 136 / 5,770 | 2.36% | ⚠️ FLAGGED |
| `fact_billing_claims` | `timely_filing_limit_120d` | Timeliness | INFO | 248 / 5,770 | 4.3% | ⚠️ FLAGGED |
| `fact_encounters` | `payer_coverage_within_claim_total` | Consistency | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `allowed_amount_within_billed` | Consistency | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `paid_amount_within_allowed` | Consistency | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |
| `dim_patients` | `death_date_after_birth_date` | Consistency | CRITICAL | 0 / 22 | 0.0% | ✅ PASSED |
| `fact_encounters` | `fk_encounter_patient` | Referential Integrity | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `fk_encounter_provider` | Referential Integrity | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `fk_encounter_organization` | Referential Integrity | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_encounters` | `fk_encounter_payer` | Referential Integrity | CRITICAL | 0 / 5,730 | 0.0% | ✅ PASSED |
| `fact_procedures` | `fk_procedure_encounter` | Referential Integrity | CRITICAL | 0 / 3,171 | 0.0% | ✅ PASSED |
| `fact_medications` | `fk_medication_encounter` | Referential Integrity | CRITICAL | 0 / 2,529 | 0.0% | ✅ PASSED |
| `fact_billing_claims` | `fk_claim_to_clinical_encounter` | Referential Integrity | WARNING | 40 / 5,770 | 0.69% | ⚠️ FLAGGED |
| `fact_billing_claims` | `fk_claim_patient` | Referential Integrity | CRITICAL | 0 / 5,770 | 0.0% | ✅ PASSED |

## 3. Discrepancy Investigation Drill-Down

### 1. duplicate_claim_submissions (fact_billing_claims)
- **Dimension:** Uniqueness
- **Severity:** `WARNING` | **Category:** `POTENTIAL_DUPLICATE_CLAIM`
- **Description:** Flags multiple claims with identical patient, provider, service date, and amount.
- **Affected Records:** `480` out of `5,770` (8.32%)
- **Sample Examples:** `CLM-2026-100027, CLM-2026-100028-DUP, CLM-2026-100036, CLM-2026-100037-DUP, CLM-2026-100051`

### 2. claim_submitted_after_service (fact_billing_claims)
- **Dimension:** Timeliness
- **Severity:** `WARNING` | **Category:** `POTENTIAL_PREMATURE_BILLING`
- **Description:** Claim submission date should not occur prior to the date service was rendered.
- **Affected Records:** `136` out of `5,770` (2.36%)
- **Sample Examples:** `CLM-2026-100020, CLM-2026-100127, CLM-2026-100134, CLM-2026-100266, CLM-2026-100307`

### 3. timely_filing_limit_120d (fact_billing_claims)
- **Dimension:** Timeliness
- **Severity:** `INFO` | **Category:** `POTENTIAL_STALE_CLAIM`
- **Description:** Claims submitted more than 120 days after service are flagged for timely-filing review.
- **Affected Records:** `248` out of `5,770` (4.3%)
- **Sample Examples:** `CLM-2026-100019, CLM-2026-100082, CLM-2026-100086, CLM-2026-100116, CLM-2026-100135`

### 4. fk_claim_to_clinical_encounter (fact_billing_claims)
- **Dimension:** Referential Integrity
- **Severity:** `WARNING` | **Category:** `POTENTIAL_ORPHAN_BILLING_CLAIM`
- **Description:** Billing claim encounter_id should map to a valid clinical visit. Orphan bills are flagged for investigation.
- **Affected Records:** `40` out of `5,770` (0.69%)
- **Sample Examples:** `CLM-2026-105731-UNMATCHED, CLM-2026-105732-UNMATCHED, CLM-2026-105733-UNMATCHED, CLM-2026-105734-UNMATCHED, CLM-2026-105735-UNMATCHED`

