# Checkpoint 2 — status and handoff

## Repository evidence ready to commit

- Fixed graph: Steps → Research Analyst → Financial Analyst → Investment Advisor
  → Strategy Manager → Verifier.
- No model selects the next graph node.
- No command-line option can skip the Verifier.
- The Manager fails an analyst part when its `Insight:` line is absent or only
  restates a figure in the earnings release's first paragraph.
- The Verifier checks all 3 Insight numbers. It skips only the Advisor thesis.
- The local page accepts a ticker, optional peers, and an optional price. It
  streams node names and displays the verified report.
- The saved seeded-error proof marks FY2026 diluted EPS of $21.76 as `wrong` and
  corrects it to $20.76 with tag `EarningsPerShareDiluted`, period
  2025-09-01 to 2026-08-30, and accession 0000909832-26-000093.
- The deterministic suite passes 11 tests.

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
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run page
```

## Lab 05 student inputs

Ansh opened the cited earnings-release lines and confirmed both claims for
Microsoft and AMD. Each pair of PASS marks is recorded at the top of its own
company report. Microsoft marks apply only to Microsoft; AMD marks apply only
to AMD.

| Microsoft claim | Expected result | Source checked | Partner mark |
|---|---|---|---|
| FY27 Q1 total revenue | $92.279 billion, three months ended September 30, 2026, GAAP total revenue | Exhibit 99.1, saved lines 170–176, “Total revenue” | PASS |
| FY27 Q1 diluted EPS | $4.92 GAAP, three months ended September 30, 2026 | Exhibit 99.1, saved lines 170–172 and 190–192, “Diluted” | PASS |

| AMD claim | Expected result | Source checked | Partner mark |
|---|---|---|---|
| Q3 2026 GAAP net revenue | $13.377 billion, three months ended September 26, 2026 | Exhibit 99.1, GAAP quarterly results and income statement, “Revenue” / “Net revenue” | PASS |
| Q3 2026 GAAP diluted EPS | $1.46, three months ended September 26, 2026 | Exhibit 99.1, GAAP quarterly results, “Diluted earnings per share” | PASS |

The partner-company report is Advanced Micro Devices, Inc. (AMD). AMD reported
Q3 2026 results on November 3, 2026. The peers are NVDA, INTC, and AVGO. The
supplied closing price is $466.84 dated November 2, 2026, the final market close
before the release; source: [AMD price history](https://ir.amd.com/stock-data/price-history).
The fallback report and saved AMD filings and facts are in
`runs/ADVANCED_MICRO_DEVICES_INC_2026-11-08_16-02-23-519971/`. The report is a
fallback and not a successful live agent-team run. AMD's two teammate manual
checks are PASS, confirmed by Ansh against the cited release lines. The required
values and source references are at the top of the report. The AMD report
remains a fallback, not a successful live agent-team run.

Microsoft (MSFT), peers GOOGL, AMZN, and ORCL, and the $531.33 close dated
October 27, 2026 are earlier work. The Microsoft fallback remains saved at
`runs/MICROSOFT_CORP_2026-11-02_15-42-54/fallback_report.md`; it is not the final
partner-company report. Microsoft manual marks apply only to that report. The
team is Krishmi, Ansh, and Zainab, and its name is Three Musketeers. The three
company-neutral role files still contain the team personas. Earlier peer facts
for AMZN remain at
`runs/MICROSOFT_CORP_2026-11-08_15-44-42-604648/facts_AMZN.json` and
`facts_AMZN.csv`.

The least-trusted Insight is the Microsoft Investment Advisor's claim that
Devices and Consumer revenue decreased 3% to $15.484 billion while total
company revenue increased 19%. The reported values and periods are verifiable
against the Microsoft earnings release, but the conclusion that one quarter of
segment weakness is important enough to support a Hold recommendation requires
investor judgment. It may not show a lasting trend, and the filing cannot verify
how much weight an investor should place on it.

The Three Musketeers team starts from Zainab's agent desk. It has the fixed
graph, Verifier, three analyst personas, user interface, saved filing evidence,
seeded-error proof, and partner-company fallback report. It lacks a completed
live model-assisted partner-company run because the OpenAI API account returned
HTTP 429 `credit_balance_exhausted`. The course-approved fallback was used
instead. A later live run can be completed if API credit becomes available, but
it is not required for the current Checkpoint 2 submission.

## Draft gap-check line

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
