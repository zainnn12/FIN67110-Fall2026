# NVDA deterministic fallback worksheet

Status: **FALLBACK EVIDENCE — NOT A SUCCESSFUL LIVE MODEL-ASSISTED REPORT**

This worksheet uses only files saved in run `DESK_2026-11-22_13-37-32-104848`. It made zero network calls and zero model calls. It is not a joined worksheet, verified report, recommendation, or completed Lab 09 valuation.

## Required valuation inputs

| Input | Status | Saved evidence | Valuation use |
|---|---|---|---|
| Earnings | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 156 supports GAAP net income of $65.287 billion for the three months ended October 25, 2026. | None. The interim value is not annualized. |
| Depreciation and amortization | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 210 supports $1.254 billion for three months and $3.378 billion for nine months. | None. The interim values are not annualized. |
| Capital expenditures | **UNSUPPORTED** as property-only capital expenditures | Exhibit 99.1 line 228 combines purchases of property and equipment with intangible assets: $4.422 billion for three months and $8.856 billion for nine months. The saved filing does not separate the required property-only amount on that line. | None. The combined amount is not substituted for property-only capital expenditures. |
| Diluted weighted-average shares | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 162 supports 24.186 billion shares for three months and 24.287 billion shares for nine months. | None. The interim values are not annualized. |
| Dated share price | **UNAVAILABLE** | The run did not supply or save a dated market price. | None. |

The saved annual facts JSON records each required annual metric as `null` because the selected primary filing is a Form 10-Q. That extractor result does not negate the supported interim filing facts above.

## Deterministic results

| Result | Value | Reason |
|---|---|---|
| Owner cash flow | **NOT COMPUTABLE** | A matched annual or trailing-12-month basis and property-only capital expenditures are missing. |
| Low-case equity value | **NOT COMPUTABLE** | Owner cash flow is not computable. |
| Low-case value per share | **NOT COMPUTABLE** | Equity value and aligned diluted shares are not computable. |
| Investment view | **NOT COMPUTABLE** | The Investment Advisor output was not produced, and filing facts alone do not establish the required view. |
| Conviction | **NOT COMPUTABLE** | The Investment Advisor output was not produced. |
| Deciding number | **NOT COMPUTABLE** | No joined valuation or Investment Advisor output exists. |

## Artifact boundaries

- Filing-supported facts: saved 10-Q, 8-K, Exhibit 99.1, facts files, and manifest.
- Partial unverified role output: saved Research Analyst and Financial Analyst node files.
- Deterministic calculation: no owner-cash-flow valuation calculation is possible from the supported matching inputs.
- Missing model output: Investment Advisor, Risk Manager, Strategy Manager, and final joined report.

See `fallback_worksheet.json` for the machine-readable record and `fallback_manifest.json` for the evidence map.
