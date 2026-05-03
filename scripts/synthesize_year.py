"""
Synthesize one full year of realistic hospital admission + medicine data.

Drops the seed CSV (45 real days) into a year-long, event-driven dataset
that respects:
  - Pakistan dengue season (Aug-Nov, peaks ~Oct 15)
  - Ramadan / Eid-ul-Fitr / Eid-ul-Adha / Muharram windows
  - Lahore heat-stroke summer (May-Jul) and monsoon GI surge (Jul-Aug)
  - Lahore smog season Nov-Feb (respiratory cases)
  - Weekly cycles (Friday OPD dip, weekend emergency-only)

Diagnosis -> medicine mappings are derived from the real seed CSV so the
co-prescription pattern stays clinically plausible. Volumes per diagnosis
are then modulated by the seasonal/event signals above.
"""
from __future__ import annotations

import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parent.parent
SEED_CSV = ROOT / "data.csv"
OUT_CSV  = ROOT / "data.csv"

START = date(2025, 5, 1)
END   = date(2026, 4, 30)

RNG_SEED = 7
random.seed(RNG_SEED)
np.random.seed(RNG_SEED)


# ---------------------------------------------------------------------------
# Calendar windows (mirror model.py)
# ---------------------------------------------------------------------------

RAMADAN_WINDOWS = [
    (date(2025, 3, 1),  date(2025, 3, 30)),
    (date(2026, 2, 18), date(2026, 3, 19)),
]
EID_FITR_WINDOWS = [
    (date(2025, 3, 31), date(2025, 4, 2)),
    (date(2026, 3, 20), date(2026, 3, 22)),
]
EID_ADHA_WINDOWS = [
    (date(2025, 6, 7),  date(2025, 6, 9)),
    (date(2026, 5, 27), date(2026, 5, 29)),
]
MUHARRAM_WINDOWS = [
    (date(2025, 7, 5),  date(2025, 7, 6)),
    (date(2026, 6, 25), date(2026, 6, 26)),
]
PUBLIC_HOLIDAYS = {
    date(2025, 8, 14), date(2025, 9, 5), date(2025, 11, 9), date(2025, 12, 25),
    date(2026, 2, 5),  date(2026, 3, 23), date(2026, 5, 1),
}

DENGUE_PEAK_DOY = 288
DENGUE_SIGMA = 28.0


def in_window(d: date, windows) -> bool:
    return any(s <= d <= e for s, e in windows)


def dengue_intensity(d: date) -> float:
    doy = d.timetuple().tm_yday
    diff = min(abs(doy - DENGUE_PEAK_DOY), 365 - abs(doy - DENGUE_PEAK_DOY))
    return float(np.exp(-(diff ** 2) / (2 * DENGUE_SIGMA ** 2)))


def smog_intensity(d: date) -> float:
    """Lahore smog peaks Nov-Dec; near-zero in monsoon."""
    monthly = {1: 0.85, 2: 0.65, 3: 0.35, 4: 0.20, 5: 0.10, 6: 0.05,
               7: 0.05, 8: 0.10, 9: 0.30, 10: 0.65, 11: 1.00, 12: 0.95}
    return monthly[d.month]


def heat_intensity(d: date) -> float:
    """Lahore heat stress May-Jul."""
    monthly = {1: 0.0, 2: 0.0, 3: 0.05, 4: 0.20, 5: 0.70, 6: 1.00,
               7: 0.85, 8: 0.55, 9: 0.30, 10: 0.10, 11: 0.0, 12: 0.0}
    return monthly[d.month]


def monsoon_intensity(d: date) -> float:
    """Monsoon-driven GI / waterborne cases (Jul-Sep)."""
    monthly = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.05, 6: 0.20,
               7: 1.00, 8: 0.95, 9: 0.55, 10: 0.10, 11: 0.0, 12: 0.0}
    return monthly[d.month]


