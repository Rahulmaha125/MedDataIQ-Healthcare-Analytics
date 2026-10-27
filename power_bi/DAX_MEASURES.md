# MedDataIQ — Production DAX Measure Library

This document provides the complete, production-grade DAX (Data Analysis Expressions) library for the **MedDataIQ Healthcare Intelligence & Revenue Integrity** Power BI model.

All measures are designed to be housed in a dedicated **`_Measures`** table to maintain clean separation between raw data columns and analytical business logic.

---

## Architecture & Measure Design Rules

1. **Explicit Measures Only**: Never rely on implicit Power BI summarizations. All metrics use explicit DAX aggregation functions (`SUM`, `COUNTROWS`, `DISTINCTCOUNT`, `DIVIDE`, `CALCULATE`).
2. **Safe Division**: All ratios and percentages utilize `DIVIDE(numerator, denominator, 0)` to gracefully prevent division-by-zero errors (`NaN` / `Infinity`).
3. **Double-Counting Safeguard**: In `Fact_Reconciliation`, the `clinical_encounter_cost` field has already had secondary duplicate claims set to `$0.00` via SQL window partitioning (`claim_seq = 1`). Summing `Fact_Reconciliation[clinical_encounter_cost]` reconciles **exactly** to `Fact_Encounter[total_claim_cost]` ($4,501,299.15).
4. **Audit vs. Operations Separation**: Discrepancies and unbilled services are tracked as revenue integrity investigation flags, distinct from routine operational variances.

---

## Folder 01: Core Volume Measures

### `[Total Patients]`
Counts the total distinct population of active patients registered in the clinical repository.
```dax
Total Patients = 
DISTINCTCOUNT(Dim_Patient[patient_id])
```

### `[Total Encounters]`
Total clinical encounter events recorded across ambulatory, inpatient, emergency, urgent care, and wellness visits.
```dax
Total Encounters = 
COUNTROWS(Fact_Encounter)
```

### `[Total Billing Claims]`
Total professional and institutional billing claims processed by the revenue cycle management system.
```dax
Total Billing Claims = 
COUNTROWS(Fact_Billing)
```

### `[Total Reconciled Records]`
The comprehensive outer-joined audit universe combining clinical encounters, matched claims, secondary duplicates, unbilled clinical encounters, and orphan unmatched billing claims.
```dax
Total Reconciled Records = 
COUNTROWS(Fact_Reconciliation)
```

### `[Active Providers]`
Count of healthcare practitioners actively delivering clinical care in the encounter dataset.
```dax
Active Providers = 
DISTINCTCOUNT(Fact_Encounter[provider_id])
```

---

## Folder 02: Financial Baselines & Parity Measures

### `[Total Clinical Cost]`
Sum of total clinical encounter costs directly from the operational encounter ledger.
```dax
Total Clinical Cost = 
SUM(Fact_Encounter[total_claim_cost])
```
*Format: `$#,##0.00` | Baseline: `$4,501,299.15`*

### `[Total Billed Amount]`
Gross charges submitted to payers on billing claims.
```dax
Total Billed Amount = 
SUM(Fact_Billing[billed_amount])
```
*Format: `$#,##0.00` | Baseline: `$4,560,904.11`*

### `[Total Paid Amount]`
Actual cash collections and reimbursements adjudicated by payers.
```dax
Total Paid Amount = 
SUM(Fact_Billing[paid_amount])
```
*Format: `$#,##0.00` | Baseline: `$3,277,329.80`*

### `[Recon Clinical Encounter Cost]`
Total clinical cost calculated within the unified reconciliation audit fact table. Guaranteed to match `[Total Clinical Cost]` exactly without double-counting.
```dax
Recon Clinical Encounter Cost = 
SUM(Fact_Reconciliation[clinical_encounter_cost])
```
*Format: `$#,##0.00` | Baseline: `$4,501,299.15`*

### `[Recon Claim Billed Amount]`
Total billed charges calculated within the unified reconciliation audit fact table. Guaranteed to match `[Total Billed Amount]` exactly.
```dax
Recon Claim Billed Amount = 
SUM(Fact_Reconciliation[claim_billed_amount])
```
*Format: `$#,##0.00` | Baseline: `$4,560,904.11`*

### `[Net Financial Variance]`
The absolute dollar variance between total billed charges and total clinical costs across the entire healthcare system.
```dax
Net Financial Variance = 
[Recon Claim Billed Amount] - [Recon Clinical Encounter Cost]
```
*Format: `$#,##0.00` | Baseline: `+$59,604.96`*

### `[Variance Percentage]`
The relative net variance percentage evaluated against clinical baseline cost.
```dax
Variance Percentage = 
DIVIDE([Net Financial Variance], [Recon Clinical Encounter Cost], 0)
```
*Format: `+0.00%;-0.00%;0.00%` | Baseline: `+1.32%`*

---

## Folder 03: Revenue Integrity & Reconciliation Audit

