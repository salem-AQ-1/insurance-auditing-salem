# Insurance Auditing – Technical Exercise

## Overview

This solution implements a rule-based auditing pipeline for hospital invoices against their contractual billing rules.

Given the 6–8 hour time budget, I prioritised depth over shallow coverage:

- Hospital 1 was used as the labelled development and calibration set.
- Hospital 2 was selected for the scored submission because its prose-based contract provided a substantially different parsing and service-matching problem.
- Hospitals 3–5 were intentionally left for future work rather than producing lower-confidence predictions.

## Approach

The audit pipeline:

1. Loads invoice and line-item data.
2. Parses contractual service rates and billing rules.
3. Normalises and matches abbreviated invoice descriptions to contract services.
4. Calculates expected line charges.
5. Applies relevant pricing rules including:
   - threshold premiums
   - weekend uplifts
   - cumulative volume discounts
   - bundles
   - daily caps
   - exclusion windows
6. Performs additional validation including:
   - duplicate invoice IDs
   - cross-invoice duplicate services
   - contract validation
   - service-date validation
   - unit-basis validation
   - line-total arithmetic
   - invoice-total reconciliation
7. Retains uncertain service/basis matches for review instead of forcing a high-confidence classification.

## Development-set Results

Hospital 1 was used for development and calibration only.

Final invoice-level results:

- Accuracy: 97.7%
- Correct classifications: 892 / 913
- Labelled erroneous invoices detected: 40 / 58
- False-positive invoices: 3

Hospital 1 is not included in `submission.csv`.

## Hospital 2

The Hospital 2 contract is substantially more prose-oriented than Hospital 1.

The parser extracted:

- 76 service rates
- 9 threshold rules
- 8 weekend uplift rules
- 8 volume discount rules
- 8 daily cap rules
- 3 bundle rules
- 6 exclusion rules

Service descriptions in the invoices were frequently abbreviated and reordered. I added abbreviation normalisation and fuzzy matching while retaining explicit review states for uncertain mappings.

Unmatched/review service lines decreased from 12,582 initially to 619 out of 14,360 lines after improving the matching layer.

During final validation, a rounding edge case was identified in cumulative volume-discount calculations. Discounted unit prices are therefore calculated using Decimal-based `ROUND_HALF_UP` rounding to avoid floating-point penny differences being incorrectly classified as pricing errors.

Because Hospital 2 has no ground-truth labels, I do not claim an accuracy estimate for it.

## Submission

`submission.csv` contains predictions for Hospital 2.

Confidence values are deliberately conservative. Deterministic findings supported by clearer rule-based checks receive higher confidence, while ambiguous service or basis mappings receive lower confidence.

## Running

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the Hospital 1 development audit:

```bash
python SRC/audit.py
```

Run Hospital 2:

```bash
python SRC/Audit_H2.py
```

Build the submission:

```bash
python SRC/Build_Submission.py
```

## AI-assisted Development

ChatGPT and Cursor were used for implementation assistance, debugging Python/Pandas issues, contract-parsing reasoning, refactoring, and iteration on service-description normalisation.

AI assistance was also used during final validation to investigate a rounding discrepancy in Hospital 2's cumulative volume-discount calculations. Changes were validated by rerunning the pipeline, inspecting intermediate audit outputs, and using the labelled Hospital 1 development set for development-stage measurement.

AI-generated suggestions were not treated as ground truth; contractual rules and measured outputs were used to validate audit decisions.

See `prompts.md` for additional details.
