# FIN 67110 — Mastering AI for Finance

Coursework and an AI-assisted equity-research desk for Purdue University's FIN 67110, Fall 2026.

The desk uses a file-based pipeline from the seeker to the deterministic pick, from the agent team’s saved run to the worksheet, and from the worksheet to the final report; the hook guards every worksheet and report output, and no model chooses the execution order or recomputes a skill’s numbers.

The Three Musketeers own a factor-check feature that fixes each factor’s definition, direction, weight, point rule, and evaluation window before any return is observed, records every comparison it runs, and reports the resulting hit rate without changing the rules after seeing the outcomes.

## Checkpoint 3: one-desk run

Use Python 3.10 through 3.13. Install the locked environment:

```bash
uv sync --project equity_research_team --locked
```

Create an ignored local `.env` with `API_KEY`, `FINANCIAL_DATASETS_API_KEY`, and `SEC_USER_AGENT`. `API_KEY` is only for OpenAI model and Verifier calls. `FINANCIAL_DATASETS_API_KEY` is only for the financialdatasets.ai `X-API-KEY` header. `SEC_USER_AGENT` is only for SEC requests. Check presence without displaying values with `python check_env.py`.

Run tests without credentials or network access:

```bash
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked pytest -q equity_research_team/tests tests
```

Run the deterministic joined desk from the repository root:

```bash
uv run --project equity_research_team --locked python one_desk.py run TICKER --run-root runs/desk
uv run --project equity_research_team --locked python one_desk.py run SCREEN --run-root runs/desk
```

Each command creates one `runs/desk/DESK_<timestamp>` folder. It contains each part’s output, elapsed-time records, saved filings, the worksheet, hook results, the final report, and a manifest. A screen with no ranked name says “not applicable” and does not pick a company. A ticker outside the seeker registry has “not applicable” spinoff sections. A failed part stops the pipeline, keeps the folder, and writes the exact command error to `failure.json`.

Replay a saved run without network access:

```bash
uv run --project equity_research_team --locked python one_desk.py replay runs/desk/DESK_<timestamp>
```

Replay writes `replay/final_report.md` and `replay/replay_proof.json`, including the content comparison and network-call count. Start the Lab 05 web page with `cd equity_research_team && uv run page`. Enter a ticker or `SCREEN`; **Run joined desk** keeps the normal joined command path. For saved NVDA or WMT failures, **Open saved fallback** reads the saved fallback report and worksheet only, makes no network or model call, and displays a prominent fallback warning. A fallback is not a verified joined report or recommendation. The UI tests do not need credentials.

The join statement above describes pipeline and guard joins: the seeker writes the registry for the deterministic picker, the agent team writes its run files for the worksheet, and the assembler quotes the guarded worksheet. The factor-check feature is a separate fixed-file evaluation and never changes production factor rules.

Roles:

- Zainab — Integration and live-record lead: owns the starting agent desk, connects the team’s tools under one command, and maintains the final live record and submission evidence.
- Ansh — Verification and evidence lead: checks report claims against SEC filings, runs the clean and seeded-error verification tests, and records the resulting marks.
- Krishmi — Seeker and valuation lead: manages the factor definitions and spinoff screen, runs the investor worksheet, and documents the valuation assumptions and results.

Limitations: Lab 06 has no ranked names. The prospective factor-check has zero comparisons and does not validate the factor. The Costco WRDS / CRSP eight-event analysis is complete, but the subscribed CIZ snapshot ends on December 31, 2025 and cannot measure the three 2026 SEC events. NVDA, WMT, and webpage limitation: Completing the NVDA and WMT live joined runs and displaying a successful live joined report through the webpage requires a funded OpenAI API key. The team does not currently have access to a funded key. The available key returned HTTP 429 `credit_balance_exhausted`, so the Investment Advisor and later stages did not finish. Saved fallback reports, worksheets, and the offline webpage display document the available evidence and failure boundary, but they are not successful live joined-model outputs. The corrected MSGR worksheet uses the matching annual Form 10 basis; it does not annualize the pre-spin 10-Q. The timing-corrected SCREEN run completed with no ranked name. Ansh’s Lab 06 review and Krishmi’s two manual worksheet recomputations are complete. Ansh’s MATW review and the genuine outside-team review remain missing. MATW pre-reaction-view limitation: The team did not capture a timestamped MATW investment view before the market reaction. That evidence does not exist and cannot be recreated retroactively. No pre-reaction view is claimed. The saved record establishes only the filing time, report-commit time, and that the report was committed within 24 hours. See [Checkpoint 3 evidence](CHECKPOINT3_SUBMISSION.md).

