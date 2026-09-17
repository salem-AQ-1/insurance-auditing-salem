from pathlib import Path
from difflib import SequenceMatcher
from decimal import Decimal, ROUND_HALF_UP
import re
import pandas as pd


# =========================================================
# HOSPITAL 1 - FULL CONTRACT AUDIT
# =========================================================

CONTRACT_FILE = "contracts/hospital_1/provider_services_agreement.md"
INVOICES_FILE = "invoices/hospital_1_invoices.csv"
LINE_ITEMS_FILE = "invoices/hospital_1_line_items.csv"

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

    text = re.sub(r"/NG-\d+", "", str(text))
    text = re.sub(r"[^A-Za-z0-9\s]", " ", text)

    abbreviations = {
        "Adv": "Advanced",
        "Amb": "Ambulatory",
        "Asst": "Assisted",
        "Compr": "Comprehensive",
        "Cont": "Continuous",
        "Crit": "Critical",
        "Cr": "Care",
        "Derm": "Dermatologic",
        "Diag": "Diagnostic",
        "Dial": "Dialysis",
        "Emer": "Emergency",
        "Ent": "Otolaryngologic",
        "Ext": "Extended",
        "Foc": "Focused",
        "Fract": "Fraction",
        "Ger": "Geriatric",
        "Hm": "Home",
        "Img": "Imaging",
        "Inpt": "Inpatient",
        "Intens": "Intensive",
        "Interm": "Intermediate",
        "Msk": "Musculoskeletal",
        "Neuro": "Neurological",
        "Nurs": "Nursing",
        "Obs": "Observation",
        "Occ": "Occupancy",
        "Onc": "Oncology",
        "Ophth": "Ophthalmic",
        "Ortho": "Orthopaedic",
        "Outpt": "Outpatient",
        "Pall": "Palliative",
        "Physio": "Physiotherapy",
        "Prog": "Programme",
        "Psych": "Psychiatric",
        "Pulm": "Pulmonary",
        "Recov": "Recovery",
        "Ren": "Renal",
        "Rtn": "Routine",
        "Sess": "Session",
        "Spclst": "Specialist",
        "Std": "Standard",
        "Supp": "Support",
        "Svc": "Service",
        "Transf": "Transfusion",
        "Urol": "Urologic",
        "Vasc": "Vascular",
        "Wd": "Ward",
        "Wnd": "Wound"
    }

    words = text.split()
    words = [abbreviations.get(word, word) for word in words]

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
# 3. SECTION 4 - RATE SCHEDULE
# =========================================================

section_4 = get_section(
    "## 4. Rate Schedule",
    "## 5."
)

contract_rates = {}

for columns in parse_markdown_table(section_4):

    if len(columns) < 3:
        continue

    if columns[0] == "Service":
        continue

    rate = extract_number(columns[2])

    if rate is None:
        continue

    service = columns[0]

    contract_rates[service] = {
        "unit_basis": columns[1],
        "rate_cents": round_half_up(rate * 100)
    }


contract_services = list(contract_rates.keys())

print("Contract rates loaded:", len(contract_rates))


# =========================================================
# 4. SECTION 5 - THRESHOLD PREMIUMS
# =========================================================

threshold_rules = {}

for columns in parse_markdown_table(
    get_section("## 5.", "## 6.")
):

    if len(columns) < 3 or columns[0] == "Service":
        continue

    threshold = extract_number(columns[1])
    uplift = extract_percent(columns[2])

    if threshold is not None and uplift is not None:
        threshold_rules[columns[0]] = {
            "threshold": threshold,
            "uplift": uplift
        }


# =========================================================
# 5. SECTION 6 - NON-BUSINESS-DAY UPLIFTS
# =========================================================

weekend_rules = {}

for columns in parse_markdown_table(
    get_section("## 6.", "## 7.")
):

    if len(columns) < 2 or columns[0] == "Service":
        continue

    uplift = extract_percent(columns[1])

    if uplift is not None:
        weekend_rules[columns[0]] = uplift


# =========================================================
# 6. SECTION 7 - CUMULATIVE VOLUME DISCOUNTS
# =========================================================

discount_rules = {}

