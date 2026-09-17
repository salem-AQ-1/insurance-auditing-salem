# AI Prompts and Development Notes

AI tools were used as development assistants during this exercise. I used ChatGPT and Cursor while iterating on the implementation.

The prompts below summarise the main prompt patterns and iterations used during development. They are included to make the AI-assisted workflow transparent.

## 1. Contract Structure and Rule Extraction

Initial prompt:

> Review the hospital contract structure and identify the billing rules that should be represented in an invoice-auditing pipeline, including service rates, unit basis, premiums, volume discounts, bundles, caps, and exclusions.

Follow-up iterations focused on translating the identified contract rules into structured Python logic rather than treating the contract text itself as a prediction.

## 2. Invoice-to-Contract Service Matching

Initial prompt:

> Help design a method to match invoice service descriptions to contract service names when the wording is abbreviated, reordered, or not an exact string match.

After observing a high number of unmatched Hospital 2 services, the prompt was refined:

> The invoice descriptions contain abbreviations such as "ADV GI PROC", "RTN NEURO IMG INTERP", and "EMER HAEM SVC". Improve the matching approach without hard-coding individual invoice IDs, while retaining uncertain matches for review.

This led to abbreviation normalisation combined with fuzzy string matching.

## 3. Audit Rule Implementation

Example prompt:

> Help implement deterministic invoice checks in Python/Pandas for expected pricing, duplicate invoice IDs, cross-invoice duplicate services, invalid service dates, line-total arithmetic, invoice-total reconciliation, daily caps, exclusion rules, and pricing differences.

The resulting logic was tested repeatedly against Hospital 1 labels.

## 4. Debugging and Iteration

Example debugging prompts included:

> Explain this Python/Pandas error and identify the smallest change needed to fix it without changing the rest of the audit logic.

> Compare the missed Hospital 1 errors by failure type and identify systematic weaknesses rather than fixing individual labelled invoices.

This was particularly useful for identifying service matching, unit-basis interpretation, arithmetic validation, and cross-invoice checks as separate failure modes.

## 5. Hospital 1 Evaluation

Prompt:

> Compare the audit predictions against the Hospital 1 ground-truth labels at invoice level. Report accuracy, detected erroneous invoices, false positives, and missed errors grouped by error category.

Hospital 1 labels were used for development and calibration only.

## 6. Hospital 2 Adaptation

Prompt:

> Adapt the existing Hospital 1 audit engine to Hospital 2 while keeping the auditing logic reusable. Account for the different prose-based contract structure and avoid assuming Hospital 1 parsing patterns will transfer directly.

Further iterations addressed Hospital 2 volume discounts, exclusions, and heavily abbreviated service descriptions.

## 7. Submission and Confidence

Prompt:

> Build the submission in the required template format. Use Hospital 1 development results to inform conservative confidence values, and do not claim an accuracy figure for unlabelled Hospital 2.

## AI Usage Boundary

AI-generated code and suggestions were not treated as authoritative contract interpretations or ground truth.

Changes were validated through program execution, inspection of extracted contract rules, and comparison with the labelled Hospital 1 development set. Uncertain mappings were retained as review cases rather than being forced into high-confidence classifications.