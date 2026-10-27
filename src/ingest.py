"""
MedDataIQ — Dataset Ingestion & Generation Module
Generates an authentic cohort adhering strictly to the Synthea specification:
- patients.csv
- encounters.csv
- procedures.csv
- medications.csv
- organizations.csv
- providers.csv
- payers.csv
"""

import csv
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from src.config import RAW_DATA_DIR, setup_logging

logger = setup_logging("IngestModule")

# Fix random seed for reproducibility
random.seed(42)

# Reference Clinical & Geographic Dictionaries
CITIES_MA = [
    ("Boston", "02101", 42.3601, -71.0589),
    ("Cambridge", "02138", 42.3736, -71.1097),
    ("Worcester", "01608", 42.2626, -71.8023),
    ("Springfield", "01103", 42.1015, -72.5898),
    ("Lowell", "01852", 42.6334, -71.3162),
    ("Quincy", "02169", 42.2529, -71.0023),
    ("Brockton", "02301", 42.0834, -71.0184),
    ("Lynn", "01901", 42.4668, -70.9495),
    ("Newton", "02458", 42.3370, -71.2092),
    ("Somerville", "02143", 42.3876, -71.0995),
]

FIRST_NAMES_M = ["James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles", "Daniel", "Matthew", "Anthony", "Donald", "Mark"]
FIRST_NAMES_F = ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Lisa", "Betty", "Margaret", "Sandra"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson"]
RACES = ["white", "black", "asian", "native", "other"]
RACE_WEIGHTS = [0.68, 0.14, 0.08, 0.01, 0.09]
ETHNICITIES = ["nonhispanic", "hispanic"]
ETHNICITY_WEIGHTS = [0.85, 0.15]

ORGANIZATIONS_DATA = [
    ("Massachusetts General Hospital", "55 Fruit St", "Boston", "02114", 42.3628, -71.0691, "617-726-2000", 250000000, 92),
    ("Beth Israel Deaconess Medical Center", "330 Brookline Ave", "Boston", "02215", 42.3394, -71.1066, "617-667-7000", 180000000, 88),
    ("Boston Medical Center", "1 Boston Medical Ctr Pl", "Boston", "02118", 42.3353, -71.0728, "617-638-8000", 140000000, 85),
    ("UMass Memorial Medical Center", "55 Lake Ave N", "Worcester", "01655", 42.2743, -71.7617, "508-334-1000", 120000000, 80),
    ("Baystate Medical Center", "759 Chestnut St", "Springfield", "01199", 42.1245, -72.6041, "413-794-0000", 110000000, 78),
    ("Cambridge Health Alliance", "1493 Cambridge St", "Cambridge", "02139", 42.3748, -71.1039, "617-665-1000", 85000000, 75),
]

PAYERS_DATA = [
    ("Medicare", "7500 Security Blvd", "Baltimore", "MD", "21244", "800-633-4227"),
    ("Medicaid MA (MassHealth)", "100 Hancock St", "Quincy", "MA", "02171", "800-841-2900"),
    ("Blue Cross Blue Shield of Massachusetts", "101 Huntington Ave", "Boston", "MA", "02199", "800-262-2583"),
    ("Harvard Pilgrim Health Care", "93 Worcester St", "Wellesley", "MA", "02481", "888-333-4742"),
    ("Tufts Health Plan", "705 Mt Auburn St", "Watertown", "MA", "02472", "800-462-0224"),
    ("UnitedHealthcare", "9900 Bren Rd E", "Minnetonka", "MN", "55343", "800-842-8000"),
    ("NO_INSURANCE", "100 Self Pay Way", "Boston", "MA", "02101", "000-000-0000"),
]

SPECIALTIES = ["General Practice", "Internal Medicine", "Emergency Medicine", "Cardiology", "Pediatrics", "Family Medicine"]

ENCOUNTER_TYPES = [
    ("wellness", "424619002", "Annual wellness visit", (40, 120), (120, 250), 0.95),
    ("ambulatory", "185349003", "Encounter for checkup / symptom evaluation", (20, 60), (100, 350), 0.85),
    ("outpatient", "406547006", "Outpatient specialist consultation", (30, 90), (180, 500), 0.80),
    ("urgentcare", "448337001", "Urgent care clinic visit", (30, 90), (150, 450), 0.80),
    ("emergency", "50849002", "Emergency room admission", (120, 480), (800, 3500), 0.75),
    ("inpatient", "32485007", "Hospital admission / Inpatient stay", (1440, 5760), (3500, 18000), 0.70),
]

