# MedDataIQ — Healthcare Service-to-Billing Reconciliation Report

**Audit Execution Timestamp:** 2026-10-27 19:50:46  
**Clean Parity Rate:** `75.99%` | **Discrepancy Rate:** `24.01%`  
**Total Records Audited:** `6,010` | **Clean Matches:** `4,567` | **Flagged for Review:** `1,443`

## 1. Executive Financial Reconciliation

| Financial Metric | Amount ($) | Description |
| :--- | :---: | :--- |
| **Total Clinical Encounter Cost** | `$4,501,299.15` | Baseline cost of clinical services rendered in EHR. |
| **Total Claim Amount Billed** | `$4,560,904.11` | Total charges submitted to payers on billing claims. |
| **Total Insurance Paid Amount** | `$3,343,206.23` | Total reimbursement received from payers. |
| **Net Overall Financial Variance** | `$59,604.96` | Mathematical variance (`Total Billed - Total Clinical`). |
| **Total Financial Exposure at Risk** | `$640,735.14` | Cumulative absolute dollar variance across all flagged categories. |

## 2. Discrepancy Category Breakdown

| Reconciliation Status | Records | Share (%) | Clinical Cost ($) | Billed Amount ($) | Variance ($) | Risk Tier |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **`UNBILLED_SERVICE`** | 240 | 3.99% | $224,443.42 | $0.00 | $-224,443.42 | `HIGH` |
| **`DUPLICATE_CLAIM`** | 240 | 3.99% | $0.00 | $189,343.57 | $189,343.57 | `HIGH` |
| **`AMOUNT_VARIANCE`** | 539 | 8.97% | $468,370.55 | $526,375.03 | $58,004.48 | `MEDIUM` |
| **`UNMATCHED_BILL`** | 40 | 0.67% | $0.00 | $36,700.33 | $36,700.33 | `HIGH` |
| **`CLEAN_MATCH`** | 4,567 | 75.99% | $3,452,058.27 | $3,452,058.27 | $0.00 | `LOW` |
| **`TIMING_SKEW`** | 384 | 6.39% | $356,426.91 | $356,426.91 | $0.00 | `MEDIUM` |

## 3. Investigation Triage Guidance

### UNBILLED_SERVICE (240 records — 3.99%)
- **Risk Tier:** `HIGH`
- **Financial Impact:** Net Variance of `$-224,443.42`
- **Recommended Audit Guidance:** Clinical service completed but no claim filed; potential revenue leakage.

### DUPLICATE_CLAIM (240 records — 3.99%)
- **Risk Tier:** `HIGH`
- **Financial Impact:** Net Variance of `$189,343.57`
- **Recommended Audit Guidance:** Multiple claims submitted for identical service; voiding recommended.

### AMOUNT_VARIANCE (539 records — 8.97%)
- **Risk Tier:** `MEDIUM`
- **Financial Impact:** Net Variance of `$58,004.48`
- **Recommended Audit Guidance:** Billed amount deviates from clinical encounter total cost.

### UNMATCHED_BILL (40 records — 0.67%)
- **Risk Tier:** `HIGH`
- **Financial Impact:** Net Variance of `$36,700.33`
- **Recommended Audit Guidance:** Billed claim exists with no clinical encounter in EHR; audit documentation.

### TIMING_SKEW (384 records — 6.39%)
- **Risk Tier:** `MEDIUM`
- **Financial Impact:** Net Variance of `$0.00`
- **Recommended Audit Guidance:** Submission date occurs prematurely or exceeds 120-day limit.

