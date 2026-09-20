# Decision Log

This is a short record of the main decisions I made while working on the exercise, especially where the contract or data was not completely straightforward.

## 1. Scope

Because the exercise had a 6–8 hour time limit, I decided not to try to cover every hospital.

I used Hospital 1 to develop and test the approach because it was the only hospital with labels. After that, I focused on Hospital 2 for the submission. Its contract was quite different from Hospital 1 and was mostly written in prose, so I thought it was a good test of whether the approach could work on a different contract structure.

I left Hospitals 3–5 out rather than submit results that I had not had enough time to validate properly.

## 2. Matching invoice descriptions to contract services

One of the biggest issues was that the descriptions in the invoices often did not match the service names in the contract.

For example, descriptions could be abbreviated, shortened, or have the words in a different order.

I handled this by normalising common abbreviations and then using fuzzy matching. I did not want to hard-code specific invoice IDs just to improve the results.

If I was not confident enough about a match, I preferred to keep it as a review case or give it lower confidence instead of forcing a match.

## 3. Unit basis

I initially found that comparing the unit basis as exact text could create false positives because the invoice and contract sometimes described the same basis differently.

Because of this, I normalised the common forms and only treated clear mismatches as errors. Cases that were still ambiguous were handled more conservatively.

## 4. Hospital 2 contract rules

Hospital 2 was more difficult to parse because many of its pricing rules were written inside contract clauses rather than in a simple rate table.

I extracted the rules into structured Python logic. This included the base service rates as well as threshold rules, weekend uplifts, volume discounts, daily caps, bundles, and exclusions.

The final parser identified:

- 76 service rates
- 9 threshold rules
- 8 weekend uplift rules
- 8 volume discount rules
- 8 daily cap rules
- 3 bundle rules
- 6 exclusion rules

I kept the contract-rule extraction separate from the service matching so I could inspect both parts independently when something looked wrong.

## 5. Volume discounts and rounding

While reviewing the Hospital 2 results, I noticed that many apparent overcharges were only different by one penny per unit.

I traced this back to rounding in the volume-discount calculation. Using normal floating-point arithmetic could produce a slightly different result from the monetary rounding expected by the contract.

I changed this calculation to use `Decimal` with `ROUND_HALF_UP`, then reran the Hospital 2 audit and rebuilt the final submission.

This was an important check because I did not want small rounding differences to create a large number of false overcharge flags.

## 6. Other invoice checks

I also decided not to rely only on price comparisons because some problems can only be found by looking at the invoice structure or across multiple invoices.

I added checks for duplicate invoice IDs, possible duplicate services, invalid contracts and dates, line arithmetic, invoice-total mismatches, daily caps, and exclusion rules.

## 7. Confidence

Hospital 2 does not have labels, so I cannot measure its real accuracy and I did not want to claim one.

I used higher confidence where the result came from a clearer rule-based check, and lower confidence where service matching or unit-basis interpretation was less certain.

Hospital 1 was used to develop and measure the approach, but its invoices were not included in the final submission.

## 8. AI assistance

I used ChatGPT and Cursor throughout the exercise to help with Python/Pandas debugging, thinking through contract-parsing logic, improving the service-matching approach, and investigating issues I found while reviewing the results.

I did not treat AI output as the correct answer by default. I reran the code, checked intermediate results against the contract rules, and used the Hospital 1 labels to measure the approach where ground truth was available.