CLINICAL_REASONS = [
    ("44054006", "Type 2 diabetes mellitus"),
    ("38341003", "Essential hypertension"),
    ("195662009", "Acute bronchitis"),
    ("233604007", "Pneumonia"),
    ("65363002", "Otitis media"),
    ("162864005", "Chest pain"),
    ("10509002", "Acute bronchitis"),
    ("444814009", "Viral sinusitis"),
    ("73211009", "Diabetes mellitus"),
    ("15777000", "Prediabetes"),
]

PROCEDURES_POOL = [
    ("703423002", "Colonoscopy", (600, 1800)),
    ("430193006", "Medication reconciliation", (50, 150)),
    ("274025005", "Colorectal cancer screening", (400, 1200)),
    ("173160006", "Diagnostic ultrasound of abdomen", (300, 850)),
    ("413782006", "Blood pressure screening", (25, 75)),
    ("710830005", "Assessment of health status", (50, 120)),
    ("5880005", "Physical examination", (75, 180)),
    ("268556000", "Urine screening test", (35, 95)),
    ("36708009", "Electrocardiogram, 12-lead", (120, 380)),
    ("399208008", "Chest X-ray", (150, 450)),
]

MEDICATIONS_POOL = [
    ("860975", "Metformin hydrochloride 500 MG Oral Tablet", (15, 45)),
    ("197361", "Amlodipine 5 MG Oral Tablet", (12, 35)),
    ("310965", "Hydrochlorothiazide 25 MG Oral Tablet", (10, 30)),
    ("311884", "Lisinopril 10 MG Oral Tablet", (14, 40)),
    ("855332", "Amoxicillin 500 MG Oral Tablet", (18, 55)),
    ("617314", "Atorvastatin 20 MG Oral Tablet", (25, 80)),
    ("197591", "Levothyroxine sodium 0.05 MG Oral Tablet", (15, 50)),
    ("2123111", "Albuterol 0.09 MG/ACTUAT Inhalant Solution", (35, 95)),
]


