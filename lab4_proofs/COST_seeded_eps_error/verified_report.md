Filings read: 10-K (accession 0000909832-26-000093); 10-Q (accession 0000909832-26-000051); 8-K Item 2.02 and Exhibit 99.1 (accession 0000909832-26-000084)

## Verification marks

The Verifier skipped the Investment Advisor thesis but checked its Insight line. The mark combines the code check and the model check.

| ID | Reported claim | Code check | Model check | Mark | Correction and real source |
|---|---|---|---|---|---|
| N001 | 1. FY2026 total revenue was $303,154 million. [reported: $303,154 million] | The value, tag, accession, and period match the saved fact. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — facts.json: tag RevenueFromContractWithCustomerExcludingAssessedTax; value 303154000000 USD; period 2025-09-01 to 2026-08-30; accession 0000909832-26-000093 |
| N002 | 2. Revenue growth was ($303,154 - $275,235) / $275,235 = 10.14%. [reported: 10.14%] | The code recomputation agrees within displayed rounding. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — Recomputed in code: $303,154 - $275,235) / $275,235 = 0.1014369538757788798662960743 |
| N003 | 3. Operating margin was $11,685 / $303,154 = 3.85%. [reported: 3.85%] | The code recomputation agrees within displayed rounding. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — Recomputed in code: $11,685 / $303,154 = 0.03854476602650797944279145253 |
| N004 | 4. FY2026 net income was $9,226 million. [reported: $9,226 million] | The value, tag, accession, and period match the saved fact. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — facts.json: tag NetIncomeLoss; value 9226000000 USD; period 2025-09-01 to 2026-08-30; accession 0000909832-26-000093 |
| N005 | 5. FY2026 diluted EPS was $21.76. [reported: $21.76] | The cited tag and period contain a different value. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | wrong | $20.76 — facts.json: tag EarningsPerShareDiluted; value 20.76 USD/shares; period 2025-09-01 to 2026-08-30; accession 0000909832-26-000093 |
| N006 | 6. Return on average equity is defined as net income divided by average beginning and ending equity: $9,226 / (($35,803 + $29,164) / 2) = 28.40%. [reported: 28.40%] | The code recomputation agrees within displayed rounding. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — Recomputed in code: $9,226 / (($35,803 + $29,164) / 2) = 0.2840211184139640124986531624 |
| N007 | 7. Debt to equity is defined as current plus noncurrent long-term debt divided by total equity: ($3,914 + $2,248) / $35,803 = 0.1721x. [reported: 0.1721x] | The code recomputation agrees within displayed rounding. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — Recomputed in code: $3,914 + $2,248) / $35,803 = 0.1721084825293969779068793118 |
| N008 | 8. Free cash flow is defined here as cash from operations less property additions: $15,817 - $6,435 = $9,382 million. [reported: $9,382 million] | The code recomputation agrees within displayed rounding. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — Recomputed in code: $15,817 - $6,435 = 9382 |
| N009 | 9. For the 16 weeks ended 2026-08-30, quarterly total revenue was $95,723 million. [reported: $95,723 million] | The number appears on the cited saved line after spacing and formatting normalization. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — 8-K_000090983226000084.txt, lines 39-39: Indicate by check mark whether the registrant is an emerging growth company as defined in Rule 405 of the Securities Act of 1933 (17 CFR §230.405) or Rule 12b-2 of the Securities Exchange Act of 1934 (17 CFR §240.12b-2). 8-K_EX-99.1_000090983226000084.txt, lines 39-39: Total revenue \| 95,723 \| 86,156 \| 303,154 \| 275,235 |
| N010 | 10. Quarterly revenue growth was ($95,723 - $86,156) / $86,156 = 11.10%. [reported: 11.10%] | The code recomputation agrees within displayed rounding. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — Recomputed in code: $95,723 - $86,156) / $86,156 = 0.1110427596452945819211662566 |
| N011 | 11. For the 16 weeks ended 2026-08-30, quarterly diluted EPS was $6.75. [reported: $6.75] | The number appears on the cited saved line after spacing and formatting normalization. | Offline proof: the deterministic evidence supplied the cited value, period, and definition. | correct | No correction required. — 8-K_000090983226000084.txt, lines 52-52: Fourth quarter fiscal 2026 supplemental information. 8-K_EX-99.1_000090983226000084.txt, lines 52-52: Diluted \| $ \| 6.75 \| $ \| 5.87 \| $ \| 20.76 \| $ \| 18.21 |

---
Run time: 2026-11-05T12:00:00-05:00

# Costco Core-Claim Verification Report

## Overview

1. FY2026 total revenue was $303,154 million. [10-K accession 0000909832-26-000093, line 1281; tag `RevenueFromContractWithCustomerExcludingAssessedTax`; period 2025-09-01 to 2026-08-30.]

2. Revenue growth was ($303,154 - $275,235) / $275,235 = 10.14%. [10-K accession 0000909832-26-000093, line 1281; period 2025-09-01 to 2026-08-30 and 2024-09-02 to 2025-08-31.]

3. Operating margin was $11,685 / $303,154 = 3.85%. [10-K accession 0000909832-26-000093, lines 1281 and 1285; period 2025-09-01 to 2026-08-30.]

4. FY2026 net income was $9,226 million. [10-K accession 0000909832-26-000093, line 1291; tag `NetIncomeLoss`; period 2025-09-01 to 2026-08-30.]

5. FY2026 diluted EPS was $21.76. [10-K accession 0000909832-26-000093, line 1294; tag `EarningsPerShareDiluted`; period 2025-09-01 to 2026-08-30.]

6. Return on average equity is defined as net income divided by average beginning and ending equity: $9,226 / (($35,803 + $29,164) / 2) = 28.40%. [10-K accession 0000909832-26-000093, lines 1291 and 1350; period 2025-09-01 to 2026-08-30; equity dates 2026-08-30 and 2025-08-31.]

7. Debt to equity is defined as current plus noncurrent long-term debt divided by total equity: ($3,914 + $2,248) / $35,803 = 0.1721x. [10-K accession 0000909832-26-000093, lines 1335, 1339, and 1350; period 2026-08-30.]

8. Free cash flow is defined here as cash from operations less property additions: $15,817 - $6,435 = $9,382 million. [10-K accession 0000909832-26-000093, lines 1402 and 1404; period 2025-09-01 to 2026-08-30.]

## Market Positioning and Growth Outlook

9. For the 16 weeks ended 2026-08-30, quarterly total revenue was $95,723 million. [Earnings release, accession 0000909832-26-000084, line 39; period 16 weeks ended 2026-08-30.]

10. Quarterly revenue growth was ($95,723 - $86,156) / $86,156 = 11.10%. [Earnings release, accession 0000909832-26-000084, line 39; periods 16 weeks ended 2026-08-30 and 2025-08-31.]

11. For the 16 weeks ended 2026-08-30, quarterly diluted EPS was $6.75. [Earnings release, accession 0000909832-26-000084, line 52; period 16 weeks ended 2026-08-30.]

## Valuation Insights

The 11 numeric claims above are the Lab 03 core claims. Each claim has its direct filing line or XBRL source and period.

## Future Developments and Strategic Recommendations

No additional numeric claim is added in this proof copy.

## Investment Recommendation

The Verifier skips this Investment Advisor thesis by design.
