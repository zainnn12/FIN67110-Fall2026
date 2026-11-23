# MATW evidence review

Status: **AI PRE-REVIEW — NOT ANSH'S REQUIRED HUMAN REVIEW**

This review was produced from saved evidence by an AI reviewer. It does not identify Ansh, Shivani Rathi, or another student as the reviewer. It does not satisfy the pending genuine human review requirement.

## Evidence opened

- `runs/live/MATW_TEAM_WORKSHEET_FINAL/live_record.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/manifest.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/8-K_000006329626000118.txt`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/8-K_EX-99.1_000006329626000118.txt`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/MATW_LIVE_REPORT.md`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/verification_summary.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/nodes/06_verifier_output.json`
- Git commit `bda922d626e4c59cd0ba1129063360731b01e421`

## Filing metadata and time calculation

- Earnings filing: Form 8-K, accession `0000063296-26-000118`.
- SEC acceptance: November 20, 2026, 08:22:14 EST (UTC−05:00).
- First report commit: `bda922d626e4c59cd0ba1129063360731b01e421` at November 20, 2026, 22:52:13 EST (UTC−05:00).
- Deadline: November 21, 2026, 08:22:14 EST (UTC−05:00).
- Calculation: `22:52:13 − 08:22:14 = 14:29:59` on November 20, 2026.
- Margin before the 24-hour deadline: `24:00:00 − 14:29:59 = 09:30:01`.

## Results

| Check | Result | One-line reason | Evidence |
|---|---|---|---|
| Filing accession | **PASS** | The 8-K and Exhibit 99.1 manifest records both use accession `0000063296-26-000118`. | `manifest.json`; `live_record.json` |
| SEC acceptance time | **PASS** | The saved manifest and live record agree on November 20, 2026, 08:22:14 EST. | `manifest.json`; `live_record.json` |
| Commit identity and time | **PASS** | The saved record and Git metadata identify commit `bda922d626e4c59cd0ba1129063360731b01e421` at 22:52:13 EST. | `live_record.json`; Git commit metadata |
| 24-hour calculation | **PASS** | The commit occurred 14:29:59 after acceptance and 09:30:01 before the deadline. | Calculation above |
| Exhibit units and periods | **PASS** | Exhibit lines 139–141 state USD thousands and fiscal years ended September 30, 2026 and 2025. | Exhibit 99.1 lines 139–141 |
| Net-loss citation | **PASS** | The exhibit reports `(21,397)` and `(24,471)` in the 2026 and 2025 columns. | Exhibit 99.1 line 143 |
| Depreciation-and-amortization citation | **PASS** | The exhibit reports `48,568` and `71,746` in the 2026 and 2025 columns. | Exhibit 99.1 line 145 |
| Operating-cash-flow citation | **PASS** | The exhibit reports `(57,977)` and `(23,550)` in the 2026 and 2025 columns. | Exhibit 99.1 line 150 |
| Capital-expenditure citation | **PASS** | The exhibit reports property-and-equipment payments of `(18,237)` and `(35,818)`. | Exhibit 99.1 line 152 |
| Overall saved financial-claim verification | **FAIL** | The verifier is not clean: 16 claim instances are correct, 4 are wrong, and 37 are unsupported. | `verification_summary.json`; `nodes/06_verifier_output.json` |
| Verifier-total transcription | **PASS** | The MATW live report reproduces the saved totals of 16 correct, 4 wrong, and 37 unsupported. | `MATW_LIVE_REPORT.md`; `verification_summary.json` |
| Pre-reaction view | **NOT VERIFIABLE** | `view_time` is `not captured`; the saved $19.37 prior close is not evidence of a recorded pre-reaction investment view. | `live_record.json`; `worksheet_closes.json` |
| Value range and margin of safety | **NOT ASSESSABLE** | The saved worksheet does not establish aligned owner-cash-flow and diluted-share inputs and publishes no value range. | `worksheet.json`; `MATW_LIVE_REPORT.md` |

## Discrepancies and limits

- The four `wrong` and 37 `unsupported` verifier marks prevent a clean overall financial-claim result, even though the four cash-flow statement citations checked above match the exhibit.
- The recorded prior close is a market-data fact. It is not a timestamped pre-reaction view.
- This AI pre-review cannot supply Ansh's independent judgment or confirmation.

AI reviewer: OpenAI Codex
Review date: 2026-11-22
Required human reviewer: Ansh
Human confirmation: not obtained