def generate_synthea_dataset(num_patients: int = 1000, target_dir: Path = RAW_DATA_DIR):
    """
    Generates realistic, schema-compliant Synthea CSV files in target_dir.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Generating Synthea cohort of {num_patients} patients at {target_dir}...")

    # 1. Payers
    payers = []
    payer_rows = []
    for p in PAYERS_DATA:
        p_id = str(uuid.uuid4())
        payers.append(p_id)
        payer_rows.append({
            "Id": p_id,
            "NAME": p[0],
            "ADDRESS": p[1],
            "CITY": p[2],
            "STATE_HEADQUARTERS": p[3],
            "ZIP": p[4],
            "PHONE": p[5]
        })

    with open(target_dir / "payers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(payer_rows[0].keys()))
        writer.writeheader()
        writer.writerows(payer_rows)
    logger.info(f"Generated payers.csv ({len(payer_rows)} records)")

    # 2. Organizations
    orgs = []
    org_rows = []
    for org in ORGANIZATIONS_DATA:
        o_id = str(uuid.uuid4())
        orgs.append(o_id)
        org_rows.append({
            "Id": o_id,
            "NAME": org[0],
            "ADDRESS": org[1],
            "CITY": org[2],
            "STATE": "MA",
            "ZIP": org[3],
            "LAT": org[4],
            "LON": org[5],
            "PHONE": org[6],
            "REVENUE": org[7],
            "UTILIZATION": org[8]
        })

    with open(target_dir / "organizations.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(org_rows[0].keys()))
        writer.writeheader()
        writer.writerows(org_rows)
    logger.info(f"Generated organizations.csv ({len(org_rows)} records)")

    # 3. Providers
    providers = []
    provider_rows = []
    for i in range(len(ORGANIZATIONS_DATA) * 5):
        pr_id = str(uuid.uuid4())
        providers.append(pr_id)
        assigned_org = random.choice(org_rows)
        gender = random.choice(["M", "F"])
        fname = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        lname = random.choice(LAST_NAMES)
        provider_rows.append({
            "Id": pr_id,
            "ORGANIZATION": assigned_org["Id"],
            "NAME": f"Dr. {fname} {lname}",
            "GENDER": gender,
            "SPECIALITY": random.choice(SPECIALTIES),
            "ADDRESS": assigned_org["ADDRESS"],
            "CITY": assigned_org["CITY"],
            "STATE": assigned_org["STATE"],
            "ZIP": assigned_org["ZIP"],
            "LAT": assigned_org["LAT"],
            "LON": assigned_org["LON"]
        })

    with open(target_dir / "providers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(provider_rows[0].keys()))
        writer.writeheader()
        writer.writerows(provider_rows)
    logger.info(f"Generated providers.csv ({len(provider_rows)} records)")

    # 4. Patients
    patients = []
    patient_rows = []
    now = datetime(2026, 10, 1)

    for i in range(num_patients):
        p_id = str(uuid.uuid4())
        patients.append(p_id)

        gender = random.choice(["M", "F"])
        fname = random.choice(FIRST_NAMES_M if gender == "M" else FIRST_NAMES_F)
        lname = random.choice(LAST_NAMES)
        prefix = "Mr." if gender == "M" else ("Ms." if random.random() < 0.6 else "Mrs.")

        # Age distribution: 0 to 88 years
        age_years = int(random.triangular(5, 88, 48))
        birth_dt = now - timedelta(days=age_years * 365 + random.randint(0, 360))
        birthdate = birth_dt.strftime("%Y-%m-%d")

        # Mortality rate for elderly
        deathdate = ""
        if age_years > 65 and random.random() < 0.12:
            death_dt = birth_dt + timedelta(days=random.randint(65 * 365, age_years * 365))
            if death_dt < now:
                deathdate = death_dt.strftime("%Y-%m-%d")

        city, zcode, lat, lon = random.choice(CITIES_MA)
        race = random.choices(RACES, weights=RACE_WEIGHTS)[0]
        ethnicity = random.choices(ETHNICITIES, weights=ETHNICITY_WEIGHTS)[0]

        # Financial accumulators
        patient_rows.append({
            "Id": p_id,
            "BIRTHDATE": birthdate,
            "DEATHDATE": deathdate,
            "SSN": f"{random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}",
            "DRIVERS": f"S{random.randint(10000000, 99999999)}",
            "PASSPORT": f"X{random.randint(10000000, 99999999)}",
            "PREFIX": prefix,
            "FIRST": fname,
            "LAST": lname,
            "SUFFIX": "",
            "MAIDEN": random.choice(LAST_NAMES) if gender == "F" and random.random() < 0.4 else "",
            "MARITAL": random.choice(["M", "S", "D", "W"]),
            "RACE": race,
            "ETHNICITY": ethnicity,
            "GENDER": gender,
            "BIRTHPLACE": f"{city}, Massachusetts, US",
            "ADDRESS": f"{random.randint(10, 999)} Main Street",
            "CITY": city,
            "STATE": "Massachusetts",
            "COUNTY": "Middlesex County" if city in ["Cambridge", "Lowell", "Newton", "Somerville"] else "Suffolk County",
            "ZIP": zcode,
            "LAT": round(lat + random.uniform(-0.02, 0.02), 4),
            "LON": round(lon + random.uniform(-0.02, 0.02), 4),
            "HEALTHCARE_EXPENSES": 0.0,  # to be updated
            "HEALTHCARE_COVERAGE": 0.0,  # to be updated
            "INCOME": random.randint(22000, 160000)
        })

    # 5. Encounters, Procedures, and Medications
    encounters_rows = []
    procedures_rows = []
    medications_rows = []

    patient_expenses = {p["Id"]: 0.0 for p in patient_rows}
    patient_coverage = {p["Id"]: 0.0 for p in patient_rows}

    # Generate timeline of visits between 2023-01-01 and 2026-09-30
    start_timeline = datetime(2023, 1, 1)

    for p in patient_rows:
        p_id = p["Id"]
        p_birth = datetime.strptime(p["BIRTHDATE"], "%Y-%m-%d")
        p_death = datetime.strptime(p["DEATHDATE"], "%Y-%m-%d") if p["DEATHDATE"] else now

        # Number of encounters based on age
        base_visits = random.randint(2, 6)
        if (now - p_birth).days > 55 * 365:
            base_visits = random.randint(5, 14)

        for _ in range(base_visits):
            # Random date between birth, timeline start, and death
            earliest_dt = max(start_timeline, p_birth)
            if earliest_dt >= p_death:
                continue
            delta_days = (p_death - earliest_dt).days
            if delta_days <= 0:
                continue
            enc_start = earliest_dt + timedelta(days=random.randint(0, delta_days), hours=random.randint(8, 17), minutes=random.randint(0, 59))

            # Pick encounter category
            enc_class_info = random.choices(
                ENCOUNTER_TYPES,
                weights=[0.30, 0.35, 0.15, 0.10, 0.07, 0.03]
            )[0]
            enc_class, enc_code, enc_desc, dur_range, cost_range, cov_rate = enc_class_info

            duration_min = random.randint(*dur_range)
            enc_stop = enc_start + timedelta(minutes=duration_min)

            enc_id = str(uuid.uuid4())
            assigned_provider = random.choice(provider_rows)
            assigned_org = assigned_provider["ORGANIZATION"]
            assigned_payer = random.choice(payers)

            base_cost = round(random.uniform(*cost_range), 2)
            total_claim = round(base_cost * random.uniform(1.05, 1.25), 2)
            payer_cov = round(total_claim * cov_rate, 2)
            out_of_pocket = round(total_claim - payer_cov, 2)

            reason_code, reason_desc = random.choice(CLINICAL_REASONS)

            encounters_rows.append({
                "Id": enc_id,
                "START": enc_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "STOP": enc_stop.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "PATIENT": p_id,
                "ORGANIZATION": assigned_org,
                "PROVIDER": assigned_provider["Id"],
                "PAYER": assigned_payer,
                "ENCOUNTERCLASS": enc_class,
                "CODE": enc_code,
                "DESCRIPTION": enc_desc,
                "BASE_ENCOUNTER_COST": base_cost,
                "TOTAL_CLAIM_COST": total_claim,
                "PAYER_COVERAGE": payer_cov,
                "REASONCODE": reason_code,
                "REASONDESCRIPTION": reason_desc
            })

            patient_expenses[p_id] += out_of_pocket
            patient_coverage[p_id] += payer_cov

            # Procedures for this encounter (50% probability)
            if random.random() < 0.55:
                proc_code, proc_desc, proc_cost_range = random.choice(PROCEDURES_POOL)
                p_cost = round(random.uniform(*proc_cost_range), 2)
                procedures_rows.append({
                    "START": enc_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "STOP": (enc_start + timedelta(minutes=random.randint(15, 60))).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "PATIENT": p_id,
                    "ENCOUNTER": enc_id,
                    "CODE": proc_code,
                    "DESCRIPTION": proc_desc,
                    "BASE_COST": p_cost,
                    "REASONCODE": reason_code,
                    "REASONDESCRIPTION": reason_desc
                })

            # Medications for this encounter (40% probability)
            if random.random() < 0.45:
                med_code, med_desc, med_cost_range = random.choice(MEDICATIONS_POOL)
                m_base = round(random.uniform(*med_cost_range), 2)
                dispenses = random.randint(1, 4)
                m_total = round(m_base * dispenses, 2)
                m_cov = round(m_total * 0.80, 2)

                medications_rows.append({
                    "START": enc_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "STOP": (enc_start + timedelta(days=30 * dispenses)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "PATIENT": p_id,
                    "PAYER": assigned_payer,
                    "ENCOUNTER": enc_id,
                    "CODE": med_code,
                    "DESCRIPTION": med_desc,
                    "BASE_COST": m_base,
                    "PAYER_COVERAGE": m_cov,
                    "DISPENSES": dispenses,
                    "TOTAL_COST": m_total,
                    "REASONCODE": reason_code,
                    "REASONDESCRIPTION": reason_desc
                })

    # Update patient lifetime totals
    for p in patient_rows:
        p["HEALTHCARE_EXPENSES"] = round(patient_expenses[p["Id"]], 2)
        p["HEALTHCARE_COVERAGE"] = round(patient_coverage[p["Id"]], 2)

    # Write patients.csv
    with open(target_dir / "patients.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(patient_rows[0].keys()))
        writer.writeheader()
        writer.writerows(patient_rows)
    logger.info(f"Generated patients.csv ({len(patient_rows)} records)")

    # Write encounters.csv
    with open(target_dir / "encounters.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(encounters_rows[0].keys()))
        writer.writeheader()
        writer.writerows(encounters_rows)
    logger.info(f"Generated encounters.csv ({len(encounters_rows)} records)")

    # Write procedures.csv
    with open(target_dir / "procedures.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(procedures_rows[0].keys()))
        writer.writeheader()
        writer.writerows(procedures_rows)
    logger.info(f"Generated procedures.csv ({len(procedures_rows)} records)")

    # Write medications.csv
    with open(target_dir / "medications.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(medications_rows[0].keys()))
        writer.writeheader()
        writer.writerows(medications_rows)
    logger.info(f"Generated medications.csv ({len(medications_rows)} records)")

    logger.info("Synthea dataset generation completed successfully!")
    return {
        "patients": len(patient_rows),
        "encounters": len(encounters_rows),
        "procedures": len(procedures_rows),
        "medications": len(medications_rows),
        "organizations": len(org_rows),
        "providers": len(provider_rows),
        "payers": len(payer_rows)
    }

if __name__ == "__main__":
    generate_synthea_dataset()
