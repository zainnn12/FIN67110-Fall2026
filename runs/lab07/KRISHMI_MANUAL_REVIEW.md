# Krishmi manual worksheet review — MSGR (Lab 07)

Reviewer: Krishmi Appuhamilage
Review date: 2026-11-22

Worksheet reviewed: `runs/desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet.md` and `worksheet.json`
Valuation rules: `skills/spinoff-worksheet/worksheet_config.json`
- Formula: owner cash flow = after-tax earnings + depreciation and amortization − capital expenditures.
- Source hierarchy: (1) reported-after-spin TTM, (2) comparable annual pro-forma figures from the Form 10, (3) otherwise not computed.
- Low case: haircut 20%, growth 0%, required return 12%.

## Why the worksheet's 10-Q basis cannot be used

The worksheet used MSGR 10-Q `0001628280-26-071325`, which covers the three months ended September 30, 2026. The distribution date was October 26, 2026 (10-Q saved text, line 693), so that quarter is pre-spin carve-out data.
- It is one quarter, and the rules forbid annualizing a single quarter.
- No reported-after-spin TTM exists yet.
- Hierarchy level 1 is therefore not available.

## Comparable annual inputs found in the saved Form 10 (hierarchy level 2)

Source: MSGR Form 10 information statement, accession `0001193125-26-409182`, saved at `runs/lab07/MSGR_evidence/Form10_0001193125-26-409182_information.txt`.
- Period for every input: fiscal year July 1, 2025 – June 30, 2026, all from the same filing.
- Units: USD thousands, except shares in thousands.

| Input | Value | Statement and saved-text line |
|---|---|---|
| Net loss, pro forma combined | (26,801) | Unaudited pro forma combined statement of operations, line 1791 |
| Net loss, historical combined (cross-check) | (26,378) | Combined statements of operations, line 5078 |
| Depreciation and amortization (pro forma = historical) | 2,348 | Line 1781 (pro forma), line 5068 (historical) |
| Capital expenditures | (634) | Combined statements of cash flows, line 5108. The Form 10 presents no pro forma cash-flow statement, so this is the historical figure for the same fiscal year in the same filing. |
| Pro forma diluted weighted-average shares | 12,077 | Line 1797 (also line 325) |

## Calculations (my arithmetic, done by hand with a calculator)

**A. Owner cash flow (pro forma basis)**
- −26,801 + 2,348 − 634 = **−25,087** thousand
- = **−25.087** USD millions

Cross-check on the historical combined basis:
- −26,378 + 2,348 − 634 = **−24,664** thousand = **−24.664** USD millions

**B. Low-case value per share**
- Low equity value = max(0, −25.087) × 0.80 ÷ (0.12 − 0.00) = 0 × 0.80 ÷ 0.12 = **0.00** USD millions
- Diluted shares: 12,077 thousand = 12.077 million
- Low-case value per share = 0.00 ÷ 12.077 = **$0.00**

| Calculation | Inputs and sources | My arithmetic | Worksheet result | Difference | PASS/FAIL |
|---|---|---|---|---|---|
| Owner cash flow | NI (26,801), D&A 2,348, capex (634), USD thousands. Form 10 0001193125-26-409182, FY ended 2026-06-30, lines 1791 / 1781 / 5108 | −26,801 + 2,348 − 634 = −25,087 thousand = −25.087 USD millions (historical cross-check: −24.664) | Not computed ("neither reported-after-spin TTM nor comparable annual Form 10 pro-forma inputs are identified") | Worksheet gives no number; manual result is −25.087 USD millions from inputs that exist in the saved Form 10 | **FAIL**: worksheet did not compute an available value |
| Low-case value per share | Owner cash flow above; haircut 0.80; required return 0.12; growth 0; diluted shares 12.077 million (line 1797) | max(0, −25.087) × 0.80 ÷ 0.12 = 0.00 USD millions; ÷ 12.077 = $0.00 | Not computed | Worksheet gives no number; manual result is $0.00 | **FAIL**: worksheet did not compute an available value |

## Finding for the team

The worksheet says no comparable annual Form 10 inputs were identified. However, the saved Form 10 information statement contains a full fiscal-year set from one filing: net income, D&A, capital expenditures and pro forma diluted shares. Owner cash flow on that basis is negative, so the low case is floored at zero. The worksheet's selector should read this Form 10 basis (hierarchy level 2) instead of reporting "not computed."

Reviewer: Krishmi Appuhamilage, 2026-11-22. I opened the saved Form 10 and 10-Q text at the lines cited and did the arithmetic myself.
