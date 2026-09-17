from pathlib import Path
from difflib import SequenceMatcher
import re
import pandas as pd


# =========================================================
# 1. Direct mapping between invoice columns and contract fields
# =========================================================

direct_mapping = {
    "contract_number": "Contract number",
    "description": "Service",
    "unit_basis_as_billed": "Unit basis",
    "unit_price_cents": "Rate"
}

print("Direct field mapping:")

for invoice_column, contract_field in direct_mapping.items():
    print(f"{invoice_column} -> {contract_field}")


# =========================================================
# 2. Read Hospital 1 data
# =========================================================

contract_text = Path(
    "contracts/hospital_1/provider_services_agreement.md"
).read_text(encoding="utf-8")

line_items = pd.read_csv(
    "invoices/hospital_1_line_items.csv"
)


# =========================================================
# 3. Get unique invoice descriptions
# =========================================================

invoice_descriptions = line_items["description"].dropna().unique()

print("\nUnique invoice descriptions count:", len(invoice_descriptions))


# =========================================================
# 4. Clean invoice descriptions
# =========================================================

def clean_description(text):

    # Remove NG codes such as /NG-3022
    text = re.sub(r"/NG-\d+", "", text)

    # Remove symbols
    text = re.sub(r"[^A-Za-z0-9\s]", " ", text)

    # Expand common abbreviations
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


# =========================================================
# 5. Extract contract services from Section 4
# =========================================================

section_4 = contract_text.split(
    "## 4. Rate Schedule"
)[1].split(
    "## 5."
)[0]

contract_services = []

for line in section_4.splitlines():

    if line.startswith("|") and not line.startswith("|---"):

        columns = [
            col.strip()
            for col in line.strip("|").split("|")
        ]

        if columns[0] != "Service":
            contract_services.append(columns[0])

print("\nContract services:", len(contract_services))


# =========================================================
# 6. Find best service match
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
        confidence = "High"

    elif best_score >= 0.55:
        confidence = "Medium"

    else:
        confidence = "Uncertain"

    return best_service, best_score, confidence


# =========================================================
# 7. Safe matching
# Only High confidence matches are accepted automatically
# =========================================================

def safe_service_match(description):

    service, score, confidence = find_best_service(description)

    if confidence == "High":
        return service, score, "High"

    return None, score, "Uncertain"


# =========================================================
# 8. Show sample of first 20 mappings
# =========================================================

print("\nService mapping sample:")

for description in invoice_descriptions[:20]:

    service, score, confidence = safe_service_match(description)

    print(
        description,
        "->",
        service,
        "|",
        confidence,
        "|",
        round(score, 2)
    )


# =========================================================
# 9. Map all unique invoice descriptions
# =========================================================

results = []

for description in invoice_descriptions:

    service, score, confidence = safe_service_match(description)

    results.append({
        "description": description,
        "matched_service": service,
        "score": round(score, 2),
        "confidence": confidence
    })


mapping_results = pd.DataFrame(results)


# =========================================================
# 10. Show mapping summary
# =========================================================

print("\nMapping summary:")

print(
    mapping_results["confidence"].value_counts()
)


# =========================================================
# 11. Show descriptions requiring review
# =========================================================

print("\nUncertain mappings:")

print(
    mapping_results[
        mapping_results["confidence"] == "Uncertain"
    ].to_string(index=False)
)