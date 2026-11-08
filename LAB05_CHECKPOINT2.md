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

## Lab 05 student inputs still required

The following items cannot be supplied by the coding agent:

1. The student's 3 persona drafts, in the student's own words. Each draft must
   include identity; reading method; given inputs; numbered criteria with a source;
   what changes the view; and the required output ending in `Insight:`.
2. The partner's hand marks for 2 core claims, written at the top of the partner
   report.
6. The least-trusted Insight line and why, after the partner-company run exists.
7. The team member whose agent desk is the starting point and what it lacks.

The supplied Lab 05 information names Microsoft (MSFT), peers GOOGL, AMZN, and
ORCL, and a $531.33 closing price dated October 27, 2026. It names Krishmi, Ansh,
and Zainab and gives the team name Three Musketeers. A fallback report is saved
at `runs/MICROSOFT_CORP_2026-11-02_15-42-54/fallback_report.md`. Its two manual
marks remain pending until a teammate confirms them directly against the release.

The API account also needs available credit. On 2026-11-05, its live model call
returned HTTP 429 `credit_balance_exhausted`. The saved proof tables are the
offline deterministic results. Run the commands above again after credit is
available to save the model-assisted marks and the 2 required company runs.

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
