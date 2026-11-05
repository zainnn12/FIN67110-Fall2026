# Lab 04 and Lab 05 — Equity Research Agent Team

This CrewAI Flow rebuilds the seven-step SEC desk as a fixed agent-team graph.
Code, not a model, selects every main node and its order:

```text
Steps → Research Analyst → Financial Analyst → Investment Advisor
      → Strategy Manager → Verifier
```

The Manager can request one correction pass. Code executes the corrections in
the fixed order Research Analyst, Financial Analyst, and Investment Advisor.
No role can make more than 2 model calls in one run. The Verifier always runs
after the Manager. There is no flag or graph branch that disables it.

## Files

- `roles/`: one instruction file for each of the 4 team roles, plus the Verifier.
- `src/equity_research_team/team_flow.py`: the fixed CrewAI Flow and Manager correction limit.
- `src/equity_research_team/verifier.py`: code checks, model semantic check, marks, and corrections.
- `tests/`: deterministic tests for the graph, call limits, clean 11 claims, seeded EPS error, and invented growth error.
- `../lab4_proofs/`: 3 copies of the saved Costco run used by the proof tests.

Each full run saves the filing texts, facts, report, verified report, node order,
and each node's JSON input and output. A full-run folder uses the company name and
date-time with microseconds. Thus, a later run cannot overwrite an earlier run.

## Exact commands

From this directory, install the packages:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache crewai install
```

Run the team on Costco with the Lab 03 close and peers:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff COST --peers WMT,TGT,BJ --price 992.13
```

Verify a saved run and run no other node:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff --verify-only ../runs/SAVED_RUN_FOLDER
```

Run all deterministic tests:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run pytest -q
```

Generate the graph without opening a browser:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run plot
```

The commands read `API_KEY` and `SEC_USER_AGENT` from `../.env`. Do not put a
secret in this project or commit a `.env` file.

## Verifier boundary

The Verifier receives only the compiled report, saved filing texts, saved facts,
and its code-check results. It does not receive the 4 role instruction files,
role prompts, role outputs, or the Investment Advisor thesis.

For each extracted report number, code checks one of these source types:

- XBRL: exact tag, accession, period, and value against `facts*.json`.
- Filing line: the cited saved line exists and contains the number after spacing
  and formatting normalization.
- Ratio: the quoted inputs recompute to the reported result within its displayed
  rounding. Ratios with an ambiguous definition must state the definition.

The model then checks whether the evidence states the number for that period and
definition. It cannot override a code mark of `wrong` or `unsupported`. The final
report marks each number `correct`, `wrong`, or `unsupported` and gives a corrected
value and real source for each rejected claim.

## Lab 05 Insight checks

Each analyst output has one structured `insight` object. Its line must start with
`Insight:`, contain a number, and cite an exact 10-K or earnings-release line. Code
fails the responsible report part when the Insight is absent, its quote is not on
the cited line, or all its numbers only repeat the earnings release's first
paragraph. The Manager can return that part once. Code then puts the Research
Insight in Overview, the Financial Insight in Valuation Insights, and the Advisor
Insight in Investment Recommendation.

The Verifier skips the Advisor thesis. It does not skip the Advisor Insight line.
Thus, all 3 Insight numbers enter the same code and model checks as other sourced
numbers. The graph order does not change.

The 3 analyst files in `roles/` must be replaced with the student's own 6-part
personas. The program supplies the Insight output contract, but it does not write
those personas.

## Page

Start the local page:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run page
```

Open `http://127.0.0.1:8000`. A user can enter a ticker, optional peers, and an
optional price. The page shows every node as it starts and shows the verified
report after the Verifier ends. The page starts the same CLI. All CLI commands
above continue to work.

This is a learning exercise, not financial advice.
