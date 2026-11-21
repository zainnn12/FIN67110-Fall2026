---
name: spinoff-seeker
description: Find U.S. spinoffs from SEC EDGAR Form 10 filings, keep filing-level provenance, read official daily closes, and rank only names that satisfy the repository's declared factor and window rules. Use for Lab 06 seeker runs, replays, and weight-zero proofs; do not use it to select the Lab 07 company.
---

# Spinoff Seeker

Run the deterministic scripts in this skill. Do not ask a model to extract,
estimate, score, rank, or repair a missing fact.

## Required inputs

- Read [references/team_inputs.json](references/team_inputs.json) before a run.
- Read [references/factors.json](references/factors.json). It is the final
  35%/40%/25% configuration. Do not edit it during a proof run.
- Read `SEC_USER_AGENT` from the repository-root `.env`. Send it on every SEC
  request. Never print the value.
- Read the financial market-data key only from `FINANCIAL_DATASETS_API_KEY` in
  the repository-root `.env`. Send it only to `https://api.financialdatasets.ai`
  as the `X-API-KEY` header. Never print the value and never send it to OpenAI.
- Keep the funded OpenAI key in `API_KEY`. Use it only for model and Verifier
  calls.
- Use `2025-11-18` unless the user gives a different start date.

## Run

From the repository root:

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache equity_research_team/.venv/bin/python skills/spinoff-seeker/scripts/seeker.py run --start-date 2025-11-18
```

The command reads EDGAR form indexes, Form 10 registrations and amendments,
CERT filings, distribution 8-Ks, parent filings, trading-proof filings, and
qualifying Form 4 purchases. It saves a timestamped folder under
`lab06_runs/`. It also saves the normalized evaluation inputs needed for an
offline replay.

## Weight-zero proof

Run the proof on the normal run's saved evaluation inputs. This uses the
separate proof-only configuration. It does not change the final factor file.

```bash
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache equity_research_team/.venv/bin/python skills/spinoff-seeker/scripts/seeker.py prove-zero-weight --base-run lab06_runs/SEEKER_RUN_FOLDER
```

The proof must fail unless the zero-weight factor has no displayed points or
score contribution for every name and every other factor's points are
unchanged.

## Tests

```bash
cd equity_research_team
UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run pytest -q tests/test_seeker.py tests/test_web.py
```

The tests use made-up companies and block live network access. Change a rule
only after its fabricated-data test changes.

## Non-negotiable boundaries

- Keep a missing fact blank. State the missing fact and the unranked reason.
- Never estimate a fact, date, filing value, price, or ticker.
- Never use a close dated on or before the distribution date. Never use a
  when-issued ticker or when-issued price.
- Read the parent's filings by the parent CIK recorded in the registry.
- A later Form 10 or amendment that proves a parent distribution overrides an
  earlier exclusion.
- Rank only a trading name inside the configured 90-calendar-day window when
  every active factor has the required input.
- Put the run date, price date, and index date on report line 1.
- End every report with exactly `screens, not recommendations`.
- Do not select a Lab 07 partner company. Show the ranked in-window names and
  stop.

