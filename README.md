# FIN 67110 — Mastering AI for Finance

Coursework and an AI-assisted equity-research desk for Purdue University's FIN 67110, Fall 2026.

## Secret handling

API keys and vendor credentials belong only in a local `.env` file. The repository ignores `.env`, raw licensed-vendor data, and local exports. `.env.example` contains placeholders only.

## Session 1 environment check

Create a local `.env` from `.env.example`, add your real values, and run:

```bash
python check_env.py
```

The program shows only the first four characters of the API key, followed by `...`, and the SEC user-agent contact. It uses only the Python standard library.

## Seven-step SEC desk and four research roles

Install the dependencies and put `API_KEY` and `SEC_USER_AGENT` in the local `.env` file. The complete desk runs seven deterministic SEC-data steps. It then runs four separate model roles based on Francis and Zhang (2026), Figure 1: Research Analyst, Financial Analyst, Investment Advisor, and Strategy Manager.

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
deterministic tests for the seeded diluted-EPS error, the invented revenue-growth
error, and the clean 11-claim Costco report. See
[`LAB04_SUBMISSION.md`](LAB04_SUBMISSION.md) for the rubric evidence and exact
commands. Lab 05 adds the 3 required Insight checks and a local page that streams
the fixed node order and displays the verified report.

This is a learning exercise, not financial advice.
AI assistance: OpenAI Codex, Google Antigravity, and Orca. I verified the sources myself; the judgments are mine.
Any remaining errors are my own.
