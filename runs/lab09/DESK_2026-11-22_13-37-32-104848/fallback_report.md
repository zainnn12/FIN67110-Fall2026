Status: FALLBACK EVIDENCE REPORT — the joined model-assisted report did not complete.

# NVDA (NVIDIA Corporation)

This fallback reports saved filing evidence and partial saved role outputs. It is not a recommendation and does not provide a view or deciding number.

## Filing evidence

- Selected primary filing: Form 10-Q, accession `0001045810-26-000075`, filed August 26, 2026, for the period ended July 26, 2026. Accepted timestamp: August 26, 2026, 16:36:00.
- Earnings release filing: Form 8-K, accession `0001045810-26-000088`, filed November 17, 2026. Accepted timestamp: November 17, 2026, 16:20:51.
- Saved filing texts read by the run: [10-Q](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/10-Q_000104581026000075.txt), [8-K](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/8-K_000104581026000088.txt), and [Exhibit 99.1 earnings release](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/8-K_EX-99.1_000104581026000088.txt). The [manifest](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/manifest.json) records the form, accession, filing date, period, and accepted times.

## Deterministic filing facts

The saved [facts JSON](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/facts.json) and [facts CSV](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/facts.csv) contain no aligned annual current/prior values. Revenue, operating income, net income, diluted EPS, equity, debt, operating cash flow, property additions, depreciation and amortization, and diluted shares are all `null` in the annual-only extractor. The saved status says those annual-only metrics are not established from the selected 10-Q. This does not mean the filing lacks quarterly facts.

## Saved partial role outputs

The Research Analyst node and Financial Analyst node completed and saved partial outputs before the Investment Advisor call failed. See the saved [Research Analyst output](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/nodes/02_research_analyst_output.json) and [Financial Analyst output](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/nodes/03_financial_analyst_output.json). These are partial model-assisted outputs, not a verified report or recommendation. The Financial Analyst output cites primary 10-Q quarterly revenue of $96,221 million versus $46,743 million, operating income of $63,734 million versus $28,440 million, and gross profit of $72,142 million versus $33,853 million for the quarters ended July 26, 2026 and July 27, 2025. See the saved partial output and cited 10-Q lines 1391–1402.

## Eleven filing claims and saved source lines

The following claims appear in NVIDIA’s saved Exhibit 99.1. They are filing facts only; no recommendation is inferred.

1. Q3 FY2027 revenue was $115.8 billion, up 103% year over year — Exhibit 99.1 lines 8, 14, and 21.
2. Data Center revenue was $107.6 billion, up 110% year over year — lines 10 and 50.
3. GAAP gross margin was 74.8% — lines 14 and 22.
4. GAAP operating income was $77.520 billion — lines 24 and 152.
5. GAAP net income was $65.287 billion — lines 25 and 156.
6. GAAP diluted EPS was $2.70 — lines 14, 26, and 159.
7. Q4 FY2027 revenue outlook was $130.0 billion, plus or minus 3% — lines 38–40.
8. The outlook assumed no Data Center compute revenue from China — line 40.
9. Q3 shareholder returns were $28.1 billion through repurchases and dividends — line 16.
10. The board approved a $150 billion increase in repurchase authorization — line 16.
11. Remaining repurchase authorization was approximately $227.3 billion — line 16.

Full cited source: [saved Exhibit 99.1](agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/8-K_EX-99.1_000104581026000088.txt).

## Run status

- Failure point: Investment Advisor call.
- Sanitized error: HTTP 429 `credit_balance_exhausted`.
- Verified final report: not produced.
- Worksheet: not produced.
- View: not produced.
- Deciding number: not produced.
- Partner manual check: **PENDING**.

Saved failure record: [failure.json](failure.json). No final report or worksheet is represented as complete.
