# Three Musketeers — Zainab, Ansh, Krishmi

Our client is a long-term individual investor seeking capital appreciation, with moderate risk tolerance and a preference for evidence-based recommendations supported by SEC filings and transparent valuation assumptions.

## Desk joins

```mermaid
flowchart LR
  UI[Web page] -->|UI call: ticker or screen| Desk[One-desk command]
  Desk -->|pipeline step when invoked with screen| Seeker[Seeker]
  Seeker -->|saved registry file| Picker[Deterministic picker]
  Picker -->|picked ticker; fixed code path| Team[Agent team]
  Desk -->|CLI ticker; fixed code path| Team
  Team -->|saved run files| Verifier[Verifier]
  Team -->|saved run files| Worksheet[Worksheet]
  Worksheet -->|guard join| Hook[Hook]
  Hook -->|guarded saved output| Assembler[Final report assembler]
  Assembler -->|saved final report| UI
  Team -->|read and write evidence files| Shared[Shared run folder]
  Seeker -->|read and write registry and evidence files| Shared
  Worksheet -->|read and write worksheet files| Shared
  Verifier -->|saved marks| Shared
  Factor[Factor check] -->|separate preregistered files| Shared
  Desk -->|file-only replay command| Shared
```

“The desk uses a file-based pipeline from the seeker to the deterministic pick, from the agent team’s saved run to the worksheet, and from the worksheet to the final report; the hook guards every worksheet and report output, and no model chooses the execution order or recomputes a skill’s numbers.”

The pipeline order is fixed in `one_desk.py`. The hook validates worksheet and final-report numeric claims against saved filings and computations. The web page calls the one-desk command and displays its saved final report. Replay is file-only. The factor check is a separate evaluation and does not alter production factors.

## Team-owned feature

The Three Musketeers own a factor-check feature that fixes each factor’s definition, direction, weight, point rule, and evaluation window before any return is observed, records every comparison it runs, and reports the resulting hit rate without changing the rules after seeing the outcomes.

## Roles

- Zainab — Integration and live-record lead: owns the starting agent desk, connects the team’s tools under one command, and maintains the final live record and submission evidence.
- Ansh — Verification and evidence lead: checks report claims against SEC filings, runs the clean and seeded-error verification tests, and records the resulting marks.
- Krishmi — Seeker and valuation lead: manages the factor definitions and spinoff screen, runs the investor worksheet, and documents the valuation assumptions and results.

## Live record

| Ticker | Release | Filing Accepted time and timezone | View time | Commit time | 24-hour result | Permanent run/report link |
|---|---|---|---|---|---|---|
| MATW | Fourth-quarter and fiscal-year 2026 earnings, period ended September 30, 2026 | 2026-11-20 08:22:14 EST (UTC−05:00), accession 0000063296-26-000118 | Not captured; no pre-reaction time is asserted | 2026-11-20 22:52:13 EST (UTC−05:00), commit `bda922d626e4c59cd0ba1129063360731b01e421` | Inside; before 2026-11-21 08:22:14 EST | [Live report](runs/live/MATW_TEAM_WORKSHEET_FINAL/MATW_LIVE_REPORT.md) · [Live record](runs/live/MATW_TEAM_WORKSHEET_FINAL/live_record.json) |

The live report includes the mandatory Verifier marks: 16 correct, 4 wrong, and 37 unsupported. The worksheet view is not computed because the required aligned owner-cash-flow and share inputs are unavailable. The report does not publish a value range.

## Evidence links

