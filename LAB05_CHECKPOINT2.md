# Checkpoint 2 — status and handoff

## Checkpoint 2 repository evidence

- Fixed graph: Steps → Research Analyst → Financial Analyst → Investment Advisor
  → Strategy Manager → Verifier.
- No model selects the next graph node.
- No command-line option can skip the Verifier.
- The Manager fails an analyst part when its `Insight:` line is absent or only
  restates a figure in the earnings release's first paragraph.
- The Verifier checks all 3 Insight numbers. It skips only the Advisor thesis.
- The page child process adds the package `src` and workspace roots to its
  `PYTHONPATH`. A regression test proves that it can import the package from an
  unrelated working directory without relying on an installed package.
- On the requested AMD inputs, the page endpoint streamed each SEC step and the
  Research Analyst start. OpenAI returned HTTP 429
  `credit_balance_exhausted`; the page returned the saved AMD report with the
  label “Fallback — not a live agent-team run.” This was an endpoint test. The
  browser control service was unavailable, so a visible form click was not
  confirmed.
- The saved seeded-error proof marks FY2026 diluted EPS of $21.76 as `wrong` and
  corrects it to $20.76 with tag `EarningsPerShareDiluted`, period
  2025-09-01 to 2026-08-30, and accession 0000909832-26-000093.
- The latest test results are 15 agent-team tests, 19 repository tests, and 3
  financial-analyst tests passed.

Saved proof:

- `lab4_proofs/COST_seeded_eps_error/verified_report.md`
- `lab4_proofs/COST_seeded_eps_error/nodes/06_verifier_output.json`

## Exact commands

Install:

```bash
cd equity_research_team
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache crewai install
```

Run Costco with the Lab 03 price:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff COST --peers WMT,TGT,BJ --price 992.13
```

Verify one saved run and run no other node:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff --verify-only ../lab4_proofs/COST_seeded_eps_error
```

Start the page:

```bash
EQUITY_RESEARCH_PAGE_PORT=8001 UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run page
```

## Live run evidence and limits

The requested COST run used ticker COST, peers WMT,TGT,BJ, and price 992.13. It
completed SEC Steps 1–7, then stopped at Research Analyst because the API
returned HTTP 429 `credit_balance_exhausted`. Its raw process output is saved at
`runs/COSTCO_WHOLESALE_CORP_NEW_2026-11-08_17-09-39-285970/actual_run.log`.
No verified report was produced in this new run folder. The prior clean report
remains at `lab4_proofs/COST_clean/verified_report.md`; it is not the output of
the new run.

The actual node-order evidence is in the COST log above and in
`runs/ADVANCED_MICRO_DEVICES_INC_2026-11-08_17-08-36-976795/ui_evidence.json`.
Both records show SEC Steps 1–7 followed by Research Analyst. Both then record
the real API error. Strategy Manager and Verifier did not run in these attempts.
The AMD UI endpoint returned the saved fallback report, which has three lines
beginning with `Insight:` and the previously confirmed PASS/PASS marks.

Tests were run with these commands:

```bash
cd equity_research_team
.venv/bin/python -m pytest -q
# 15 passed

cd ..
equity_research_team/.venv/bin/python -m pytest -q tests
# 19 passed

cd financial_analyst_agent
.venv/bin/python -m pytest -q
# 3 passed
```

The staged changes include no `.env` file, API key, secret, temporary file, or
virtual environment.

## Lab 05 Student Inputs

### Partner company and report

The partner company is Advanced Micro Devices, Inc. (AMD). AMD reported its Q3
2026 results on November 3, 2026. The report compares AMD with NVIDIA (NVDA),
Intel (INTC), and Broadcom (AVGO). It uses the supplied closing price of $466.84
from November 2, 2026, the last close before the release. The price source is
[AMD price history](https://ir.amd.com/stock-data/price-history).

The AMD report and its saved filings and facts are in
`runs/ADVANCED_MICRO_DEVICES_INC_2026-11-08_16-02-23-519971/`. It is a
course-approved fallback report, not a successful live agent-team run. Ansh
checked both claims against AMD's Exhibit 99.1 and confirmed them: Q3 2026 GAAP
net revenue was $13.377 billion for the three months ended September 26, 2026
(PASS), and Q3 2026 GAAP diluted EPS was $1.46 for that period (PASS). These
marks appear at the top of the AMD report.

### Earlier Microsoft report

The Microsoft report is earlier work. It is saved at
`runs/MICROSOFT_CORP_2026-11-02_15-42-54/fallback_report.md`. Ansh confirmed
FY27 Q1 GAAP total revenue of $92.279 billion and GAAP diluted EPS of $4.92 for
the three months ended September 30, 2026. Both marks are PASS in the Microsoft
report. They apply only to Microsoft.

## Team and Reflection

The team is Three Musketeers: Krishmi, Ansh, and Zainab. The team starts from
Zainab's agent desk. It has the fixed graph, Verifier, three analyst personas,
user interface, saved filing evidence, seeded-error proof, and partner-company
fallback report.

The least-trusted Insight is the Microsoft Investment Advisor's claim that
Devices and Consumer revenue decreased 3% to $15.484 billion while total
company revenue increased 19%. The reported values and periods can be checked
against Microsoft's earnings release. The judgment that one quarter of segment
weakness is important enough to support a Hold recommendation is less certain.
One quarter may not establish a lasting trend. The filing cannot decide how
much weight an investor should give this result.

The OpenAI API account returned HTTP 429 `credit_balance_exhausted`. The team
did not complete a live model-assisted partner-company run. The course-approved
fallback report was used. A live run can be completed if API credit becomes
available, but it is not required for the current Checkpoint 2 submission.

## Costco report gap check

The earnings release's first paragraph does not state Costco's FY2026 diluted EPS
of $20.76; the release states that number later in its net-income paragraph and
per-share table.

## Learn-on-your-own answers

The Manager is the orchestrator-workers workflow. It checks the 5 report parts and
returns a failed part to 1 responsible role, 1 time only. The Verifier is the
evaluator-optimizer workflow. It evaluates the compiled report after the Manager.

The Verifier receives only the compiled report, saved filing texts, saved facts,
and code-check results. It does not receive the role instructions, private role
work, or the Advisor thesis. If it received the role instructions, it could judge
whether a role followed its process instead of judging the final number against
independent evidence. That shared context can make the check less independent.

For a persona, the Verifier can check the number, filing, period, quote, and line in
the Insight. A reader must judge whether the persona's criteria are useful and
whether the Insight is material. A scoring persona adds explicit measures,
thresholds, and conditions that can change its view. A descriptive role can state
facts without showing how those facts change its conclusion.
