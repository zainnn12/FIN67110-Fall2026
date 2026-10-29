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

This is a learning exercise, not financial advice.
AI assistance: OpenAI Codex, Google Antigravity, and Orca. I verified the sources myself; the judgments are mine.
Any remaining errors are my own.
