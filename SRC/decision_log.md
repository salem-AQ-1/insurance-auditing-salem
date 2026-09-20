# Decision Log

This document records the main assumptions, ambiguities, and implementation decisions made during the insurance-auditing exercise.

## 1. Scope and Sequencing

**Ambiguity / constraint:** The exercise covers four unlabelled hospitals in addition to the labelled development set, while the stated time budget is limited to 6–8 hours.

**Decision:** I used Hospital 1 as the labelled development and calibration set, then focused the scored submission on Hospital 2. Hospital 2 was selected because its prose-based contract provided a different contract-parsing and service-matching challenge from Hospital 1.

I intentionally did not attempt Hospitals 3–5 rather than producing lower-confidence predictions without sufficient validation.

## 2. Invoice Description Matching

**Ambiguity:** Hospital invoice descriptions do not consistently match the contractual service names. They frequently contain abbreviations, reordered words, and shortened terminology.

**Decision:** I normalised common abbreviations and used fuzzy matching to identify likely contractual services. I avoided hard-coding individual invoice IDs or manually mapping known errors.

Where the match remained uncertain, I retained the case for review or assigned lower confidence rather than forcing a high-confidence classification.

## 3. Unit-Basis Interpretation

**Ambiguity:** The wording of the billed unit basis does not always exactly match the terminology used in the contract.

**Decision:** I did not automatically classify every textual unit-basis difference as an error. During development on Hospital 1, this produced false positives. Clear incompatibilities were flagged, while ambiguous mappings were handled conservatively.

## 4. Contract Rule Extraction

**Ambiguity:** Hospital 2 expresses pricing rules in prose rather than in a single structured rate table. Individual services may also be affected by additional rules such as thresholds, weekend uplifts, cumulative volume discounts, daily caps, bundles, and exclusions.

**Decision:** I extracted these rules into structured representations and applied them separately from service-description matching. This made it possible to inspect the extracted rules and avoid treating raw contract text or AI interpretation as a prediction.

For Hospital 2, the parser extracted 76 service rates, 9 threshold rules, 8 weekend uplift rules, 8 volume discount rules, 8 daily cap rules, 3 bundle rules, and 6 exclusion rules.

## 5. Cumulative Volume Discounts and Rounding

**Ambiguity:** Cumulative volume discounts require both ordering utilisation over time and calculating discounted monetary values without introducing floating-point rounding differences.

**Decision:** Utilisation was processed in service-date order and accumulated by service. During final validation, I identified cases where floating-point arithmetic produced a one-penny difference in discounted unit prices.

I changed the discounted-price calculation to Decimal-based `ROUND_HALF_UP` rounding and regenerated the Hospital 2 audit and final submission. This prevented penny-level floating-point differences from being treated as pricing errors.

## 6. Cross-Invoice and Structural Checks

**Ambiguity:** Not every invoice error can be identified by comparing a single line's price with a contract rate.

**Decision:** I included additional checks for duplicate invoice IDs, potential duplicate services across invoices, contract validity, service and invoice dates, line-total arithmetic, invoice-total reconciliation, daily caps, and exclusion rules.

These checks were kept separate from service matching so that deterministic structural findings did not depend unnecessarily on fuzzy description matching.

## 7. Confidence and Uncertainty

**Ambiguity:** Hospital 2 has no ground-truth labels, so its true accuracy cannot be measured directly.

**Decision:** I do not report an accuracy estimate for Hospital 2. Confidence values are deliberately conservative: clearer deterministic findings receive higher confidence, while cases affected by uncertain service or unit-basis interpretation receive lower confidence.

Hospital 1 labels were used for development and calibration only and were not included in the scored submission.

## 8. AI Assistance

ChatGPT and Cursor were used as development assistants for contract-parsing reasoning, Python/Pandas implementation, debugging, service-description matching, and investigation of the final rounding discrepancy.

AI-generated suggestions were not treated as authoritative contract interpretations or ground truth. Changes were validated through program execution, inspection of extracted rules and intermediate outputs, and comparison with the labelled Hospital 1 development set where labels were available.