- Lab 06 corrected run: [seeker report](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/seeker_report.md), [registry](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/registry.json), [62-quote filing audit](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/citation_audit.json), [validation](LAB06_VALIDATION.md), [zero-weight proof](lab06_runs/SEEKER_2026-11-20_22-29-06-302032/weight_zero_proof_2026-11-20_22-49-34-990421/proof.json), [original 18-record factual table](LAB06_SPINOFF_PARTNER_TABLE.md).
- Lab 07 worksheet rules: [persona](skills/spinoff-worksheet/investor_persona.md), [configuration](skills/spinoff-worksheet/worksheet_config.json). MSGR one-desk attempts: [original saved failure](runs/desk/DESK_2026-11-20_22-53-23-552966/failure.json) and [latest filing-selection failure](runs/desk/DESK_2026-11-22_13-06-14-404940/failure.json). MSGR has a primary 10-Q but no primary 10-K in the saved submissions. The current workflow still requires a 10-K, so the required first-primary-filing 10-Q fallback is not implemented. No MSGR agent report or worksheet is represented as complete.
- MSGR saved input and worksheet status: [saved registry facts](runs/lab07/MSGR_evidence/verified_registry_facts.json), [information statement](runs/lab07/MSGR_evidence/Form10_0001193125-26-409182_information.txt), [price response](runs/lab07/MSGR_evidence/MSGR_2026-10-26_2026-11-19.json), [worksheet status](runs/lab07/MSGR_worksheet_status.md).
- Hook implementation and tests: [hook](skills/spinoff-worksheet/spinoff_worksheet_hook.py), [worksheet tests](equity_research_team/tests/test_worksheet.py), [one-desk tests](tests/test_one_desk.py). Actual clean/seeded worksheet evidence: [clean](runs/lab07/hook_proofs/clean_result.txt), [seeded](runs/lab07/hook_proofs/seeded_result.txt). Actual clean/seeded final-report evidence: [clean](runs/lab08/hook_proofs/clean_result.txt), [seeded](runs/lab08/hook_proofs/seeded_result.txt).
- Lab 08 empty-screen run: [final report](runs/desk/DESK_2026-11-20_22-55-01-801000/final_report.md), [picker](runs/desk/DESK_2026-11-20_22-55-01-801000/picker.json), [offline replay proof](runs/desk/DESK_2026-11-20_22-55-01-801000/replay/replay_proof.json). Replay is byte-identical and recorded zero network calls. A later timing-corrected live attempt stopped on a premature SEC response; its exact failure is saved at `runs/desk/DESK_2026-11-20_23-27-39-420799/failure.json`. The current timing-corrected attempt (2026-11-22) has not completed yet.
- Lab 09 filing evidence and audit: [NVDA filings](runs/lab09/NVDA_evidence/manifest.json), [NVDA audit](runs/lab09/NVDA_evidence/audit.md), [NVDA comparison](LAB09_NVDA_COMPARISON.md); [WMT filings](runs/lab09/WMT_evidence/manifest.json), [WMT audit](runs/lab09/WMT_evidence/audit.md). Attempts: [NVDA failure](runs/lab09/DESK_2026-11-20_22-59-43-273213/failure.json), [WMT failure](runs/lab09/DESK_2026-11-20_23-12-58-930177/failure.json). The latest NVDA attempt ([failure](runs/desk/DESK_2026-11-22_13-07-22-875777/failure.json)) and WMT attempt ([failure](runs/desk/DESK_2026-11-22_13-08-28-011198/failure.json)) stopped when OpenAI returned HTTP 429 `credit_balance_exhausted`; neither has a verified final report. Earlier filing bundles and independent audits remain available.
- Factor check: [preregistration and limits](runs/lab07/factor_check_plan.md), [hit-rate table](runs/factor_check/hit_rate_table.md). There are zero prospective comparisons; no validation is claimed.
- Model cutoff: [probe result and official documentation](runs/lab07/model_cutoff_probe.json). The live probe failed for lack of API credits; OpenAI's official GPT-6 Astra page documents an April 30, 2026 cutoff.
- WRDS / CRSP: [implementation](wrds_crsp_reaction.py), [eight SEC events](runs/wrds/costco_eight_events.csv), [54 CRSP source rows](runs/wrds/costco_crsp_daily.csv), [calculations and validation](runs/wrds/crsp_reaction.json), and [methodology and reproducible command](runs/wrds/crsp_reaction_methodology.md). The run uses the current CRSP CIZ `crsp.dsf_v2` table and does not substitute another data provider.
- Test proof: see exact commands below. Latest full locked run: 67 passed.
- Latest test/evidence summary: [validation record](runs/checkpoint3/test_results.md).

## Costco eight-event CRSP reaction

The account connected to WRDS and had access to the `crsp` library. The account's Costco CIZ data ends on December 31, 2025. Therefore, the analysis uses the latest eight Costco Item 2.02 8-K events with complete reaction windows in that data: March 7, 2024 through December 11, 2025. It does not use the three 2026 SEC events because the subscribed CRSP snapshot has no 2026 rows.

| SEC acceptance date | Accession | Last close before | First close after | Reaction |
|---|---|---:|---:|---:|
| 2024-03-07 | 0000909832-24-000012 | $785.59 | $725.56 | -7.6414% |
| 2024-05-30 | 0000909832-24-000026 | $815.34 | $809.89 | -0.6684% |
| 2024-09-26 | 0000909832-24-000043 | $901.44 | $885.62 | -1.7550% |
| 2024-12-12 | 0000909832-24-000075 | $988.39 | $989.35 | 0.0971% |
| 2025-03-06 | 0000909832-25-000012 | $1,026.62 | $964.31 | -6.0694% |
| 2025-05-29 | 0000909832-25-000031 | $1,008.74 | $1,040.18 | 3.1168% |
| 2025-09-25 | 0000909832-25-000093 | $943.31 | $915.95 | -2.9004% |
| 2025-12-11 | 0000909832-25-000164 | $884.48 | $884.47 | -0.0011% |

