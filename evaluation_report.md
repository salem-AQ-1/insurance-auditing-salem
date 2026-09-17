# Evaluation Report

## 1. Approach and Measurement

I used Hospital 1 as the development and calibration set because it is the only hospital with ground-truth labels. I first built a rule-based auditing pipeline that parses contract rules, maps invoice descriptions to contract services, calculates expected charges, and performs additional invoice and cross-invoice validation.

I measured Hospital 1 at invoice level. An invoice was considered detected as erroneous when the audit produced one or more error findings.

The final Hospital 1 result was:

- 892 correct classifications out of 913 invoices
- 97.7% accuracy
- 40 of 58 labelled erroneous invoices detected
- 3 false-positive invoices

Hospital 1 was used only for development and calibration and is not included in the scored submission.

I then applied the approach to Hospital 2. I chose Hospital 2 rather than attempting shallow coverage of Hospitals 2–5 because its prose-based contract provided a substantially different extraction and matching problem.

## 2. Hospital 1 Performance and Error Analysis

Several deterministic categories were particularly reliable on the development set. Detected duplicate invoice IDs, invalid contracts, invalid service dates, invoice-total mismatches, line-total arithmetic errors, daily-cap violations, and overcharges were associated with labelled erroneous invoices in the observed Hospital 1 results.

The remaining errors were mainly explained by four systematic failure modes:

### Service-description matching

Invoice descriptions frequently use abbreviations, shortened words, or a different word order from the contract. Conservative matching reduces false positives but can leave genuine unknown-service errors undetected.

### Unit-basis interpretation

A textual difference between the billed unit basis and contract wording does not always imply an erroneous invoice. Aggressive basis validation produced false positives during development, so uncertain mappings were retained for review.

### Interacting pricing rules

Premiums, weekend uplifts, cumulative volume discounts, bundles, caps, and exclusion rules can interact. Correctly identifying an individual rule is easier than reliably reproducing every combination and ordering of rules.

### Dates and cross-invoice context

Malformed service dates and duplicate activity across separate invoices cannot always be detected through a simple line-level price comparison. I therefore added explicit date, duplicate-invoice, cross-invoice duplicate-service, arithmetic, and invoice-total checks.

## 3. Hospital 2 and Uncertainty

Hospital 2 has no labels, so I do not report an accuracy figure for it.

Its contract parser extracted 76 service rates, 9 threshold rules, 8 weekend uplift rules, 8 volume-discount rules, 8 daily-cap rules, 3 bundle rules, and 6 exclusion rules.

The largest practical issue was service-description variation. Billing descriptions included heavily abbreviated forms such as `ADV GI PROC` and `RTN NEURO IMG INTERP`. I added general abbreviation normalisation and fuzzy service matching rather than hard-coding specific invoice IDs.

This reduced unmatched/review service lines from 12,582 initially to 619 out of 14,360 lines.

For the submitted predictions, confidence is deliberately conservative. Findings supported by deterministic rules that performed strongly on Hospital 1 receive higher confidence. Ambiguous service and unit-basis mappings receive lower confidence rather than being presented as certain conclusions.

## 4. What I Would Do With Another Week

With additional time, I would:

1. Move the normalised contract rules and invoice data into a relational database and implement more deterministic audit checks in SQL, using indexing and window functions for scalable duplicate, cumulative-volume, and cross-invoice validation.
2. Evaluate stronger semantic matching approaches, including embedding-based retrieval and relevant NVIDIA AI tooling, to improve service-name resolution beyond abbreviation rules and fuzzy string similarity.
3. Add targeted automated tests for every pricing-rule family and combinations of rules.
4. Improve confidence calibration and then extend the reusable audit pipeline to Hospitals 3–5..

## AI Tool Usage

I used ChatGPT and Cursor for implementation assistance, Python/Pandas debugging, refactoring, reasoning about contract parsing, and iteration on service-description normalisation.

I validated changes by rerunning the pipeline and measuring the resulting behaviour against the labelled Hospital 1 development set. AI-generated suggestions were treated as development assistance rather than ground truth; contract rules and measured outputs remained the basis for audit decisions.