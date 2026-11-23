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

## Submission evidence validation (2026-11-22)

- Full locked offline suite after the Checkpoint 3 page and fallback-report edits: **72 passed**.
- No OpenAI API request was made for this submission update.
- Credential scan over tracked submission files and the new fallback reports: PASS, zero matches.
- Unsupported-attribution scan: PASS, zero matches.
- Relative links in `CHECKPOINT3_SUBMISSION.md`: checked against repository files.
- `.env`: ignored and untracked.

## Ansh Lab 06 review merge validation (2026-11-22)

- ZIP extraction scope: only `02_LAB06_VALIDATION_section_COMPLETED.md` was extracted. Its SHA-256 is `1c212b0e116fa514bf376390708380cc4391e7226c5e8ee70a403bc37f67d38e`, identical to the ZIP entry. The evidence folder, draft file, ZIP, caches, and raw evidence were not added.
- Review merge: the section appended to `LAB06_VALIDATION.md` is byte-identical to the extracted completed section. It contains Ansh's 12 PASS marks, 2 NOT VERIFIABLE marks, 1 INCOMPLETE PERIOD mark, 1 FAIL mark, and 8 limitations without changes.
- Cortigent correction: the original saved run remains unchanged. A separate correction artifact records the withdrawn October 8, 2025 record date and the later pending merger status. The classification regression test uses the three saved Cortigent filing facts.
- Full locked offline suite: **73 passed**.
- Credential scan over tracked files and the intended untracked review and correction files: PASS, zero matching files. The scan checked AWS, OpenAI, GitHub, Slack, and private-key signatures without printing secret values.
- Placeholder-token scan over tracked document and data files and the intended untracked review and correction files: PASS, zero matching files. The scan checked the standard unresolved-work and template-marker forms.
- Unsupported-attribution scan over the submission and review documents: PASS, zero matches.
- Relative-link check over the extracted review, merged validation, completion matrix, merge checklist, and submission page: PASS, 70 links checked and zero missing.
- `.env`: ignored and untracked.

## Krishmi Lab 07 review merge and MSGR correction validation (2026-11-22)

- Manual review merge: `runs/lab07/KRISHMI_MANUAL_REVIEW.md` is byte-identical to `/Users/zfashola/Downloads/KRISHMI_MANUAL_REVIEW.md`. Both files have SHA-256 `8aeebac0e48f1072d9f746f907103d3ac09e0895b870504b1b79fc2d3915cf05`. Krishmi Appuhamilage's calculations, conclusions, review date, and two FAIL marks are unchanged.
- Form 10 regression: PASS. The saved-evidence parser selected accession `0001193125-26-409182`, period 2025-07-01 through 2026-06-30, pro forma net loss of −$26,801,000 at line 1791, depreciation and amortization of $2,348,000 at line 1781, capital expenditures of −$634,000 at line 5108, and pro forma diluted weighted-average shares of 12,077,000 at line 1797. The parser rejects a 10-Q filename and does not annualize or mix its three-month period.
- Corrected result: owner cash flow is −$25.087 million. The capital-expenditure subtraction uses the absolute value. Low-case equity value and value per share are $0.00.
- Offline worksheet proof: PASS, zero network calls and zero model calls. The original saved persona response was not replaced or regenerated through an OpenAI API call.
- Hook proof: clean corrected final report PASS. The seeded $0.01 error was refused at line 51. The hook no longer treats every source-text line number as an allowed financial amount.
- Offline replay: PASS, zero network calls, zero model calls, byte-identical content, and matching SHA-256 `b8d740c1ddeb1de30033764088910886336d5a34c89b5e9d1eb0cc29c21d5809`.
- Full locked offline suite: **76 passed**.
- Credential scan: PASS. All tracked files and every intended untracked review, correction, and proof file were checked for AWS, OpenAI, GitHub, Slack, and private-key signatures. Zero files matched, and no secret values were printed.
- Placeholder-token scan: PASS. The intended code, tests, documents, corrected run outputs, review, correction record, and proofs have zero standard unresolved-work or template-marker matches.
- Unsupported-attribution scan: PASS. The submission documents do not mark the outside-team review complete or passed, do not claim that Krishmi passed either reviewed calculation, and do not claim that her marks or conclusions were changed or upgraded.
- Relative-link check: PASS, 76 links checked and zero missing across the manual review, completion matrix, merge checklist, and submission page.
- The independent outside-team review remains pending. `.env` remains ignored and untracked.

## Lab 09 fallback, webpage, and review-evidence validation (2026-11-22)

- OpenAI API calls: **0**. No model was called. The saved HTTP 429 `credit_balance_exhausted` evidence was reused without retry.
- NVIDIA citation regression: PASS. The test fixes the November 17, 2026 release date, November 17, 2026, 16:20:51 Eastern Time acceptance, exact revenue at line 145, 103% growth at lines 8, 14, and 21, Data Center values at lines 10 and 50, and exact net income at line 156. It also checks the other saved table citations.
- NVDA fallback worksheet: PASS. Required annual or trailing-12-month valuation results are `NOT COMPUTABLE`; the combined property-and-equipment and intangible-asset line is not substituted for property-only capital expenditures.
- WMT fallback worksheet: PASS. The matched nine-month diagnostic is `17,114 + 11,763 − 22,621 = 6,256` USD million. It is marked interim, not annualized, and excluded from valuation. Required valuation results are `NOT COMPUTABLE`.
- Targeted fallback and webpage tests: **11 passed**.
- Full locked offline suite: **82 passed**.
- Local page: `GET /health` returned HTTP 200. `POST /api/fallbacks` returned HTTP 202 with status `fallback` for both NVDA and WMT. Both saved UI response artifacts record zero network calls, zero model calls, the required warning banner, the failure reason, artifact paths, missing outputs, and `live_joined_report_succeeded: false`.
- Browser capture: unavailable. The browser tool returned `The browser access host is unavailable`; no screenshot is claimed. Deterministic response evidence was saved for both fallback packages.
- Credential and secret scan: PASS. All tracked files, including the staged files, were scanned for AWS, OpenAI, GitHub, Slack, and private-key signatures. Zero files matched, and no secret values were printed.
- Placeholder/TODO scan: PASS. The high-signal unresolved-work scan found zero TODO, TBD, FIXME, XXX, template-token, or insert-marker matches. Literal `placeholder` uses are limited to intentional UI identifiers, an HTML input hint, an `.env.example` description, and preserved historical wording; none is unresolved work.
- Unsupported-attribution scan: PASS. No file attributes the AI pre-reviews to Ansh or Shivani Rathi, and no file states that human confirmation was obtained.
- Unsupported-permission scan: PASS. No tracked file claims unsupported permission, consent, authorization, or approval.
- Relative-link check: PASS, 170 relative Markdown links checked and zero missing.
- Git diff whitespace check: PASS.
- Staged-file scope: PASS. The final staged set contains 23 intended code, test, fallback, review, validation-record, and submission-document files. It contains no `.env`, key, ZIP, cache, raw evidence, downloaded package, `.pyc`, or unrelated untracked file.
- Human limits: Ansh’s MATW review, the genuine outside-team student review, the MATW pre-reaction view, both live Lab 09 joined outputs, and successful live joined-model webpage display remain missing.