# ---------------------------------------------------------------------------
# Clinical scenarios (diagnosis bucket -> typical medicine basket)
# Buckets normalised so we can reason about season-driven volume.
# ---------------------------------------------------------------------------

SCENARIOS = {
    "DENGUE_FEBRILE": {
        "diagnoses": ["DENGUE FEVER", "DHF", "VIRAL FEVER", "ACUTE FEBRILE ILLNESS", "PUO"],
        "basket": [
            ("Paracetamol",                         "Provas 1G 100ml inf",  0.95),
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",        0.98),
            ("ELECTROLYTES",                        "Hartmann Sol 1L",      0.65),
            ("Ondansetron",                         "Onset 8mg inj",        0.55),
            ("ESOMEPRAZOLE",                        "Nexum 40 Mg Inj",      0.45),
            ("Metoclopramide",                      "Maxolon 10 Mg Inj",    0.20),
            ("Ceftriaxone",                         "Rocephin 1g Inj",      0.15),
        ],
        "baseline": 1.5,
        "modifier":  lambda d: 1.0 + 7.0 * dengue_intensity(d),
    },
    "GASTROENTERITIS": {
        "diagnoses": ["AGE", "ACUTE G/E", "ACUTE GASTROENTERITIS", "G/E", "GE"],
        "basket": [
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",        0.97),
            ("Ondansetron",                         "Onset 8mg inj",        0.85),
            ("ESOMEPRAZOLE",                        "Nexum 40 Mg Inj",      0.55),
            ("Metronidazole",                       "Flagyl 100 ml Inj",    0.60),
            ("Ketorolac tromethamine",              "Toradol 30 Mg Inj",    0.30),
            ("PHLOROGLUCINOL/TRIMETHYLPHLOROGLUCINOL","Spasfon Inj",        0.45),
            ("ELECTROLYTES",                        "Hartmann Sol 1L",      0.40),
        ],
        "baseline": 4.0,
        "modifier":  lambda d: (
            1.0
            + 1.6 * monsoon_intensity(d)
            + (1.2 if in_window(d, EID_ADHA_WINDOWS) else 0.0)
            + (0.6 if in_window(d, RAMADAN_WINDOWS) else 0.0)
        ),
    },
    "RESPIRATORY_LRTI_URTI": {
        "diagnoses": ["URTI", "LRTI", "BRONCHIAL ASTHMA", "COPD EXACERBATION", "PNEUMONIA"],
        "basket": [
            ("Beclometasone Dipropionate",          "Beclate Resp 0.5mg/2ml",0.85),
            ("Ipratropium bromide",                 "Atrovent UDV",          0.80),
            ("HYDROCORTISONE SODIUM SUCCINATE",     "Solu-Cortef 100mg Inj", 0.55),
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",         0.70),
            ("Ceftriaxone",                         "Rocephin 1g Inj",       0.50),
            ("Paracetamol",                         "Provas 1G 100ml inf",   0.55),
            ("MEROPENEM",                           "Meronem 1G Inj",        0.10),
        ],
        "baseline": 2.0,
        "modifier":  lambda d: 1.0 + 3.0 * smog_intensity(d),
    },
    "HEAT_DEHYDRATION": {
        "diagnoses": ["HEAT STROKE", "DEHYDRATION", "ACUTE KIDNEY INJURY"],
        "basket": [
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",         0.99),
            ("ELECTROLYTES",                        "Hartmann Sol 1L",       0.85),
            ("Paracetamol",                         "Provas 1G 100ml inf",   0.55),
            ("Ondansetron",                         "Onset 8mg inj",         0.40),
        ],
        "baseline": 0.6,
        "modifier":  lambda d: 1.0 + 5.0 * heat_intensity(d),
    },
    "TRAUMA_RTA": {
        "diagnoses": ["RTA", "POLY TRAUMA", "HEAD INJURY", "FRACTURE"],
        "basket": [
            ("Ketorolac tromethamine",              "Toradol 30 Mg Inj",     0.92),
            ("Paracetamol",                         "Provas 1G 100ml inf",   0.65),
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",         0.80),
            ("Ceftriaxone",                         "Rocephin 1g Inj",       0.45),
            ("TRAMADOL/ METOCLOPRAMIDE",            "Tramal/Maxolon Combo",  0.30),
        ],
        "baseline": 1.4,
        "modifier":  lambda d: (
            1.0
            + (1.8 if in_window(d, EID_FITR_WINDOWS) else 0.0)
            + (1.4 if in_window(d, EID_ADHA_WINDOWS) else 0.0)
            + (1.0 if in_window(d, MUHARRAM_WINDOWS) else 0.0)
            + (0.6 if d in PUBLIC_HOLIDAYS else 0.0)
        ),
    },
    "CARDIO_NEURO": {
        "diagnoses": ["ACS", "MI", "HYPERTENSION", "STROKE", "LT BASAL GANGLIA HEMORRHAGE"],
        "basket": [
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",         0.85),
            ("PANTOPRAZOLE",                        "Pantop 40 Mg Inj",      0.65),
            ("Ondansetron",                         "Oniron 8mg inj",        0.30),
            ("Ceftriaxone",                         "Rocephin 1g Inj",       0.20),
            ("Paracetamol",                         "Provas 1G 100ml inf",   0.40),
        ],
        "baseline": 1.6,
        "modifier":  lambda d: 1.0 + 0.6 * smog_intensity(d),
    },
    "MIGRAINE_MSK": {
        "diagnoses": ["MIGRAINE", "MSK PAIN", "C.SPINE DISC", "BACKACHE"],
        "basket": [
            ("Ketorolac tromethamine",              "Toradol 30 Mg Inj",     0.90),
            ("PANTOPRAZOLE",                        "Pantop 40 Mg Inj",      0.55),
            ("Metoclopramide",                      "Maxolon 10 Mg Inj",     0.40),
            ("TRAMADOL/ METOCLOPRAMIDE",            "Tramal/Maxolon Combo",  0.20),
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",         0.55),
        ],
        "baseline": 1.2,
        "modifier":  lambda d: 1.0 + (0.4 if d.weekday() < 5 else 0.0),
    },
    "APD_GASTRITIS": {
        "diagnoses": ["APD", "APD, GASTRITIS.", "GASTRITIS"],
        "basket": [
            ("ESOMEPRAZOLE",                        "Nexum 40 Mg Inj",       0.85),
            ("PANTOPRAZOLE",                        "Pantop 40 Mg Inj",      0.45),
            ("Omeprazole",                          "Omepral 40 Mg Inj",     0.55),
            ("PHLOROGLUCINOL/TRIMETHYLPHLOROGLUCINOL","Spasfon Inj",         0.50),
            ("Ondansetron",                         "Oniron 8mg inj",        0.35),
            ("SODIUM CHLORIDE 0.9%",                "NS 0.9% 25 Ml",         0.60),
        ],
        "baseline": 2.2,
        "modifier":  lambda d: 1.0 + (0.7 if in_window(d, RAMADAN_WINDOWS) else 0.0),
    },
}


