# Checkpoint 3 validation record

## Automated tests

Command:

```bash
UV_CACHE_DIR=/private/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked pytest -q equity_research_team/tests tests
```

Result: **67 passed**. This was the full test run after the WRDS dependency, authentication, current CRSP CIZ query, saved-evidence recalculation, worksheet/hook/desk changes, and empty-screen timing regression test.

## Environment and secret handling

- `python check_env.py`: required variable names present; no values printed.
- `WRDS_USERNAME` was loaded from the ignored worktree-root `.env` through `python-dotenv`; no value was printed or saved.
- `git check-ignore .env`: `.env` is ignored.
- `git ls-files --error-unmatch .env`: no tracked `.env`.
- Tracked-file secret-pattern scan: PASS, 0 files flagged. No key values were printed.
- Saved-artifact scan: PASS, 378 non-raw files scanned, 0 files flagged. Raw SEC and Financial Datasets payloads were excluded from the pattern scan; they contain downloaded source data, not request headers.
- Intended WRDS update scan: PASS, 12 files scanned, 0 files flagged. The ignored `.env` remained untracked and was not read into any saved artifact.

## Saved command proofs

- Lab 06: corrected run `lab06_runs/SEEKER_2026-11-20_22-29-06-302032`; final weights 35/40/25; 62/62 cited fact quotes found in saved filings; 8/8 saved first regular closes are after distribution; 0 ranked names; final report sentinel exact.
- Weight-zero proof: `lab06_runs/SEEKER_2026-11-20_22-29-06-302032/weight_zero_proof_2026-11-20_22-49-34-990421/proof.json`, PASS.
- Hook clean worksheet: `runs/lab07/hook_proofs/clean_result.txt`, PASS.
- Hook seeded worksheet (+$0.01): `runs/lab07/hook_proofs/seeded_result.txt`, refused at line 14.
- Hook clean final report: `runs/lab08/hook_proofs/clean_result.txt`, PASS.
- Hook seeded final report (+$0.01): `runs/lab08/hook_proofs/seeded_result.txt`, refused at line 20.
- Empty screen: `runs/desk/DESK_2026-11-20_22-55-01-801000/final_report.md`, not applicable; no ticker picked.
- Offline replay: `runs/desk/DESK_2026-11-20_22-55-01-801000/replay/replay_proof.json`, byte-identical, 0 network calls.
- WRDS smoke test: connected; `crsp_available` was `true`. No full library list or credential value was printed or saved.
- WRDS / CRSP run: `runs/wrds/crsp_reaction.json`, PASS. Eight unique Costco events produced eight complete reactions from 54 saved `crsp.dsf_v2` source rows. One PERMNO was present, and all event windows were inside the subscribed data range.
- Saved-evidence recalculation: PASS. The offline test independently selected the before/after closes and recalculated all eight event reactions, the mean, and the median from `runs/wrds/costco_crsp_daily.csv`.
- CRSP cutoff: the account's Costco CIZ rows run through 2025-12-31. The analysis uses the latest eight Item 2.02 filings with complete windows through that date and does not represent 2026 SEC events as analyzed.

## External failures

- A separately invoked OpenAI Verifier smoke check was saved at `runs/checkpoint3/verifier_smoke.json`; it returned 429 `credit_balance_exhausted`.
- NVDA and WMT joined-desk attempts failed at model calls with the same OpenAI quota response. Each has a `failure.json`; SEC filing bundles and independent filing audits are saved.
- MSGR agent attempt failed closed because no primary 10-K exists in its saved SEC submissions. Evidence is in `runs/desk/DESK_2026-11-20_22-53-23-552966/failure.json`.
- A second live screen attempt stopped after a premature SEC response. The failed folder and error are preserved at `runs/desk/DESK_2026-11-20_23-27-39-420799/failure.json`. The earlier successful live empty-screen output and replay proof remain intact.

## Continuation validation (2026-11-22)

- Completion smoke: PASS, `gpt-6-astra`, response status `completed`. Later NVDA, WMT, and webpage model calls returned HTTP 429 `credit_balance_exhausted` with message `You have no credits remaining`; no key or headers were saved.
- Lab 07 regression coverage: standard 10-K selection, 10-Q fallback, registration-statement rejection, and annual facts marked not established when unavailable under a 10-Q fallback.
- Full locked test suite: **72 passed**.
- The new MSGR one-desk run selected primary 10-Q accession `0001628280-26-071325`, filing date 2026-11-06, reported period ending 2026-09-30. Owner cash flow and per-share values remain not computed because the filing period precedes the distribution and aligned post-spin cash-flow and share inputs are not established.
- The MSGR Lab 08 run passed the clean hook and refused the seeded arithmetic error. Offline replay recorded zero network calls, zero model calls, and identical final-report SHA-256 hashes.
- The timing-corrected SCREEN run completed with no rankable company and saved individual part timings.
- NVDA and WMT saved filings, facts, and initial analyst outputs; both stopped at the Investment Advisor call on HTTP 429. Their joined reports remain pending.
- The local page health endpoint passed. Its valid MSGR request stopped on HTTP 429 before any node output or final report was produced.
