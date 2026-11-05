# Lab 04 Submission — The Agent Team

## Framework and routing answer

Framework: **CrewAI Flows 1.15.35**.

One-line routing answer: **Code decides which node runs next. The `@start` and
`@listen` edges fix the main sequence; a model never selects a graph edge.**

The graph definition is:

```text
run_steps
  → research_analyst
  → financial_analyst
  → investment_advisor
  → strategy_manager
  → verifier
```

The Manager can report failed parts. Code groups them by responsible role and
permits 1 correction call for a role. A hard guard raises if any role would make
more than 2 calls. The correction order is fixed in code.

## Verifier boundary

The Verifier receives:

- the compiled report;
- saved filing-text excerpts and the saved filing texts in its node-input record;
- saved `facts*.json` data;
- deterministic code-check results.

The Verifier never receives:

- the Research Analyst, Financial Analyst, Investment Advisor, or Manager instructions;
- those roles' hidden prompts or intermediate outputs;
- the Investment Advisor thesis.

Giving the Verifier the role instructions would make it weaker. The instructions
could anchor it to the same assumptions that produced the report. They could also
make it check prompt compliance instead of the filing evidence. The narrower input
reduces shared failure modes and makes the filing data the deciding evidence.

## Orchestrator and evaluator

The Strategy Manager is the orchestrator-workers pattern for the one correction
pass: it identifies a failed part, and code returns that part to its responsible
role. The Manager also evaluates five-part completeness and consistency.

The Verifier is the evaluator in the evaluator-optimizer pattern. It evaluates the
compiled report independently and supplies corrections. The implementation does
not send the verified report back through an unlimited model loop; the Verifier's
correction table is the final optimized artifact.

## Required proof cases

The saved copies are:

- Clean: `lab4_proofs/COST_clean`
- Seeded diluted-EPS error: `lab4_proofs/COST_seeded_eps_error`
- Invented revenue-growth error: `lab4_proofs/COST_invented_growth_error`

Deterministic and stub-semantic test results:

| Test | Correct | Wrong | Unsupported | Required correction |
|---|---:|---:|---:|---|
| Clean 11 core claims | 11 | 0 | 0 | None |
| Seeded diluted EPS | 10 | 1 | 0 | `$21.76` → `$20.76`; tag `EarningsPerShareDiluted`; FY2026 period |
| Invented quarterly revenue growth | 11 | 1 | 0 | `15.10%` → `11.10%`; code arithmetic from `$95,723` and `$86,156` |

The offline test command reported **6 passed**. The original desk reported
**19 passed**, and the earlier focused Financial Analyst Flow reported **3 passed**.

The live `--verify-only` call reached the Verifier model. On 2026-11-05, the
configured OpenAI account returned HTTP 429 `credit_balance_exhausted`. Therefore,
the required live model semantic proof and the 2 new live COST runs still require
API credit. The code, graph, deterministic proof, and saved proof copies are ready.

## Exact commands

From `equity_research_team`:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache crewai install
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff COST --peers WMT,TGT,BJ --price 992.13
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff --verify-only ../lab4_proofs/COST_seeded_eps_error
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff --verify-only ../lab4_proofs/COST_invented_growth_error
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run kickoff --verify-only ../lab4_proofs/COST_clean
```

After API credit is available, run the team command 2 times. Confirm the printed
node order and confirm that the 2 run-folder paths differ. Then run the 3
`--verify-only` commands and have the partner check the EPS correction against the
10-K line.

## Reflection

1. In Lab 03, the Financial Analyst model could request an additional calculator
   pass. In Lab 04, code supplies all permitted arithmetic and rejects such a
   request. Code also fixes every main graph edge.
2. The Verifier cannot evaluate the Investment Advisor thesis or decide whether
   Buy, Hold, or Sell is persuasive. It skips that thesis by design. It also cannot
   validate a market price that is not present in the saved filing texts or facts.
