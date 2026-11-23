# NVDA fallback comparison

Status: **FALLBACK COMPARISON — NOT A LIVE PARTS-ALONE OR JOINED-MODEL COMPARISON**

The Lab 09 comparison uses NVIDIA as the test company. NVIDIA’s earnings release is dated **November 17, 2026** at saved Exhibit 99.1 line 13. The SEC accepted the Form 8-K, accession `0001045810-26-000088`, on **November 17, 2026 at 16:20:51 Eastern Time**, as recorded in the saved run manifest and `runs/lab09/NVDA_evidence/manifest.json`.

The saved joined run stopped at the Investment Advisor call after HTTP 429 `credit_balance_exhausted`. A standalone parts-alone output was not run. No joined final report, verified report, joined worksheet, investment view, or deciding number was produced. The [fallback report](runs/lab09/DESK_2026-11-22_13-37-32-104848/fallback_report.md), [fallback worksheet](runs/lab09/DESK_2026-11-22_13-37-32-104848/fallback_worksheet.md), and [fallback manifest](runs/lab09/DESK_2026-11-22_13-37-32-104848/fallback_manifest.json) use saved evidence only. They document the failure boundary and do not replace the missing live outputs.

| Claim | Parts-alone output | Joined final output | Filing-supported fact | Fallback worksheet result | Difference or view | Human review |
|---|---|---|---|---|---|---|
| Total revenue $115.844 billion, up 103% year over year | **NOT PRODUCED** | **NOT PRODUCED** | Exact revenue: Exhibit 99.1 line 145. Reported 103% growth: lines 8, 14, and 21. | Filing fact supported; no valuation inference. | **NOT ASSESSABLE** | PENDING |
| Data Center revenue $107.6 billion, up 110% | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 lines 10 and 50. | Filing fact supported; no valuation inference. | **NOT ASSESSABLE** | PENDING |
| GAAP gross margin 74.8% | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 lines 14 and 22. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| GAAP operating income $77.520 billion | **NOT PRODUCED** | **NOT PRODUCED** | Exact amount: Exhibit 99.1 line 152; line 24 is the rounded $77.5 billion summary. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| GAAP net income $65.287 billion | **NOT PRODUCED** | **NOT PRODUCED** | Exact amount: Exhibit 99.1 line 156; line 25 is only the rounded $65.3 billion summary. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| GAAP diluted EPS $2.70 | **NOT PRODUCED** | **NOT PRODUCED** | Exact amount: Exhibit 99.1 line 159; lines 14 and 26 also report $2.70. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| Q4 FY2027 revenue outlook $130.0 billion, ±3% | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 line 40. | Forward-looking filing fact supported; not a reported result. | **NOT ASSESSABLE** | PENDING |
| Outlook assumes no Data Center compute revenue from China | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 line 40. | Forward-looking filing fact supported. | **NOT ASSESSABLE** | PENDING |
| Q3 return to shareholders $28.1 billion through repurchases and dividends | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 line 16. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| Board approved a $150 billion increase in repurchase authorization | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 line 16. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| Remaining repurchase authorization approximately $227.3 billion | **NOT PRODUCED** | **NOT PRODUCED** | Exhibit 99.1 line 16. | Filing fact supported. | **NOT ASSESSABLE** | PENDING |
| Required annual or TTM valuation inputs | **NOT PRODUCED** | **NOT PRODUCED** | The saved annual facts are null because the selected primary filing is a 10-Q. The release supplies interim values only. | **NOT COMPUTABLE**; exact property-only capital expenditures and a valid annual or TTM basis are unavailable. | **NOT ASSESSABLE** | PENDING |
| Investment view | **NOT PRODUCED** | **NOT PRODUCED** | Filing facts alone do not establish the required valuation view. | **NOT COMPUTABLE** | **NOT ASSESSABLE** | PENDING |
| Deciding number | **NOT PRODUCED** | **NOT PRODUCED** | No completed Investment Advisor or Strategy Manager output exists. | **NOT COMPUTABLE** | **NOT ASSESSABLE** | PENDING |

Partial Research Analyst and Financial Analyst files exist in the saved run. They are labeled partial, unverified model output. They are not used as parts-alone output, a joined final report, or a recommendation. The AI evidence audit is recorded separately in `OUTSIDE_TEAM_REVIEW.md`; genuine Ansh and outside-team student reviews remain pending.