All eight reactions are complete. Two are positive. The unrounded mean is -1.977736679324163364381306051%, and the unrounded median is -1.211701313548072472846480770%. The saved JSON retains the unrounded event calculations. The methodology includes a source-price arithmetic check, and the offline test suite independently recalculates all eight rows from the saved CRSP CSV.

## Limitations and pending items

- Automated evidence audits are labeled as automated audits. No teammate or partner manual check is marked PASS. Ansh’s report checks, Krishmi’s two worksheet recomputations, and the outside-team reviewer’s manual review remain pending.
- Lab 09 uses NVDA and WMT as test companies. No outside-team student selector is documented.
- Lab 06 has no ranked names. Seven of 17 classified records have no established distribution date; eight have saved first regular closes, all after the recorded distribution date. Some prices remain unavailable.
- MSGR’s saved SEC submissions do not include a primary 10-K. The existing agent team fails closed. The minimal OpenAI model-list smoke test passed. Live role calls returned HTTP 429 `credit_balance_exhausted` with message `You have no credits remaining` (sanitized; no key or request headers were saved). This blocks the MSGR worksheet persona call and the MSGR/NVDA/WMT live agent reports. The clean and seeded hook proofs did run offline and pass/refuse as expected.
- A first live empty-screen run succeeded, but its saved timing instrumentation did not record each part separately. The timing-corrected second screen stopped on an SEC `Response ended prematurely` error. A successful empty-screen run with corrected per-part timing remains pending. The file-only replay of the earlier successful empty-screen run passed with zero network calls, zero model calls, and identical final-report content. The run proof records both counts and matching SHA-256 values.
- The subscribed Costco CRSP CIZ data ends on December 31, 2025. The completed eight-event analysis therefore excludes three later 2026 SEC earnings filings. This is a data-availability cutoff, not an authentication or coding failure.
- The MATW view time was not captured before the release. The first valid report commit was inside the 24-hour window, but it does not establish a pre-reaction view.
- Historical factor outcomes were observed before the prospective factor-check registration and are excluded. The available prospective sample has zero comparisons.
- No value range is reported where owner cash flow, shares, price, or other required inputs cannot be established.

## Reproducible commands

Run from the repository root. Put secret values in the ignored `.env`; never put them in command arguments.

```bash
uv sync --project equity_research_team --locked
python check_env.py
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked pytest -q equity_research_team/tests tests
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python skills/spinoff-seeker/scripts/seeker.py run --start-date 2025-11-18 --end-date 2026-11-20 --output-root lab06_runs
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python skills/spinoff-seeker/scripts/seeker.py prove-zero-weight --base-run lab06_runs/SEEKER_2026-11-20_22-29-06-302032
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python one_desk.py run MSGR --run-root runs/desk --registry lab06_runs/SEEKER_2026-11-20_22-29-06-302032/registry.json
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python audit_lab06_citations.py --run lab06_runs/SEEKER_2026-11-20_22-29-06-302032 --output /tmp/lab06-citation-audit.json
cp -R runs/live/MATW_TEAM_WORKSHEET_FINAL /tmp/MATW_worksheet_replay
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python skills/spinoff-worksheet/worksheet.py /tmp/MATW_worksheet_replay MATW
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python skills/spinoff-worksheet/spinoff_worksheet_hook.py runs/live/MATW_TEAM_WORKSHEET_FINAL/MATW_LIVE_REPORT.md --evidence runs/live/MATW_TEAM_WORKSHEET_FINAL
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python one_desk.py run MSGR --run-root runs/desk
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python one_desk.py run SCREEN --run-root runs/desk
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python one_desk.py run NVDA --run-root runs/lab09
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python one_desk.py run WMT --run-root runs/lab09
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python one_desk.py replay runs/desk/DESK_TIMESTAMP
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python factor_check.py hit-rate --output runs/factor_check/hit_rate_table.md
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python factor_check.py run --output runs/factor_check
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python wrds_crsp_reaction.py --smoke-test
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python wrds_crsp_reaction.py --events runs/wrds/costco_eight_events.csv --source-output runs/wrds/costco_crsp_daily.csv --output runs/wrds/crsp_reaction.json --methodology-output runs/wrds/crsp_reaction_methodology.md
cd equity_research_team && UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run page
```

This desk produces screens, not recommendations.
