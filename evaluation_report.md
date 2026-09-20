# Evaluation Report

## 1. Approach and Measurement

I used Hospital 1 as the development and validation set because it is the only hospital with ground-truth labels. I built a rule-based auditing pipeline that reads contract rules, matches invoice descriptions to contract services, calculates expected charges, and performs additional invoice-level and cross-invoice checks.

I evaluated Hospital 1 at invoice level by comparing the audit result for each invoice with the provided labels.

The final Hospital 1 results were:

- 892 correct classifications out of 913 invoices
- 97.7% overall accuracy
- 40 of 58 labelled erroneous invoices detected
- 3 false-positive invoices

Hospital 1 was used only to develop and evaluate the approach and is not included in the scored submission.

Given the limited time, I then focused on Hospital 2 rather than attempting shallow coverage of Hospitals 2–5. Hospital 2 also provided a different challenge because its contract is more prose-based and its invoice service descriptions frequently differ from the contract wording.

## 2. Hospital 1 Performance and Error Analysis

The pipeline performed well on several rule-based checks, including duplicate invoice IDs, invalid contracts and dates, invoice-total mismatches, arithmetic errors, daily-cap checks, and pricing differences.

After comparing the missed invoices with the Hospital 1 labels, I identified four main areas where the approach could be improved:

### Service-description matching

Invoice descriptions frequently contain abbreviations, shortened words, or a different word order from the contract. This makes it difficult to reliably identify the corresponding contract service. When a match was uncertain, I preferred to leave it for review rather than force a high-confidence match.

### Unit-basis interpretation

The billed unit basis and the wording used in the contract do not always match exactly. Treating every textual difference as an error created false positives during development, so uncertain cases were handled more cautiously.

### Interacting pricing rules

Some prices depend on more than one contract rule, such as premiums, weekend uplifts, volume discounts, bundles, caps, or exclusions. These combinations are more difficult to validate than a simple comparison with a base rate.

### Dates and cross-invoice checks

Some errors require looking beyond a single invoice line. I therefore added checks for invalid dates, duplicate invoice IDs, duplicate services across invoices, arithmetic consistency, and invoice-total consistency.

## 3. Hospital 2 and Uncertainty

Hospital 2 has no provided labels, so I do not claim an accuracy figure for it.

From the Hospital 2 contract, the pipeline extracted:

- 76 service rates
- 9 threshold rules
- 8 weekend uplift rules
- 8 volume discount rules
- 8 daily cap rules
- 3 bundle rules
- 6 exclusion rules

The largest challenge was matching invoice service descriptions with the contract. Billing descriptions included heavily abbreviated forms such as `ADV GI PROC` and `RTN NEURO IMG INTERP`.

I added abbreviation normalisation and fuzzy matching to improve this process without hard-coding individual invoice IDs. After these improvements, the number of service lines requiring review decreased from 12,582 to 619 out of 14,360 lines.

During final validation, I also identified a rounding edge case in cumulative volume-discount calculations. Floating-point arithmetic could produce a one-penny difference in discounted unit prices and incorrectly classify otherwise correct lines as overcharges. I changed these calculations to Decimal-based `ROUND_HALF_UP` rounding and regenerated the audit results before producing the final submission.

For the final submission, I used higher confidence for findings supported by clearer rule-based checks and lower confidence where service or unit-basis matching remained uncertain.

## 4. What I Would Do With Another Week

With additional time, I would:

1. Move the normalised contract rules and invoice data into a relational database and implement more of the structured audit checks in SQL. Indexing and window functions could support efficient duplicate detection, cumulative-volume calculations, and cross-invoice validation at larger scale.
2. Evaluate vector-based semantic search, such as Oracle AI Vector Search, to store service embeddings and improve matching between abbreviated invoice descriptions and contract services.
3. Add automated tests for each pricing-rule type, including rounding boundaries and cases where multiple pricing rules interact.
4. Further validate the confidence scores and then extend the reusable audit pipeline to Hospitals 3–5.

## AI Tool Usage

I used ChatGPT and Cursor as development assistants for Python/Pandas debugging, code iteration, contract-parsing reasoning, and improving service-description matching.

I validated changes by rerunning the pipeline, inspecting extracted contract rules and intermediate audit outputs, and comparing the development approach with the provided Hospital 1 labels. AI-generated suggestions were treated as development assistance rather than ground truth; contractual rules and measured development results were used to evaluate audit decisions.
