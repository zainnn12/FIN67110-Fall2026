# Three Musketeers — Zainab, Ansh, Krishmi

Our client is a long-term individual investor seeking capital appreciation, with moderate risk tolerance and a preference for evidence-based recommendations supported by SEC filings and transparent valuation assumptions.

## Desk design

The local web page and terminal workflow use the same `one_desk.py` command. The pipeline uses saved files and a fixed code-defined order. A deterministic screen can select a ticker from the saved registry. The agent team saves filing-based work. The verifier and worksheet consume saved run files. A hook checks worksheet and report outputs before the final report assembler writes its report. Replay reads saved files only.

```mermaid
flowchart LR
  UI[Local web page] -->|subprocess: one_desk.py run| Desk[One-desk command]
  CLI[Terminal command] -->|one_desk.py run| Desk
  Desk -->|SCREEN path| Seeker[Seeker]
  Seeker -->|file: registry| Picker[Deterministic picker]
  Picker -->|fixed code path| Team[Agent team]
  Desk -->|ticker path, fixed code path| Team
  Team -->|saved run files| Verify[Verifier]
  Team -->|saved run files| Worksheet[Worksheet]
  Worksheet -->|validated file| Hook[Evidence hook]
  Verify -->|saved marks| Hook
  Hook -->|guarded outputs| Assembler[Final report assembler]
  Assembler -->|saved report| UI
  Desk -->|file-only replay| Replay[Replay]
```

## Joins

- The seeker joins to the deterministic picker through the saved registry file.
- The ticker or selected name joins to the agent team through a fixed code path in `one_desk.py`.
- The verifier and worksheet join to the agent run through saved files in the run folder.
- The hook joins the worksheet and verifier evidence by reading saved outputs and validating numeric claims.
- The final assembler joins the guarded outputs by reading their saved files.
- The web page joins to the desk by starting the same `one_desk.py run` command in a subprocess.
- Replay joins only to saved run files. It makes no network or model calls.

## Team-owned feature

The team owns a prospective factor-check feature. It fixes each factor’s definition, direction, weight, point rule, and evaluation window before observing returns. It records each comparison and reports a hit rate. The saved prospective sample has zero comparisons, so no factor validation is claimed.

## Team roles

- Zainab — Integration and live-record lead; connects the tools under one command and maintains the live record and submission evidence.
- Ansh — Verification and evidence lead; checks report claims against SEC filings and records the assigned review results.
- Krishmi — Seeker and valuation lead; maintains factor definitions and the spinoff screen and completes the assigned worksheet recomputations.

## Live record so far

