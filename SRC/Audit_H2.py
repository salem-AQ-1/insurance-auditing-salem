from pathlib import Path
from difflib import SequenceMatcher
from decimal import Decimal, ROUND_HALF_UP
import re
import pandas as pd


# =========================================================
# HOSPITAL 2 - FULL CONTRACT AUDIT
# =========================================================

CONTRACT_FILE = "contracts/hospital_2/master_services_agreement.md"
INVOICES_FILE = "invoices/hospital_2_invoices.csv"
LINE_ITEMS_FILE = "invoices/hospital_2_line_items.csv"

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


# =========================================================
# 1. LOAD DATA
# =========================================================

contract_text = Path(CONTRACT_FILE).read_text(encoding="utf-8")

original_invoices = pd.read_csv(INVOICES_FILE)
line_items = pd.read_csv(LINE_ITEMS_FILE)

# Keep duplicate IDs for validation before deduplicating the merge source.
duplicate_invoice_ids = set(
    original_invoices.loc[
        original_invoices["invoice_id"].duplicated(keep=False),
        "invoice_id"
    ]
)

# Prevent duplicate invoice rows from multiplying line items during merge.
invoices = original_invoices.drop_duplicates(
    subset=["invoice_id"],
    keep="first"
).copy()

data = line_items.merge(
    invoices,
    on="invoice_id",
    how="left"
)

data["service_date_original"] = data["service_date"]

data["service_date"] = pd.to_datetime(
    data["service_date"],
    format="mixed",
    errors="coerce"
)

data["invoice_date_parsed"] = pd.to_datetime(
    data["invoice_date"],
    format="mixed",
    errors="coerce"
)

data["quantity"] = pd.to_numeric(
    data["quantity"],
    errors="coerce"
).fillna(0)

print(
    "Invalid service dates:",
    int(data["service_date"].isna().sum())
)


# =========================================================
# 2. HELPERS
# =========================================================

def round_half_up(value):
    return int(
        Decimal(str(value)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP
        )
    )


def clean_description(text):

    # Remove Hospital 2 reference suffixes such as /SA-3924.
    text = re.sub(r"/(?:NG|SA)-\d+", "", str(text), flags=re.I)
    text = re.sub(r"[^A-Za-z0-9\s]", " ", text)

    abbreviations = {
        "ADV": "Advanced",
        "AMB": "Ambulatory",
        "ASST": "Assisted",
        "BIOP": "Biopsy",
        "COMPR": "Comprehensive",
        "CONF": "Conference",
        "CONT": "Continuous",
        "CRIT": "Critical",
        "CR": "Care",
        "CS": "Case",
        "DERM": "Dermatologic",
        "DIAG": "Diagnostic",
        "DIAL": "Dialysis",
        "DISP": "Dispensed",
        "ELECT": "Elective",
        "EMER": "Emergency",
        "ENT": "Otolaryngologic",
        "EXT": "Extended",
        "FOC": "Focused",
        "FRACT": "Fraction",
        "GER": "Geriatric",
        "GI": "Gastrointestinal",
        "HAEM": "Haematology",
        "HM": "Home",
        "IMG": "Imaging",
        "INPT": "Inpatient",
        "INTENS": "Intensive",
        "INTERM": "Intermittent",
        "INTERP": "Interpretation",
        "ISOL": "Isolation",
        "LAB": "Laboratory",
        "METAB": "Metabolic",
        "MONIT": "Monitoring",
        "MSK": "Musculoskeletal",
        "NEURO": "Neurological",
        "NURS": "Nursing",
        "NUTR": "Nutritional",
        "OBS": "Observation",
        "OCC": "Occupancy",
        "ONC": "Oncology",
        "OPHTH": "Ophthalmic",
        "ORTHO": "Orthopaedic",
        "OUTPT": "Outpatient",
        "PALL": "Palliative",
        "PHARM": "Pharmacy",
        "PHYSIO": "Physiotherapy",
        "PROC": "Procedure",
        "PROG": "Programme",
        "PSYCH": "Psychiatric",
        "PULM": "Pulmonary",
        "RECOV": "Recovery",
        "REN": "Renal",
        "RM": "Room",
        "RTN": "Routine",
        "SESS": "Session",
        "SPCLST": "Specialist",
        "STD": "Standard",
        "SUPP": "Support",
        "SVC": "Service",
        "TELEM": "Telemetry",
        "TRANSP": "Transport",
        "TRANSF": "Transfusion",
        "UROL": "Urologic",
        "VASC": "Vascular",
        "VST": "Visit",
        "WD": "Ward",
        "WND": "Wound"
    }

    words = text.split()
    words = [abbreviations.get(word.upper(), word) for word in words]

    return " ".join(words)