### `[Clean Reconciliation Count]`
Total clinical encounters perfectly matched 1:1 with corresponding billing claims without financial or timing anomalies.
```dax
Clean Reconciliation Count = 
CALCULATE(
    COUNTROWS(Fact_Reconciliation),
    Fact_Reconciliation[reconciliation_status] = "CLEAN_MATCH"
)
```
*Baseline: 4,567 rows*

### `[Clean Reconciliation Cost]`
Total clinical cost associated with clean 1:1 matched encounters.
```dax
Clean Reconciliation Cost = 
CALCULATE(
    SUM(Fact_Reconciliation[clinical_encounter_cost]),
    Fact_Reconciliation[reconciliation_status] = "CLEAN_MATCH"
)
```
*Format: `$#,##0.00` | Baseline: `$3,452,058.27`*

### `[Amount Variance Count]`
Count of encounters where a single claim was submitted, but the billed charge differed from the documented clinical service cost.
```dax
Amount Variance Count = 
CALCULATE(
    COUNTROWS(Fact_Reconciliation),
    Fact_Reconciliation[reconciliation_status] = "AMOUNT_VARIANCE"
)
```
*Baseline: 539 rows*

### `[Amount Variance Net Exposure]`
Net dollar variance from single-claim billing discrepancies (under-billing or over-billing).
```dax
Amount Variance Net Exposure = 
CALCULATE(
    SUM(Fact_Reconciliation[variance_amount]),
    Fact_Reconciliation[reconciliation_status] = "AMOUNT_VARIANCE"
)
```
*Format: `$#,##0.00` | Baseline: `+$58,004.48`*

### `[Duplicate Claim Count]`
Count of redundant billing claims submitted for an encounter that already possessed a valid primary claim.
```dax
Duplicate Claim Count = 
CALCULATE(
    COUNTROWS(Fact_Reconciliation),
    Fact_Reconciliation[reconciliation_status] = "DUPLICATE_CLAIM"
)
```
*Baseline: 240 rows*

### `[Duplicate Claim Exposure]`
Total financial risk representing redundant charges submitted to payers. Because the primary claim covered the encounter, the clinical cost for these duplicate records is attributed as `$0.00`, meaning 100% of the billed charge is gross over-billing risk.
```dax
Duplicate Claim Exposure = 
CALCULATE(
    SUM(Fact_Reconciliation[claim_billed_amount]),
    Fact_Reconciliation[reconciliation_status] = "DUPLICATE_CLAIM"
)
```
*Format: `$#,##0.00` | Baseline: `$189,343.57`*

> **Critical Audit Commentary**:
> `[Duplicate Claim Exposure]` is tracked separately from operational variance because duplicate submissions represent a systemic compliance, billing scrubber, or clearinghouse issue. Grouping them with clinical amount variances would distort genuine provider pricing differences.

### `[Unbilled Service Count]`
Clinical encounters documented in the EHR with positive clinical cost for which **no billing claim was ever submitted** (revenue leakage).
```dax
Unbilled Service Count = 
CALCULATE(
    COUNTROWS(Fact_Reconciliation),
    Fact_Reconciliation[reconciliation_status] = "UNBILLED_SERVICE"
)
```
*Baseline: 240 rows*

### `[Unbilled Clinical Cost]`
Total uncaptured clinical revenue leakage resulting from unbilled encounters.
```dax
Unbilled Clinical Cost = 
CALCULATE(
    SUM(Fact_Reconciliation[clinical_encounter_cost]),
    Fact_Reconciliation[reconciliation_status] = "UNBILLED_SERVICE"
)
```
*Format: `$#,##0.00` | Baseline: `$224,443.42`*

### `[Unmatched Bill Count]`
Billing claims submitted into the clearinghouse that have **no matching clinical encounter record in the EHR** (potential ghost claims, unlinked pre-authorizations, or cross-system synchronization lag).
```dax
Unmatched Bill Count = 
CALCULATE(
    COUNTROWS(Fact_Reconciliation),
    Fact_Reconciliation[reconciliation_status] = "UNMATCHED_BILL"
)
```
*Baseline: 40 rows*

### `[Unmatched Billed Amount]`
Total gross charges on claims lacking supporting clinical encounter documentation.
```dax
Unmatched Billed Amount = 
CALCULATE(
    SUM(Fact_Reconciliation[claim_billed_amount]),
    Fact_Reconciliation[reconciliation_status] = "UNMATCHED_BILL"
)
```
*Format: `$#,##0.00` | Baseline: `$36,700.33`*

### `[Timing Skew Count]`
Encounters matched to claims where the submission date fell outside acceptable revenue cycle lag thresholds (> 30 days after clinical discharge).
```dax
Timing Skew Count = 
CALCULATE(
    COUNTROWS(Fact_Reconciliation),
    Fact_Reconciliation[reconciliation_status] = "TIMING_SKEW"
)
```
*Baseline: 384 rows*