| Ticker | Release | Filing Accepted time | View time | Commit time | 24-hour result | Permanent GitHub evidence |
|---|---|---|---|---|---|---|
| MATW | Fourth-quarter and fiscal-year 2026 earnings, period ended September 30, 2026 | November 20, 2026, 08:22:14 EST (UTC−05:00); accession `0000063296-26-000118` | Not captured; no pre-reaction view time is asserted | November 20, 2026, 22:52:13 EST (UTC−05:00); commit [`bda922d626e4c59cd0ba1129063360731b01e421`](https://github.com/zainnn12/FIN67110-Fall2026/commit/bda922d626e4c59cd0ba1129063360731b01e421) | Inside; before November 21, 2026, 08:22:14 EST | [MATW live report at the recorded commit](https://github.com/zainnn12/FIN67110-Fall2026/blob/bda922d626e4c59cd0ba1129063360731b01e421/runs/live/MATW_TEAM_WORKSHEET_FINAL/MATW_LIVE_REPORT.md) · [saved live record](runs/live/MATW_TEAM_WORKSHEET_FINAL/live_record.json) |

The MATW report records verifier marks of 16 correct, 4 wrong, and 37 unsupported. The worksheet view and value range were not computed because aligned owner-cash-flow and share inputs were unavailable. The saved MATW live report does not establish a pre-reaction view.

## Checkpoint 3 evidence

### Lab 06

- [Corrected Lab 06 run](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/seeker_report.md), [registry](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/registry.json), and [citation audit](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/citation_audit.json).
- [Zero-weight proof](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/weight_zero_proof_2026-11-20_22-49-34-990421/proof.json), [Lab 06 validation](LAB06_VALIDATION.md), and [Ansh's completed review section](02_LAB06_VALIDATION_section_COMPLETED.md). Ansh completed the independent manual review on November 22, 2026. The saved screen has no ranked name.
- Ansh marked Cortigent **FAIL** because the saved evidence contradicts the registry's October 8, 2025 record date and pending spin-off status. He marked the Octave and BioKey insider checks **NOT VERIFIABLE** and the MSG Rangers insider check **INCOMPLETE PERIOD**. His 12 PASS marks and all 8 stated limitations remain unchanged. The historical run is preserved; the separate [Cortigent correction artifact](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/CORRECTION_CORTIGENT_2026-11-22.json) clears the withdrawn record date and removes Cortigent from registered/watch eligibility.

### Lab 07

- The saved MSGR joined run’s [final report](runs/desk/DESK_2026-11-22_13-31-53-865623/final_report.md) and [manifest](runs/desk/DESK_2026-11-22_13-31-53-865623/run_manifest.json) show that the run completed. It selected Form 10-Q accession `0001628280-26-071325`, filed November 6, 2026, for the period ended September 30, 2026. The period predates the October 26, 2026 distribution.
- Krishmi’s [completed manual review](runs/lab07/KRISHMI_MANUAL_REVIEW.md) records two **FAIL** marks: the original worksheet did not compute the available owner-cash-flow value or the available low-case value per share. Her calculations, conclusions, review date of November 22, 2026, and both FAIL marks are unchanged.
- The [correction record](runs/lab07/MSGR_WORKSHEET_CORRECTION_2026-11-22.json) and corrected [worksheet](runs/desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet.md) use Form 10 accession `0001193125-26-409182` for the single matching fiscal year from July 1, 2025 through June 30, 2026. The source units are USD thousands, except shares in thousands. The inputs are pro forma net loss of −$26,801,000 at line 1791, depreciation and amortization of $2,348,000 at line 1781, capital expenditures of −$634,000 at line 5108 with its absolute value subtracted, and pro forma diluted weighted-average shares of 12,077,000 at line 1797.
- The corrected owner cash flow is −$25.087 million. The low-case equity value and value per share are $0.00. The [offline worksheet proof](runs/desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet_offline_proof.json), [hook result](runs/desk/DESK_2026-11-22_13-31-53-865623/hook_result.json), and [offline replay proof](runs/desk/DESK_2026-11-22_13-31-53-865623/replay/replay_proof.json) record zero model calls, zero network calls for regeneration and replay, a clean hook PASS, and a byte-identical replay. The pre-spin 10-Q is not annualized and is not mixed with the annual Form 10 period.

### Lab 08

- [Successful MSGR joined run](runs/desk/DESK_2026-11-22_13-31-53-865623/final_report.md) with [fixed node order](runs/desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/node_order.json), individual timings, and [manifest](runs/desk/DESK_2026-11-22_13-31-53-865623/run_manifest.json).
- [Clean hook PASS](runs/desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/clean_result.txt), [seeded-error refusal](runs/desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/seeded_result.txt), and [offline replay proof](runs/desk/DESK_2026-11-22_13-31-53-865623/replay/replay_proof.json). Replay recorded zero network calls, zero model calls, and identical report hashes and content.
- The timing-corrected [SCREEN result](runs/desk/DESK_2026-11-22_13-37-17-802277/final_report.md) has no ranked ticker. It does not select a company.

### Lab 09

- [NVDA fallback report](runs/lab09/DESK_2026-11-22_13-37-32-104848/fallback_report.md), [manifest](runs/lab09/DESK_2026-11-22_13-37-32-104848/agent/NVIDIA_CORP_2026-11-22_13-37-33-357977/manifest.json), and [failure record](runs/lab09/DESK_2026-11-22_13-37-32-104848/failure.json).
- [WMT fallback report](runs/lab09/DESK_2026-11-22_13-37-44-279695/fallback_report.md), [manifest](runs/lab09/DESK_2026-11-22_13-37-44-279695/agent/Walmart_Inc_2026-11-22_13-37-46-216137/manifest.json), and [failure record](runs/lab09/DESK_2026-11-22_13-37-44-279695/failure.json).
- Both joined runs stopped at the Investment Advisor call after HTTP 429 `credit_balance_exhausted`. Their final verified reports, worksheets, views, and deciding numbers were not produced. The [NVDA comparison](LAB09_NVDA_COMPARISON.md) records missing parts-alone and joined outputs. Manual checks remain pending.

### WRDS / CRSP

- [Eight event list](runs/wrds/costco_eight_events.csv), [saved CRSP source rows](runs/wrds/costco_crsp_daily.csv), [calculations and validation](runs/wrds/crsp_reaction.json), and [methodology and reproducible command](runs/wrds/crsp_reaction_methodology.md).
- The CRSP CIZ snapshot ends December 31, 2025. The analysis therefore does not include three 2026 SEC events.

### Local webpage

- [Local page evidence](runs/checkpoint3/LOCAL_PAGE_EVIDENCE.md) records the health response, start command, shared desk command, and failed MSGR UI request. The health response does not prove a complete desk run. No successful model-assisted report display is claimed.

## Manual reviews

- Ansh’s independent [Lab 06 validation review](LAB06_VALIDATION.md) is **COMPLETE — November 22, 2026**. Cortigent is FAIL; Octave and BioKey are NOT VERIFIABLE; MSG Rangers is INCOMPLETE PERIOD. The remaining checks keep Ansh's PASS marks and stated limitations.
- Krishmi’s independent [Lab 07 manual worksheet review](runs/lab07/KRISHMI_MANUAL_REVIEW.md) is **COMPLETE — November 22, 2026**. Both reviewed calculations remain marked FAIL because the original worksheet did not compute the available values. The corrected deterministic result is recorded separately and does not change her marks.
- The independent outside-team review is **PENDING**. No automated audit is represented as that review.
- [Test results](runs/checkpoint3/test_results.md) record the locked test suite. The [completion matrix](CHECKPOINT3_COMPLETION_MATRIX.md) records each requirement and remaining action. The [teammate evidence merge checklist](TEAMMATE_EVIDENCE_TO_MERGE.md) lists the expected files and required links.

## Disclosed limitations

- Lab 06 produced no ranked name.
- The prospective factor-check has zero comparisons.
- MSGR has no reported-after-spin TTM. The corrected worksheet therefore uses the matching annual Form 10 hierarchy level 2 basis, not the pre-spin 10-Q. Owner cash flow is −$25.087 million, and the low-case equity value and value per share are $0.00.
- NVDA and WMT joined reports did not complete after the Investment Advisor calls returned HTTP 429 `credit_balance_exhausted`.
- The local page health check passed, but no successful model-assisted webpage report display was completed.
- The independent outside-team review remains pending. Ansh's Lab 06 manual review and Krishmi's Lab 07 manual review are complete.
- The subscribed CRSP data ends December 31, 2025.
- The MATW pre-reaction view time was not captured.
- The OpenAI completion smoke request passed, but later model calls exhausted the account credit. No further model call was made for this submission update.

This page submits the Checkpoint 3 proposal and available evidence. It does not claim that every Lab 07–09 deliverable or the independent outside-team review is complete.
