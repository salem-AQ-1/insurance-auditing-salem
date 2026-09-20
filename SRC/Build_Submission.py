import pandas as pd

INPUT = "output/hospital_2_full_audit.csv"
OUTPUT = "submission.csv"

df = pd.read_csv(INPUT)

# Calibrated conservatively using Hospital 1 development results.
HIGH_CONFIDENCE_ERRORS = {
    "INVALID_UNIT_BASIS",
    "DAILY_CAP_VIOLATION",
    "DUPLICATE_INVOICE_ID",
    "DUPLICATE_SERVICE",
    "INVALID_CONTRACT",
    "INVALID_SERVICE_DATE",
    "INVOICE_TOTAL_MISMATCH",
    "OVERCHARGE",
    "LINE_TOTAL_ARITHMETIC",
}

MEDIUM_CONFIDENCE_ERRORS = {
    "EXCLUSION_VIOLATION",
}

REVIEW_STATUSES = {
    "REVIEW_SERVICE",
    "REVIEW_BASIS",
    "REVIEW_INVALID_DATE",
    "REVIEW",
}

rows = []

for invoice_id, inv in df.groupby("invoice_id"):

    statuses = set(inv["status"].dropna())

    high_errors = sorted(statuses & HIGH_CONFIDENCE_ERRORS)
    medium_errors = sorted(statuses & MEDIUM_CONFIDENCE_ERRORS)
    reviews = sorted(statuses & REVIEW_STATUSES)

    if high_errors:
        flagged = 1
        error_category = "|".join(high_errors + medium_errors)
        confidence = 0.95

    elif medium_errors:
        flagged = 1
        error_category = "|".join(medium_errors)
        confidence = 0.60

    elif reviews:
        # We do not have enough evidence to accuse the invoice of an error.
        flagged = 0
        error_category = "|".join(reviews)
        confidence = 0.50

    else:
        flagged = 0
        error_category = ""
        confidence = 0.90

    billed_total = int(inv["invoice_total_cents"].iloc[0])

    expected = inv["expected_line_total_cents"]

    if expected.notna().all():
        expected_total = int(expected.sum())
    else:
        expected_total = ""

    rows.append({
        "invoice_id": invoice_id,
        "flagged": flagged,
        "error_category": error_category,
        "expected_total_cents": expected_total,
        "billed_total_cents": billed_total,
        "confidence": confidence,
    })

submission = pd.DataFrame(rows)

submission.to_csv(OUTPUT, index=False)

print("================================")
print("FINAL SUBMISSION - HOSPITAL 2")
print("================================")
print("Invoices:", len(submission))
print("Flagged:", int(submission["flagged"].sum()))
print("Not flagged:", int((submission["flagged"] == 0).sum()))

print("\nConfidence:")
print(submission["confidence"].value_counts().sort_index())

print("\nSaved:", OUTPUT)