## Secret handling

API keys and vendor credentials belong only in a local `.env` file. The repository ignores `.env`, raw licensed-vendor data, and local exports. `.env.example` contains placeholders only.

## Session 1 environment check

Create a local `.env` from `.env.example`, add your real values, and run:

```bash
python check_env.py
```

The program confirms that the required variables are present. It does not print
either API key or the SEC user-agent value. It uses only the Python standard
library.

## Seven-step SEC desk and four research roles

Install the dependencies and put `API_KEY`, `FINANCIAL_DATASETS_API_KEY`, and
`SEC_USER_AGENT` in the local `.env` file. `API_KEY` is only for OpenAI model
and Verifier calls. `FINANCIAL_DATASETS_API_KEY` is only for financial market
data from `https://api.financialdatasets.ai`. The complete desk runs seven
deterministic SEC-data steps. It then runs four separate model roles based on
Francis and Zhang (2026), Figure 1: Research Analyst, Financial Analyst,
Investment Advisor, and Strategy Manager.

Run the desk with one primary ticker, one or more peer tickers, and the current share price:

```bash
python equity_research_data.py TICKER --peers PEER1 PEER2 PEER3 --price 123.45
```

The default model is `gpt-6-astra`. To use another model that supports Structured Outputs, add `--model MODEL_NAME`.

Each role receives one JSON object with `task`, `context`, and `expected_output`. The Financial Analyst receives deterministic arithmetic from the Python calculator and can request one additional calculator pass. The Strategy Manager checks the five required report parts, returns each failing part to its responsible role no more than once, and saves `equity_research_report.md` in the timestamped run folder.

The report starts with the filings and accession numbers, followed by the run time. The program prints each role name when its model call starts and prints the final report path.

## Lab 04 fixed agent-team graph

Labs 04 and 05 are in [`equity_research_team`](equity_research_team/). It uses CrewAI
Flows to run the seven steps, the four roles, and a mandatory Verifier in a fixed
code-defined order. The Verifier supports `--verify-only` for saved runs and has
offline deterministic tests for the seeded diluted-EPS error, the invented revenue-growth
error, and the clean 11-claim Costco report. The seeded-error proof is an offline
deterministic verifier proof using saved SEC evidence; it is not a live model run. See
[`LAB04_SUBMISSION.md`](LAB04_SUBMISSION.md) for the rubric evidence and exact
commands. Lab 05 adds the 3 required Insight checks and a local page that streams
the fixed node order and displays the verified report.

The Microsoft Lab 05 fallback report is in
[`runs/MICROSOFT_CORP_2026-11-02_15-42-54/fallback_report.md`](runs/MICROSOFT_CORP_2026-11-02_15-42-54/fallback_report.md).
It is a fallback, not a live run. Ansh confirmed both Microsoft partner claim
checks as PASS: FY27 Q1 GAAP total revenue of $92.279 billion and GAAP diluted
EPS of $4.92. The Microsoft report records both marks. The UI command is
`cd equity_research_team && UV_CACHE_DIR=/tmp/equity-research-team-uv-cache uv run page`.

This is a learning exercise, not financial advice.
AI assistance: OpenAI Codex, Google Antigravity, and Orca. The Checkpoint 3 page labels automated audits and pending human checks. It does not represent automated checks as teammate review.