# ---------------------------------------------------------------------------
# Patient pool (re-used across the year so MRNs feel real)
# ---------------------------------------------------------------------------

PATIENT_POOL = []


def _make_patient_pool(seed_df: pd.DataFrame, n_extra: int = 1500):
    pool = (
        seed_df[["MRN", "Patient Name", "Age", "Gender"]]
        .drop_duplicates(subset=["MRN"]).to_dict(orient="records")
    )
    first_names_m = [
        "Ahmed", "Ali", "Hamza", "Bilal", "Usman", "Kashif", "Faisal", "Imran",
        "Tariq", "Nadeem", "Asif", "Salman", "Junaid", "Wajid", "Saad", "Adnan",
    ]
    first_names_f = [
        "Sara", "Ayesha", "Mariam", "Fatima", "Zainab", "Hira", "Rabia", "Kiran",
        "Nimra", "Sana", "Iqra", "Nida", "Hina", "Aniqa", "Madiha", "Saira",
    ]
    last_names = [
        "Khan", "Ahmed", "Iqbal", "Hussain", "Ali", "Mehmood", "Akhtar", "Sheikh",
        "Butt", "Anjum", "Riaz", "Shahid", "Yousaf", "Bashir", "Abbas",
    ]
    next_mrn = max(int(p["MRN"]) for p in pool) + 1
    for _ in range(n_extra):
        gender = random.choice(["Male", "Female"])
        first = random.choice(first_names_f if gender == "Female" else first_names_m)
        name = f"{first} {random.choice(last_names)}"
        pool.append({
            "MRN": next_mrn,
            "Patient Name": name,
            "Age": int(np.clip(np.random.normal(42, 18), 1, 92)),
            "Gender": gender,
        })
        next_mrn += 1
    return pool