for columns in parse_markdown_table(
    get_section("## 7.", "## 8.")
):

    if len(columns) < 3 or columns[0] == "Service":
        continue

    threshold = extract_number(columns[1])
    discount = extract_percent(columns[2])

    if threshold is None or discount is None:
        continue

    discount_rules.setdefault(
        columns[0],
        []
    ).append({
        "threshold": threshold,
        "discount": discount
    })


for service in discount_rules:

    discount_rules[service] = sorted(
        discount_rules[service],
        key=lambda x: x["threshold"]
    )


# =========================================================
# 7. SECTION 8 - DAILY CAPS
# =========================================================

daily_caps = {}

for columns in parse_markdown_table(
    get_section("## 8.", "## 9.")
):

    if len(columns) < 2 or columns[0] == "Service":
        continue

    cap = extract_number(columns[1])

    if cap is not None:
        daily_caps[columns[0]] = cap


# =========================================================
# 8. SECTION 9 - BUNDLES
# =========================================================

bundle_rules = []

for columns in parse_markdown_table(
    get_section("## 9.", "## 10.")
):

    if len(columns) < 4 or columns[0] == "Service A":
        continue

    rate_a = extract_number(columns[2])
    rate_b = extract_number(columns[3])

    if rate_a is None or rate_b is None:
        continue

    bundle_rules.append({
        "service_a": columns[0],
        "service_b": columns[1],
        "rate_a_cents": round_half_up(rate_a * 100),
        "rate_b_cents": round_half_up(rate_b * 100)
    })


# =========================================================
# 9. SECTION 10 - EXCLUSION WINDOWS
# =========================================================

exclusion_rules = []

for columns in parse_markdown_table(
    get_section("## 10.")
):

    if len(columns) < 3 or columns[0] == "Service":
        continue

    days = extract_number(columns[1])

    if days is None:
        continue

    exclusion_rules.append({
        "service": columns[0],
        "days": int(days),
        "other_service": columns[2]
    })


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

    best_service = None
    best_score = 0

    for service in contract_services:

        score = SequenceMatcher(
            None,
            cleaned.lower(),
            service.lower()
        ).ratio()

        if score > best_score:
            best_score = score
            best_service = service

    if best_score >= 0.75:
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

EXPECTED_CONTRACT = "INS-H1-2024-0417"
EXPECTED_FACILITY = "F-MAIN"
VALID_PLAN_TIERS = {"BRONZE", "SILVER", "GOLD"}

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

data["plan_tier_valid"] = (
    data["plan_tier"]
    .astype(str)
    .str.strip()
    .str.upper()
    .isin(VALID_PLAN_TIERS)
)

data["service_date_valid"] = (
    data["service_date"].notna()
    &
    data["invoice_date_parsed"].notna()
    &
    (
        data["service_date"]
        <=
        data["invoice_date_parsed"]
    )
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
print("HOSPITAL 1 - FULL AUDIT SUMMARY")
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
    OUTPUT_DIR / "hospital_1_full_audit.csv",
    index=False
)

data[
    data["status"] == "OVERCHARGE"
].to_csv(
    OUTPUT_DIR / "hospital_1_overcharges.csv",
    index=False
)

data[
    data["status"] == "UNDERCHARGE"
].to_csv(
    OUTPUT_DIR / "hospital_1_undercharges.csv",
    index=False
)

data[
    data["status"] == "DAILY_CAP_VIOLATION"
].to_csv(
    OUTPUT_DIR / "hospital_1_daily_cap_violations.csv",
    index=False
)

data[
    data["status"] == "EXCLUSION_VIOLATION"
].to_csv(
    OUTPUT_DIR / "hospital_1_exclusion_violations.csv",
    index=False
)

data[
    data["status"] == "DUPLICATE_SERVICE"
].to_csv(
    OUTPUT_DIR / "hospital_1_duplicate_services.csv",
    index=False
)

data[
    data["status"].str.startswith(
        ("REVIEW", "INVALID", "DUPLICATE", "INVOICE")
    )
].to_csv(
    OUTPUT_DIR / "hospital_1_review.csv",
    index=False
)

print("\nFiles saved in output/")
print("hospital_1_full_audit.csv")
print("hospital_1_overcharges.csv")
print("hospital_1_undercharges.csv")
print("hospital_1_daily_cap_violations.csv")
print("hospital_1_exclusion_violations.csv")
print("hospital_1_duplicate_services.csv")
print("hospital_1_review.csv")