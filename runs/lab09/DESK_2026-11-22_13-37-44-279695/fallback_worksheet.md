# WMT deterministic fallback worksheet

Status: **FALLBACK EVIDENCE — NOT A SUCCESSFUL LIVE MODEL-ASSISTED REPORT**

This worksheet uses only files saved in run `DESK_2026-11-22_13-37-44-279695`. It made zero network calls and zero model calls. It is not a joined worksheet, verified report, recommendation, or completed Lab 09 valuation.

## Required valuation inputs

| Input | Status | Saved evidence | Valuation use |
|---|---|---|---|
| Earnings | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 216 supports consolidated net income of $17.114 billion for nine months ended October 31, 2026. | None. The interim value is not annualized. |
| Depreciation and amortization | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 218 supports $11.763 billion for nine months ended October 31, 2026. | None. The interim value is not annualized. |
| Capital expenditures | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 230 supports property-and-equipment payments of $22.621 billion for nine months ended October 31, 2026. | None. The interim value is not annualized. |
| Diluted weighted-average shares | **UNAVAILABLE** for an annual or trailing-12-month basis | Exhibit 99.1 line 164 supports 7.952 billion shares for three months and 7.976 billion shares for nine months. | None. The interim values are not annualized. |
| Dated share price | **UNAVAILABLE** | The run did not supply or save a dated market price. | None. |

The saved annual facts JSON records each required annual metric as `null` because the selected primary filing is a Form 10-Q. That extractor result does not negate the supported interim filing facts above.

## Deterministic calculations

The saved release supports one matched nine-month diagnostic:

`$17.114 billion + $11.763 billion − $22.621 billion = $6.256 billion`

This is nine-month interim owner-cash-flow arithmetic. It is **not** an annual or trailing-12-month valuation input. It is not annualized and is not used for a value or investment view.

| Result | Value | Reason |
|---|---|---|
| Nine-month interim owner-cash-flow diagnostic | **$6.256 billion** | Direct arithmetic from matched nine-month filing values at lines 216, 218, and 230; valuation use is false. |
| Required annual or trailing-12-month owner cash flow | **NOT COMPUTABLE** | A supported annual or trailing-12-month matched basis is missing. |
| Low-case equity value | **NOT COMPUTABLE** | Required owner cash flow is not computable. |
| Low-case value per share | **NOT COMPUTABLE** | Equity value and aligned annual or trailing-12-month diluted shares are not computable. |
| Investment view | **NOT COMPUTABLE** | The Investment Advisor output was not produced, and filing facts alone do not establish the required view. |
| Conviction | **NOT COMPUTABLE** | The Investment Advisor output was not produced. |
| Deciding number | **NOT COMPUTABLE** | No joined valuation or Investment Advisor output exists. |

## Artifact boundaries

- Filing-supported facts: saved 10-Q, 8-K, Exhibit 99.1, facts files, and manifest.
- Partial unverified role output: saved Research Analyst and Financial Analyst node files.
- Deterministic calculation: the $6.256 billion nine-month diagnostic above, which is excluded from valuation.
- Missing model output: Investment Advisor, Risk Manager, Strategy Manager, and final joined report.

See `fallback_worksheet.json` for the machine-readable record and `fallback_manifest.json` for the evidence map.