def _pick_patient():
    return random.choice(PATIENT_POOL)


# ---------------------------------------------------------------------------
# Daily generator
# ---------------------------------------------------------------------------

def _day_volume_multiplier(d: date) -> float:
    """Background volume modulation independent of any single scenario."""
    weekday = d.weekday()
    base = 1.0
    if weekday == 4:          # Friday — half day OPD
        base *= 0.78
    if weekday >= 5:          # weekend — emergency only
        base *= 0.62
    if d in PUBLIC_HOLIDAYS:
        base *= 0.55
    if in_window(d, EID_FITR_WINDOWS) or in_window(d, EID_ADHA_WINDOWS):
        base *= 0.70
    return base


def _admission_time(d: date) -> datetime:
    hour = int(np.clip(np.random.normal(13, 5), 0, 23))
    minute = random.randint(0, 59)
    return datetime(d.year, d.month, d.day, hour, minute)


def _basket_for_visit(scenario_key: str) -> list[tuple[str, str]]:
    sc = SCENARIOS[scenario_key]
    out = []
    for generic, trade, prob in sc["basket"]:
        if random.random() < prob:
            out.append((generic, trade))
    if not out:
        # always at least the most likely med
        out.append((sc["basket"][0][0], sc["basket"][0][1]))
    # NS doses often get repeated 2-3x
    expanded = []
    for g, t in out:
        if "SODIUM CHLORIDE" in g.upper():
            for _ in range(random.choice([1, 2, 2, 3])):
                expanded.append((g, t))
        else:
            expanded.append((g, t))
    return expanded


def generate(seed_df: pd.DataFrame) -> pd.DataFrame:
    global PATIENT_POOL
    PATIENT_POOL = _make_patient_pool(seed_df)

    rows = []
    cur = START
    while cur <= END:
        day_mult = _day_volume_multiplier(cur)
        for key, sc in SCENARIOS.items():
            mean_visits = sc["baseline"] * sc["modifier"](cur) * day_mult
            n_visits = np.random.poisson(max(0.05, mean_visits))
            for _ in range(n_visits):
                pat = _pick_patient()
                diag = random.choice(sc["diagnoses"])
                doa = _admission_time(cur)
                doa_str = doa.strftime("%-m/%-d/%y %-I:%M %p")
                for generic, trade in _basket_for_visit(key):
                    rows.append({
                        "MRN":          pat["MRN"],
                        "Patient Name": pat["Patient Name"],
                        "Age":          pat["Age"],
                        "Gender":       pat["Gender"],
                        "DOA":          doa_str,
                        "Diagnosis":    diag,
                        "GenericName":  generic,
                        "Tradename":    trade,
                    })
        cur += timedelta(days=1)

    df = pd.DataFrame(rows)
    return df


def main():
    seed = pd.read_csv(SEED_CSV)
    print(f"Seed rows: {len(seed):,}")
    out = generate(seed)
    print(f"Generated rows: {len(out):,} ({(END - START).days + 1} days)")
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV}")


if __name__ == "__main__":
    main()
