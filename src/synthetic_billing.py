"""
MedDataIQ — Synthetic Billing Claims Generator
Implements Phase 1 requirement 4:
"If billing details are unavailable, propose clearly labeled synthetic billing records linked to suitable healthcare encounters."

Generates `data/raw/billing_claims.csv` with realistic healthcare claim lifecycles,
contractual allowances, adjudication statuses, and controlled discrepancy categories for audit testing:
- CLEAN_MATCH (Baseline high-fidelity parity)
- AMOUNT_DISCREPANCY (Billed amount deviates from clinical encounter cost)
- TIMING_SKEW (Submission date precedes service date or exceeds 120-day filing limits)
- DUPLICATE_CLAIM (Duplicate claim submitted for same service)
- UNMATCHED_BILL (Claim filed without matching clinical encounter)
- Note: Unbilled clinical encounters occur when valid encounters are omitted from billing.
"""

import csv
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from src.config import RAW_DATA_DIR, setup_logging

logger = setup_logging("BillingGenerator")
random.seed(101)


def generate_billing_claims(raw_dir: Path = RAW_DATA_DIR) -> int:
    """
    Reads encounters.csv and generates a realistic billing_claims.csv file.
    """
    encounters_file = raw_dir / "encounters.csv"
    if not encounters_file.exists():
        raise FileNotFoundError(f"Missing {encounters_file}. Run ingest.py first.")

    encounters = []
    with open(encounters_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            encounters.append(row)

    logger.info(f"Loaded {len(encounters)} encounters to generate billing claims...")

    claims_rows = []
    claim_counter = 100000

    # 1. Process encounters (with controlled reconciliation distributions)
    # ~4% of encounters will be intentionally UNBILLED (revenue leakage audit)
    for enc in encounters:
        # Check if we should omit claim (Unbilled Service)
        if random.random() < 0.04:
            continue  # Encounter has no bill

        claim_counter += 1
        claim_id = str(uuid.uuid4())
        claim_num = f"CLM-2026-{claim_counter}"

        start_dt = datetime.strptime(enc["START"], "%Y-%m-%dT%H:%M:%SZ")
        enc_cost = float(enc["TOTAL_CLAIM_COST"])
        payer_cov = float(enc["PAYER_COVERAGE"])

        # Decide discrepancy scenario
        roll = random.random()

        if roll < 0.76:
            # CLEAN_MATCH: Standard claim lifecycle
            audit_cat = "CLEAN_MATCH"
            billed_amount = enc_cost
            allowed_amount = round(billed_amount * 0.90, 2)
            paid_amount = round(allowed_amount * 0.85, 2)
            patient_resp = round(allowed_amount - paid_amount, 2)
            submission_dt = start_dt + timedelta(days=random.randint(1, 14))
            status = "PAID"

        elif roll < 0.86:
            # AMOUNT_DISCREPANCY: Claim billed differs from clinical cost
            audit_cat = "AMOUNT_DISCREPANCY"
            # Either underbilled or overbilled
            multiplier = random.choice([0.60, 0.75, 1.35, 1.60])
            billed_amount = round(enc_cost * multiplier, 2)
            allowed_amount = round(billed_amount * 0.85, 2)
            paid_amount = round(allowed_amount * 0.80, 2)
            patient_resp = round(allowed_amount - paid_amount, 2)
            submission_dt = start_dt + timedelta(days=random.randint(2, 21))
            status = random.choice(["PAID", "PENDING_REVIEW", "APPEALED"])

        elif roll < 0.93:
            # TIMING_SKEW: Submission date anomalies
            audit_cat = "TIMING_SKEW"
            billed_amount = enc_cost
            allowed_amount = round(billed_amount * 0.80, 2)
            paid_amount = round(allowed_amount * 0.70, 2)
            patient_resp = round(allowed_amount - paid_amount, 2)
            # Either before service or > 120 days after
            if random.random() < 0.35:
                submission_dt = start_dt - timedelta(days=random.randint(1, 10))  # illogical early date
                status = "DENIED"
            else:
                submission_dt = start_dt + timedelta(days=random.randint(125, 200))  # late filing
                status = "DENIED"

        else:
            # Standard claim that will be DUPLICATED below
            audit_cat = "CLEAN_MATCH"
            billed_amount = enc_cost
            allowed_amount = round(billed_amount * 0.90, 2)
            paid_amount = round(allowed_amount * 0.85, 2)
            patient_resp = round(allowed_amount - paid_amount, 2)
            submission_dt = start_dt + timedelta(days=random.randint(2, 14))
            status = "PAID"

        claim_record = {
            "claim_id": claim_id,
            "claim_number": claim_num,
            "encounter_id": enc["Id"],
            "patient_id": enc["PATIENT"],
            "provider_id": enc["PROVIDER"],
            "payer_id": enc["PAYER"],
            "service_date": start_dt.strftime("%Y-%m-%d"),
            "claim_submission_date": submission_dt.strftime("%Y-%m-%d"),
            "billed_amount": billed_amount,
            "allowed_amount": allowed_amount,
            "paid_amount": paid_amount,
            "patient_responsibility": patient_resp,
            "claim_status": status,
            "audit_category": audit_cat
        }
        claims_rows.append(claim_record)

        # Inject controlled DUPLICATE_CLAIM (2% frequency)
        if roll >= 0.93 and random.random() < 0.60:
            claim_counter += 1
            dup_record = dict(claim_record)
            dup_record["claim_id"] = str(uuid.uuid4())
            dup_record["claim_number"] = f"CLM-2026-{claim_counter}-DUP"
            dup_record["audit_category"] = "DUPLICATE_CLAIM"
            dup_record["claim_status"] = "PENDING_REVIEW"
            claims_rows.append(dup_record)

    # 2. Inject controlled UNMATCHED_BILL (Ghost bills without clinical encounter)
    # Generate ~20-30 orphan claims referencing real patients/providers but non-existent encounter UUIDs
    sample_enc = random.sample(encounters, min(40, len(encounters)))
    for ref_enc in sample_enc:
        claim_counter += 1
        s_dt = datetime.strptime(ref_enc["START"], "%Y-%m-%dT%H:%M:%SZ")
        claims_rows.append({
            "claim_id": str(uuid.uuid4()),
            "claim_number": f"CLM-2026-{claim_counter}-UNMATCHED",
            "encounter_id": str(uuid.uuid4()),  # Non-existent encounter ID
            "patient_id": ref_enc["PATIENT"],
            "provider_id": ref_enc["PROVIDER"],
            "payer_id": ref_enc["PAYER"],
            "service_date": s_dt.strftime("%Y-%m-%d"),
            "claim_submission_date": (s_dt + timedelta(days=5)).strftime("%Y-%m-%d"),
            "billed_amount": round(random.uniform(250, 1500), 2),
            "allowed_amount": 0.0,
            "paid_amount": 0.0,
            "patient_responsibility": 0.0,
            "claim_status": "DENIED",
            "audit_category": "UNMATCHED_BILL"
        })

    # Write output to billing_claims.csv
    out_file = raw_dir / "billing_claims.csv"
    with open(out_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(claims_rows[0].keys()))
        writer.writeheader()
        writer.writerows(claims_rows)

    logger.info(f"Successfully generated {len(claims_rows)} billing claims in {out_file}")
    return len(claims_rows)


if __name__ == "__main__":
    generate_billing_claims()