### `[Timing Skew Exposure]`
Total dollar variance on encounters experiencing severe billing submission lag.
```dax
Timing Skew Exposure = 
CALCULATE(
    SUM(Fact_Reconciliation[variance_amount]),
    Fact_Reconciliation[reconciliation_status] = "TIMING_SKEW"
)
```
*Format: `$#,##0.00` | Baseline: `+$0.00` (Costs matched, but timing was skewed)*

---

## Folder 04: Key Performance Indicators & Rates

### `[Clean Reconciliation Rate]`
Proportion of the audit universe that passed reconciliation with zero errors.
```dax
Clean Reconciliation Rate = 
DIVIDE([Clean Reconciliation Count], [Total Reconciled Records], 0)
```
*Format: `0.0%` | Baseline: `76.0%` (4,567 / 6,010)*

### `[Discrepancy Rate]`
Proportion of records requiring clinical or revenue cycle investigation.
```dax
Discrepancy Rate = 
1 - [Clean Reconciliation Rate]
```
*Format: `0.0%` | Baseline: `24.0%` (1,443 / 6,010)*

### `[Duplicate Claim Rate]`
Percentage of submitted claims flagged as duplicate submissions.
```dax
Duplicate Claim Rate = 
DIVIDE([Duplicate Claim Count], [Total Billing Claims], 0)
```
*Format: `0.00%` | Baseline: `4.16%` (240 / 5,770)*

### `[Unbilled Encounter Rate]`
Percentage of completed clinical encounters lacking billing submission.
```dax
Unbilled Encounter Rate = 
DIVIDE([Unbilled Service Count], [Total Encounters], 0)
```
*Format: `0.00%` | Baseline: `4.19%` (240 / 5,730)*

### `[Collection Rate]`
Percentage of submitted charges actually collected from payers and patients.
```dax
Collection Rate = 
DIVIDE([Total Paid Amount], [Total Billed Amount], 0)
```
*Format: `0.0%` | Baseline: `71.9%` ($3,277,329.80 / $4,560,904.11)*

---

## Folder 05: Data Quality Dimensions & Rules

### `[Data Quality Total Rules]`
Total active data quality rules evaluated across the 6 healthcare data quality dimensions.
```dax
Data Quality Total Rules = 
COUNTROWS(Fact_DataQuality)
```
*Baseline: 43 rules*

### `[Data Quality Passed Rules]`
Rules meeting complete acceptance criteria without threshold violations.
```dax
Data Quality Passed Rules = 
CALCULATE(
    COUNTROWS(Fact_DataQuality),
    Fact_DataQuality[status] = "PASS"
)
```
*Baseline: 39 rules*

### `[Data Quality Flagged Rules]`
Rules flagging anomalies for data governance review.
```dax
Data Quality Flagged Rules = 
CALCULATE(
    COUNTROWS(Fact_DataQuality),
    Fact_DataQuality[status] = "FLAGGED"
)
```
*Baseline: 4 rules*

### `[Data Quality Compliance Rate]`
Overall enterprise data health index across Completeness, Uniqueness, Validity, Timeliness, Consistency, and Referential Integrity.
```dax
Data Quality Compliance Rate = 
DIVIDE([Data Quality Passed Rules], [Data Quality Total Rules], 0)
```
*Format: `0.0%` | Baseline: `90.7%` (39 / 43)*

---

## Folder 06: Operational & Provider Averages

### `[Avg Clinical Cost per Encounter]`
Average clinical resource expenditure per encounter.
```dax
Avg Clinical Cost per Encounter = 
DIVIDE([Total Clinical Cost], [Total Encounters], 0)
```
*Format: `$#,##0.00` | Baseline: `$785.57`*

### `[Avg Billed per Claim]`
Average charge submitted per billing claim.
```dax
Avg Billed per Claim = 
DIVIDE([Total Billed Amount], [Total Billing Claims], 0)
```
*Format: `$#,##0.00` | Baseline: `$790.45`*

### `[Encounters per Active Provider]`
Clinical workload distribution per active credentialed provider.
```dax
Encounters per Active Provider = 
DIVIDE([Total Encounters], [Active Providers], 0)
```
*Format: `#,##0.0` | Baseline: `191.0` (5,730 / 30)*

---

## Implementation Instructions: Creating the `_Measures` Table in Power BI

1. On the **Home** tab in Power BI Desktop, click **Enter Data**.
2. Rename the table to `_Measures` and column to `Dummy`. Click **Load**.
3. Select `_Measures` in the Data pane, click **New Measure**, and paste in each DAX formula above.
4. Set the **Format** for each measure in the Measure Tools ribbon (Currency `$`, Percentage `%`, Whole Number).
5. In the Model view, create Display Folders (`01 - Volume`, `02 - Financials`, `03 - Revenue Integrity`, `04 - Integrity KPIs`, `05 - Data Quality`, `06 - Operations`) by setting the **Display folder** property on each measure.
6. Delete the initial `Dummy` column. The `_Measures` table will automatically rise to the top of your Data pane with a calculator icon.
