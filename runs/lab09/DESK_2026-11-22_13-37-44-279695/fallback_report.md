Status: FALLBACK EVIDENCE REPORT — the joined model-assisted report did not complete.

# WMT (Walmart Inc.)

This fallback reports saved filing evidence and partial saved role outputs. It is not a recommendation and does not provide a view or deciding number.

## Filing evidence

- Selected primary filing: Form 10-Q, accession `0000104169-26-000154`, filed August 28, 2026, for the period ended July 31, 2026. Accepted timestamp: August 28, 2026, 16:11:28.
- Earnings release filing: Form 8-K, accession `0000104169-26-000168`, filed November 19, 2026. Accepted timestamp: November 19, 2026, 06:58:52.
- Saved filing texts read by the run: [10-Q](agent/Walmart_Inc_2026-11-22_13-37-46-216137/10-Q_000010416926000154.txt), [8-K](agent/Walmart_Inc_2026-11-22_13-37-46-216137/8-K_000010416926000168.txt), and [Exhibit 99.1 earnings release](agent/Walmart_Inc_2026-11-22_13-37-46-216137/8-K_EX-99.1_000010416926000168.txt). The [manifest](agent/Walmart_Inc_2026-11-22_13-37-46-216137/manifest.json) records the form, accession, filing date, period, and accepted times.

## Deterministic filing facts

The saved [facts JSON](agent/Walmart_Inc_2026-11-22_13-37-46-216137/facts.json) and [facts CSV](agent/Walmart_Inc_2026-11-22_13-37-46-216137/facts.csv) contain no aligned annual current/prior values. Revenue, operating income, net income, diluted EPS, equity, debt, operating cash flow, property additions, depreciation and amortization, and diluted shares are all `null` in the annual-only extractor. The saved status says those annual-only metrics are not established from the selected 10-Q. This does not mean the filing lacks quarterly facts.

## Saved partial role outputs

The Research Analyst node and Financial Analyst node completed and saved partial outputs before the Investment Advisor call failed. See the saved [Research Analyst output](agent/Walmart_Inc_2026-11-22_13-37-46-216137/nodes/02_research_analyst_output.json) and [Financial Analyst output](agent/Walmart_Inc_2026-11-22_13-37-46-216137/nodes/03_financial_analyst_output.json). These are partial model-assisted outputs, not a verified report or recommendation. The Financial Analyst output cites primary 10-Q quarterly revenue of $187,937 million versus $177,402 million, operating income of $9,383 million versus $7,286 million, and consolidated net income of $6,529 million versus $7,151 million for the quarters ended July 31, 2026 and 2025. See the saved partial output and cited 10-Q lines 1068–1086.

## Eleven filing claims and saved source lines

These claims appear in Walmart’s saved Exhibit 99.1. They are filing facts only; no recommendation is inferred.

1. Q3 revenue was $188.8 billion, up 5.2% — Exhibit 99.1 lines 7 and 11.
2. Global eCommerce sales grew 17% — line 11.
3. Walmart U.S. eCommerce grew 23% — line 11.
4. Global advertising business grew 25% — line 11.
5. Walmart U.S. advertising grew 37% — line 11.
6. Membership fee revenue grew 17% globally — line 11.
7. Gross profit rate increased 28 basis points — line 11.
8. Operating income increased $1.1 billion, or 16.0% — line 11.
9. GAAP EPS was $0.62 and adjusted EPS was $0.65 — line 7 and the definitions in lines 11–12.
10. Global inventory increased 8.1% — line 11.
11. FY2027 outlook: net sales growth of 4.9%–5.2%, adjusted operating income growth of 8.0%–8.6%, and adjusted EPS of $2.84–$2.89 — line 9.

Full cited source: [saved Exhibit 99.1](agent/Walmart_Inc_2026-11-22_13-37-46-216137/8-K_EX-99.1_000010416926000168.txt).

## Run status

- Failure point: Investment Advisor call.
- Sanitized error: HTTP 429 `credit_balance_exhausted`.
- Verified final report: not produced.
- Worksheet: not produced.
- View: not produced.
- Deciding number: not produced.
- Partner manual check: **PENDING**.

Saved failure record: [failure.json](failure.json). The model-assisted joined report did not complete. No final report, worksheet, view, or deciding number exists.