def normalize_basis(text):

    if pd.isna(text):
        return ""

    text = str(text).lower().strip()
    text = text.replace("_", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = " ".join(text.split())

    aliases = {
        "per visit": "per_visit",
        "per procedure": "per_procedure",
        "per hour": "per_hour",
        "per day": "per_day",
        "per day of service": "per_day",
        "per item": "per_item",
        "per item supplied": "per_item",
        "per night": "per_night",
        "per night of occupancy": "per_night",
        "per unit dispensed": "per_unit_dispensed",
        "per test": "per_test",
    }

    return aliases.get(text, text)
def extract_number(text):
    match = re.search(
        r"([\d,]+(?:\.\d+)?)",
        str(text)
    )

    if not match:
        return None

    return float(
        match.group(1).replace(",", "")
    )


def extract_percent(text):

    number = extract_number(text)

    if number is None:
        return None

    return number / 100


def get_section(start_heading, end_heading=None):

    if start_heading not in contract_text:
        return ""

    section = contract_text.split(
        start_heading,
        1
    )[1]

    if end_heading and end_heading in section:
        section = section.split(
            end_heading,
            1
        )[0]

    return section


def parse_markdown_table(section):

    rows = []

    for line in section.splitlines():

        line = line.strip()

        if not line.startswith("|"):
            continue

        if re.match(r"^\|\s*-", line):
            continue

        columns = [
            column.strip()
            for column in line.strip("|").split("|")
        ]

        rows.append(columns)

    return rows


# =========================================================
# 3-9. HOSPITAL 2 - PARSE PROSE CONTRACT RULES
# =========================================================

# Hospital 2 stores service rules in prose clauses rather than markdown tables.
# Parse each contracted-service clause directly from the agreement.
service_clauses = []
for raw_line in contract_text.splitlines():
    line = raw_line.strip()
    m = re.match(r"^\d+\.\d+\s+In respect of (.+?), the Provider shall invoice the Payer at the rate of GBP\s+([\d,]+(?:\.\d+)?)\s+(.+?)\.", line)
    if not m:
        continue

    service = m.group(1).strip()
    rate = float(m.group(2).replace(",", ""))
    basis_phrase = m.group(3).strip()

    # The normal contract wording is "per <basis>".  If extra wording follows,
    # keep only the first recognised billable basis.
    basis_patterns = [
        (r"per night of occupancy", "per night of occupancy"),
        (r"per day of service", "per day of service"),
        (r"per unit dispensed", "per unit dispensed"),
        (r"per item supplied", "per item supplied"),
        (r"per procedure", "per procedure"),
        (r"per visit", "per visit"),
        (r"per hour", "per hour"),
        (r"per test", "per test"),
        (r"per item", "per item supplied"),
    ]
    unit_basis = None
    for pattern, canonical in basis_patterns:
        if re.search(pattern, basis_phrase, flags=re.I):
            unit_basis = canonical
            break
    if unit_basis is None:
        continue

    service_clauses.append((service, rate, unit_basis, line))

contract_rates = {
    service: {
        "unit_basis": basis,
        "rate_cents": round_half_up(rate * 100)
    }
    for service, rate, basis, _ in service_clauses
}
contract_services = list(contract_rates.keys())

threshold_rules = {}
weekend_rules = {}
discount_rules = {}
daily_caps = {}
bundle_rules = []
exclusion_rules = []

for service, _, _, clause in service_clauses:
    # Patient/Service-Day threshold premium.
    m = re.search(
        r"aggregate quantity of this Service delivered to a Patient on a single Service Day exceeds.*?\(([\d,]+)\).*?rate applicable to that Service Day shall be increased by.*?\((\d+(?:\.\d+)?)%\)",
        clause,
        flags=re.I,
    )
    if m:
        threshold_rules[service] = {
            "threshold": float(m.group(1).replace(",", "")),
            "uplift": float(m.group(2)) / 100,
        }

    # Weekend / non-business-day uplift.
    m = re.search(
        r"does not fall on a Business Day.*?increased by.*?\((\d+(?:\.\d+)?)%\)",
        clause,
        flags=re.I,
    )
    if m:
        weekend_rules[service] = float(m.group(1)) / 100

    # Cumulative volume discounts. There may be multiple thresholds in one clause.
    for dm in re.finditer(
        r"cumulative utilisation of this Service exceeds.*?\(([\d,]+)\).*?discount of.*?\((\d+(?:\.\d+)?)%\).*?subsequent Unit",
        clause,
        flags=re.I,
    ):
        discount_rules.setdefault(service, []).append({
            "threshold": float(dm.group(1).replace(",", "")),
            "discount": float(dm.group(2)) / 100,
        })

    # Daily caps.
    m = re.search(
        r"shall not bill more than.*?\(([\d,]+)\).*?of this Service for a Patient on a single Service Day",
        clause,
        flags=re.I,
    )
    if m:
        daily_caps[service] = float(m.group(1).replace(",", ""))

    # Exclusion windows, measured in either direction under Article III 3.6.
    m = re.search(
        r"This Service is not billable where (.+?) has been delivered to the same Patient within.*?\(([\d,]+)\)\s+days of the Service Date",
        clause,
        flags=re.I,
    )
    if m:
        exclusion_rules.append({
            "service": service,
            "days": int(m.group(2).replace(",", "")),
            "other_service": m.group(1).strip(),
        })

    # Bundles: capture the companion service and both substituted rates.
    bm = re.search(
        r"Where this Service and (.+?) are both delivered to the same Patient on the same Service Day, the two shall be billed as a bundle, this Service at GBP\s+([\d,]+(?:\.\d+)?)\s+.+? and (.+?) at GBP\s+([\d,]+(?:\.\d+)?)\s+.+?, in substitution for their standalone rates",
        clause,
        flags=re.I,
    )
    if bm:
        other_service = bm.group(1).strip()
        rate_self = round_half_up(float(bm.group(2).replace(",", "")) * 100)
        named_other = bm.group(3).strip()
        rate_other = round_half_up(float(bm.group(4).replace(",", "")) * 100)
        # Avoid adding the same bundle twice when its reciprocal clause also appears.
        key = frozenset((service, other_service))
        existing = {frozenset((b["service_a"], b["service_b"])) for b in bundle_rules}
        if key not in existing:
            bundle_rules.append({
                "service_a": service,
                "service_b": other_service,
                "rate_a_cents": rate_self,
                "rate_b_cents": rate_other,
            })

for service in discount_rules:
    discount_rules[service] = sorted(
        discount_rules[service],
        key=lambda x: x["threshold"]
    )

print("Contract rates loaded:", len(contract_rates))
print("Threshold rules:", len(threshold_rules))
print("Weekend uplift rules:", len(weekend_rules))
print("Volume discount rules:", len(discount_rules))
print("Daily cap rules:", len(daily_caps))
print("Bundle rules:", len(bundle_rules))
print("Exclusion rules:", len(exclusion_rules))


# =========================================================
# 10. SERVICE MATCHING
# =========================================================

def find_best_service(description):

    cleaned = clean_description(description)

    def norm_tokens(s):
        return [
            re.sub(r"[^a-z0-9]", "", w.lower())
            for w in str(s).split()
            if re.sub(r"[^a-z0-9]", "", w.lower())
        ]

    desc_tokens = norm_tokens(cleaned)

    best_service = None
    best_score = 0

    for service in contract_services:
        service_tokens = norm_tokens(service)

        seq_score = SequenceMatcher(
            None,
            " ".join(desc_tokens),
            " ".join(service_tokens)
        ).ratio()

        # Token-prefix score helps with abbreviations such as
        # "Metab", "Rehab", "Telem", etc. without hard-coding every alias.
        matched = 0
        used = set()
        for dt in desc_tokens:
            candidates = []
            for i, st in enumerate(service_tokens):
                if i in used:
                    continue
                if dt == st or (len(dt) >= 4 and st.startswith(dt)) or (len(st) >= 4 and dt.startswith(st)):
                    candidates.append(i)
            if candidates:
                used.add(candidates[0])
                matched += 1

        token_score = matched / max(len(desc_tokens), len(service_tokens), 1)
        score = max(seq_score, token_score)

        if score > best_score:
            best_score = score
            best_service = service

    if best_score >= 0.60:
        return best_service, best_score

    return None, best_score


matches = data["description"].apply(find_best_service)

data["matched_service"] = matches.apply(
    lambda x: x[0]
)

data["match_score"] = matches.apply(
    lambda x: round(x[1], 2)
)


# =========================================================
# 11. UNIT BASIS
# =========================================================

def get_contract_basis(service):

    if pd.isna(service):
        return None

    if service not in contract_rates:
        return None

    return contract_rates[service]["unit_basis"]


data["contract_unit_basis"] = (
    data["matched_service"].apply(
        get_contract_basis
    )
)


def basis_matches(row):

    if pd.isna(row["matched_service"]):
        return None

    return (
        normalize_basis(row["unit_basis_as_billed"])
        ==
        normalize_basis(row["contract_unit_basis"])
    )


data["basis_match"] = data.apply(
    basis_matches,
    axis=1
)


# =========================================================
# 12. HEADER / INVOICE VALIDATION
# =========================================================

EXPECTED_CONTRACT = "INS-H2-2024-1183"
EXPECTED_FACILITY = "F-MAIN"
VALID_PLAN_TIERS = None

data["contract_number_valid"] = (
    data["contract_number"]
    .astype(str)
    .str.strip()
    .eq(EXPECTED_CONTRACT)
)

data["facility_valid"] = (
    data["facility_code"]
    .astype(str)
    .str.strip()
    .eq(EXPECTED_FACILITY)
)

# Article I 1.3 says rates apply irrespective of plan tier.
data["plan_tier_valid"] = True

CONTRACT_START = pd.Timestamp("2024-01-01")
CONTRACT_END = pd.Timestamp("2025-12-31")

data["service_date_valid"] = (
    data["service_date"].notna()
    & data["invoice_date_parsed"].notna()
    & data["service_date"].between(CONTRACT_START, CONTRACT_END)
    & (data["service_date"] <= data["invoice_date_parsed"])
)

data["duplicate_invoice_id"] = (
    data["invoice_id"].isin(
        duplicate_invoice_ids
    )
)


# =========================================================
# 13. INVOICE TOTAL VALIDATION
# =========================================================

calculated_invoice_totals = (
    line_items
    .groupby("invoice_id")["line_total_cents"]
    .sum()
    .to_dict()
)

invoice_total_lookup = (
    invoices
    .set_index("invoice_id")["invoice_total_cents"]
    .to_dict()
)


def check_invoice_total(invoice_id):

    if invoice_id not in calculated_invoice_totals:
        return False

    if invoice_id not in invoice_total_lookup:
        return False

    return (
        calculated_invoice_totals[invoice_id]
        ==
        invoice_total_lookup[invoice_id]
    )


data["invoice_total_valid"] = (
    data["invoice_id"].apply(
        check_invoice_total
    )
)


# =========================================================
# 14. MATCHED VALID-DATE DATA
# =========================================================

matched_data = data[
    data["matched_service"].notna()
    &
    data["service_date"].notna()
].copy()


# =========================================================
# 15. DAILY QUANTITY
# =========================================================

daily_quantity = (
    matched_data
    .groupby([
        "patient_id",
        "service_date",
        "matched_service"
    ])["quantity"]
    .sum()
    .to_dict()
)

# =========================================================
# 16. CROSS-INVOICE DUPLICATE
# =========================================================

duplicate_invoice_lines = set()

duplicate_cols = [
    "patient_id",
    "service_date",
    "description",
    "quantity",
    "unit_price_cents",
]

valid_dup = data[
    data["service_date"].notna()
].copy()

for _, group in valid_dup.groupby(
    duplicate_cols,
    dropna=False
):

    invoice_ids = sorted(
        group["invoice_id"].dropna().unique()
    )

    if len(invoice_ids) <= 1:
        continue

    # First invoice is the original.
    # Any later invoice is treated as the duplicate.
    duplicate_ids = set(invoice_ids[1:])

    duplicate_rows = group[
        group["invoice_id"].isin(duplicate_ids)
    ]

    duplicate_invoice_lines.update(
        duplicate_rows.index.tolist()
    )


data["duplicate_service"] = data.index.isin(
    duplicate_invoice_lines
)


# =========================================================
# 17. PATIENT-DAY SERVICES
# =========================================================

patient_day_services = (
    matched_data
    .groupby([
        "patient_id",
        "service_date"
    ])["matched_service"]
    .apply(set)
    .to_dict()
)


# =========================================================
# 18. BUNDLED RATES
# =========================================================

def bundled_rate(row):

    service = row["matched_service"]

    if pd.isna(service):
        return None, False

    if service not in contract_rates:
        return None, False

    normal_rate = contract_rates[
        service
    ]["rate_cents"]

    if pd.isna(row["service_date"]):
        return normal_rate, False

    key = (
        row["patient_id"],
        row["service_date"]
    )

    services = patient_day_services.get(
        key,
        set()
    )

    for rule in bundle_rules:

        if (
            rule["service_a"] in services
            and
            rule["service_b"] in services
        ):

            if service == rule["service_a"]:
                return rule["rate_a_cents"], True

            if service == rule["service_b"]:
                return rule["rate_b_cents"], True

    return normal_rate, False


bundle_results = data.apply(
    bundled_rate,
    axis=1
)

data["base_rate_cents"] = (
    bundle_results.apply(lambda x: x[0])
)

data["bundle_applied"] = (
    bundle_results.apply(lambda x: x[1])
)


# =========================================================
# 19. THRESHOLD PREMIUM
# =========================================================

def threshold_uplift(row):

    service = row["matched_service"]

    if pd.isna(service):
        return 0

    if pd.isna(row["service_date"]):
        return 0

    if service not in threshold_rules:
        return 0

    key = (
        row["patient_id"],
        row["service_date"],
        service
    )

    quantity = daily_quantity.get(key, 0)
    rule = threshold_rules[service]

    if quantity > rule["threshold"]:
        return rule["uplift"]

    return 0


data["threshold_uplift"] = data.apply(
    threshold_uplift,
    axis=1
)


# =========================================================
# 20. NON-BUSINESS-DAY UPLIFT
# =========================================================

def weekend_uplift(row):

    service = row["matched_service"]

    if pd.isna(service):
        return 0

    if pd.isna(row["service_date"]):
        return 0

    if service not in weekend_rules:
        return 0

    # Monday=0 ... Saturday=5, Sunday=6
    if row["service_date"].weekday() in [5, 6]:
        return weekend_rules[service]

    return 0


data["weekend_uplift"] = data.apply(
    weekend_uplift,
    axis=1
)


# =========================================================
# 21. DAILY CAP
# =========================================================

def cap_exceeded(row):

    service = row["matched_service"]

    if pd.isna(service):
        return False

    if pd.isna(row["service_date"]):
        return False

    if service not in daily_caps:
        return False

    key = (
        row["patient_id"],
        row["service_date"],
        service
    )

    return (
        daily_quantity.get(key, 0)
        >
        daily_caps[service]
    )


data["cap_exceeded"] = data.apply(
    cap_exceeded,
    axis=1
)


# =========================================================
# 22. EXCLUSION WINDOWS
# =========================================================

patient_service_dates = {}

for _, row in matched_data.iterrows():

    key = (
        row["patient_id"],
        row["matched_service"]
    )

    patient_service_dates.setdefault(
        key,
        []
    ).append(row["service_date"])


def exclusion_violation(row):

    service = row["matched_service"]

    if pd.isna(service):
        return False

    if pd.isna(row["service_date"]):
        return False

    patient = row["patient_id"]
    current_date = row["service_date"]

    for rule in exclusion_rules:

        if service != rule["service"]:
            continue

        other_dates = patient_service_dates.get(
            (
                patient,
                rule["other_service"]
            ),
            []
        )

        for other_date in other_dates:

            if pd.isna(other_date):
                continue

            difference = abs(
                (current_date - other_date).days
            )

            if difference <= rule["days"]:
                return True

    return False


data["exclusion_violation"] = data.apply(
    exclusion_violation,
    axis=1
)


# =========================================================
# 23. SORT FOR CUMULATIVE UTILISATION
# =========================================================

data = data.sort_values(
    by=["service_date", "line_id"],
    na_position="last"
).reset_index(drop=True)


# =========================================================
# 24. CUMULATIVE VOLUME DISCOUNT
# =========================================================

running_usage = {}
volume_discounts = []

for _, row in data.iterrows():

    service = row["matched_service"]

    if pd.isna(service) or pd.isna(row["service_date"]):

        volume_discounts.append(0)
        continue

    prior_usage = running_usage.get(
        service,
        0
    )

    discount = 0

    if service in discount_rules:

        for rule in discount_rules[service]:

            if prior_usage > rule["threshold"]:

                discount = max(
                    discount,
                    rule["discount"]
                )

    volume_discounts.append(discount)

    running_usage[service] = (
        prior_usage + row["quantity"]
    )


data["volume_discount"] = volume_discounts


# =========================================================
# 25. EXPECTED UNIT PRICE
# Order:
# bundle -> premiums/uplifts -> volume discount
# =========================================================

def calculate_expected_rate(row):

    if pd.isna(row["matched_service"]):
        return None

    if pd.isna(row["service_date"]):
        return None

    rate = row["base_rate_cents"]

    if pd.isna(rate):
        return None

    if row["threshold_uplift"] > 0:

        rate = round_half_up(
            rate * (
                1 + row["threshold_uplift"]
            )
        )

    if row["weekend_uplift"] > 0:

        rate = round_half_up(
            rate * (
                1 + row["weekend_uplift"]
            )
        )

    if row["volume_discount"] > 0:

        rate = round_half_up(
            rate * (
                1 - row["volume_discount"]
            )
        )

    return rate


data["expected_unit_price_cents"] = (
    data.apply(
        calculate_expected_rate,
        axis=1
    )
)


# =========================================================
# 26. EXPECTED LINE TOTAL
# =========================================================

def expected_line_total(row):

    rate = row["expected_unit_price_cents"]

    if pd.isna(rate):
        return None

    return round_half_up(
        rate * row["quantity"]
    )


data["expected_line_total_cents"] = (
    data.apply(
        expected_line_total,
        axis=1
    )
)


data["unit_price_difference_cents"] = (
    data["unit_price_cents"]
    -
    data["expected_unit_price_cents"]
)

data["line_total_difference_cents"] = (
    data["line_total_cents"]
    -
    data["expected_line_total_cents"]
)
# =========================================================
# LINE TOTAL ARITHMETIC CHECK
# =========================================================

data["calculated_line_total_cents"] = (
    data["quantity"] * data["unit_price_cents"]
).apply(round_half_up)

data["line_total_arithmetic_error"] = (
    data["line_total_cents"]
    != data["calculated_line_total_cents"]
)

# =========================================================
# 27. FINAL STATUS
# =========================================================

def final_status(row):

    if pd.isna(row["service_date"]):
        return "REVIEW_INVALID_DATE"

    if row["duplicate_invoice_id"]:
        return "DUPLICATE_INVOICE_ID"

    if not row["contract_number_valid"]:
        return "INVALID_CONTRACT"

    if not row["facility_valid"]:
        return "INVALID_FACILITY"

    if not row["plan_tier_valid"]:
        return "INVALID_PLAN_TIER"

    if not row["service_date_valid"]:
        return "INVALID_SERVICE_DATE"

    if not row["invoice_total_valid"]:
        return "INVOICE_TOTAL_MISMATCH"

    if row["line_total_arithmetic_error"]:
        return "LINE_TOTAL_ARITHMETIC"

    if pd.isna(row["matched_service"]):
        return "REVIEW_SERVICE"

    if row["basis_match"] is not True:
        return "REVIEW_BASIS"

    if row["duplicate_service"]:
        return "DUPLICATE_SERVICE"

    if row["exclusion_violation"]:
        return "EXCLUSION_VIOLATION"

    if row["cap_exceeded"]:
        return "DAILY_CAP_VIOLATION"

    difference = row["line_total_difference_cents"]

    if pd.isna(difference):
        return "REVIEW"

    if difference == 0:
        return "PASS"

    if difference > 0:
        return "OVERCHARGE"

    return "UNDERCHARGE"


data["status"] = data.apply(
    final_status,
    axis=1
)


# =========================================================
# 28. SUMMARY
# =========================================================

print("\n======================================")
print("HOSPITAL 2 - FULL AUDIT SUMMARY")
print("======================================")

print(data["status"].value_counts())

print("\nTotal lines:", len(data))

print("\nADDITIONAL CHECKS")

print(
    "Duplicate service affected lines:",
    int(data["duplicate_service"].sum())
)

print(
    "Duplicate invoice ID affected lines:",
    int(data["duplicate_invoice_id"].sum())
)

print(
    "Invalid contract number affected lines:",
    int((~data["contract_number_valid"]).sum())
)

print(
    "Invalid facility affected lines:",
    int((~data["facility_valid"]).sum())
)

print(
    "Invalid plan tier affected lines:",
    int((~data["plan_tier_valid"]).sum())
)

print(
    "Invalid service/invoice date affected lines:",
    int((~data["service_date_valid"]).sum())
)

print(
    "Invoice total mismatch affected lines:",
    int((~data["invoice_total_valid"]).sum())
)


# =========================================================
# 29. POTENTIAL OVERCHARGE
# =========================================================

overcharge_df = data[
    data["status"] == "OVERCHARGE"
].copy()

potential_overcharge_cents = (
    overcharge_df[
        "line_total_difference_cents"
    ].sum()
)

potential_overcharge_gbp = (
    potential_overcharge_cents / 100
)

print(
    "\nPotential overcharge (GBP):",
    round(potential_overcharge_gbp, 2)
)


# =========================================================
# 30. SAVE OUTPUTS
# =========================================================

data.to_csv(
    OUTPUT_DIR / "hospital_2_full_audit.csv",
    index=False
)

data[
    data["status"] == "OVERCHARGE"
].to_csv(
    OUTPUT_DIR / "hospital_2_overcharges.csv",
    index=False
)

data[
    data["status"] == "UNDERCHARGE"
].to_csv(
    OUTPUT_DIR / "hospital_2_undercharges.csv",
    index=False
)

data[
    data["status"] == "DAILY_CAP_VIOLATION"
].to_csv(
    OUTPUT_DIR / "hospital_2_daily_cap_violations.csv",
    index=False
)

data[
    data["status"] == "EXCLUSION_VIOLATION"
].to_csv(
    OUTPUT_DIR / "hospital_2_exclusion_violations.csv",
    index=False
)

data[
    data["status"] == "DUPLICATE_SERVICE"
].to_csv(
    OUTPUT_DIR / "hospital_2_duplicate_services.csv",
    index=False
)

data[
    data["status"].str.startswith(
        ("REVIEW", "INVALID", "DUPLICATE", "INVOICE")
    )
].to_csv(
    OUTPUT_DIR / "hospital_2_review.csv",
    index=False
)

print("\nFiles saved in output/")
print("hospital_2_full_audit.csv")
print("hospital_2_overcharges.csv")
print("hospital_2_undercharges.csv")
print("hospital_2_daily_cap_violations.csv")
print("hospital_2_exclusion_violations.csv")
print("hospital_2_duplicate_services.csv")
print("hospital_2_review.csv")