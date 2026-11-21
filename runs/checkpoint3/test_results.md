# Checkpoint 3 validation record

## Automated tests

Command:

```bash
UV_CACHE_DIR=/private/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked pytest -q equity_research_team/tests tests
```

Result: **61 passed**. This was the full test run after the final CRSP price-sign change, worksheet/hook/desk changes, and empty-screen timing regression test.

## Environment and secret handling

- `python check_env.py`: required variable names present; no values printed.
- `git check-ignore .env`: `.env` is ignored.
- `git ls-files --error-unmatch .env`: no tracked `.env`.
- Tracked-file secret-pattern scan: PASS, 0 files flagged. No key values were printed.
- Saved-artifact scan: PASS, 378 non-raw files scanned, 0 files flagged. Raw SEC and Financial Datasets payloads were excluded from the pattern scan; they contain downloaded source data, not request headers.

## Saved command proofs

- Lab 06: corrected run `lab06_runs/SEEKER_2026-11-20_22-29-06-302032`; final weights 35/40/25; 62/62 cited fact quotes found in saved filings; 8/8 saved first regular closes are after distribution; 0 ranked names; final report sentinel exact.
- Weight-zero proof: `lab06_runs/SEEKER_2026-11-20_22-29-06-302032/weight_zero_proof_2026-11-20_22-49-34-990421/proof.json`, PASS.
- Hook clean worksheet: `runs/lab07/hook_proofs/clean_result.txt`, PASS.
- Hook seeded worksheet (+$0.01): `runs/lab07/hook_proofs/seeded_result.txt`, refused at line 14.
- Hook clean final report: `runs/lab08/hook_proofs/clean_result.txt`, PASS.
- Hook seeded final report (+$0.01): `runs/lab08/hook_proofs/seeded_result.txt`, refused at line 20.
- Empty screen: `runs/desk/DESK_2026-11-20_22-55-01-801000/final_report.md`, not applicable; no ticker picked.
- Offline replay: `runs/desk/DESK_2026-11-20_22-55-01-801000/replay/replay_proof.json`, byte-identical, 0 network calls.
- WRDS: `runs/wrds/crsp_reaction.json`, PENDING WRDS LOGIN; no provider substitution.

## External failures

- A separately invoked OpenAI Verifier smoke check was saved at `runs/checkpoint3/verifier_smoke.json`; it returned 429 `credit_balance_exhausted`.
- NVDA and WMT joined-desk attempts failed at model calls with the same OpenAI quota response. Each has a `failure.json`; SEC filing bundles and independent filing audits are saved.
- MSGR agent attempt failed closed because no primary 10-K exists in its saved SEC submissions. Evidence is in `runs/desk/DESK_2026-11-20_22-53-23-552966/failure.json`.
- A second live screen attempt stopped after a premature SEC response. The failed folder and error are preserved at `runs/desk/DESK_2026-11-20_23-27-39-420799/failure.json`. The earlier successful live empty-screen output and replay proof remain intact.
