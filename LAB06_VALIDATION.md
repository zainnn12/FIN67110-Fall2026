# Lab 06 evidence audit

Reviewer: **Codex evidence audit, authorized by the instructor and relayed by Zainab on November 20, 2026.**

## Original saved run

Path: `lab06_runs/SEEKER_2026-11-19_22-51-35-640553/`

| Check | Result | Saved evidence |
|---|---|---|
| Final factor file is 35% / 40% / 25% | PASS | `skills/spinoff-seeker/references/factors.json`; `manifest.json` SHA-256 matches the final factor file. |
| Report first line has run, price, and index dates | PASS | `seeker_report.md`: `Run date: 2026-11-19 | Price date: 2026-10-27 | Index date: 2026-11-19`. |
| Final line is exact | PASS | `seeker_report.md`: final line is `screens, not recommendations`. |
| Ranked in-window records | PASS, none ranked | `manifest.json` reports `ranked_count: 0`; there is no ranked list to report. |
| Registered/watch list | PASS | The report has a Registered and watch list section. |
| Dropped filer reason and supporting filing | PASS | The report has 130 dropped filers; all have a reason and supporting accession. |
| First close after distribution | PASS for all 7 saved first prices | For each price, its date is strictly later than its recorded distribution date. All are Financial Datasets regular daily closes; the reader rejects when-issued tickers. Other prices remain blank. |
| Missing facts not estimated | PASS | Missing distribution dates and prices remain null or blank and appear in the unavailable-facts section. |
| Weight-zero proof | PASS | `weight_zero_proof_2026-11-20_21-25-31-256338/proof.json`; the zero-weight factor has no points, other factors retain their points, and final factors file hashes match. |
| Parent identity extraction | FAIL | The registry stores prose fragments as parent names for Qnity Electronics, Solstice Advanced Materials, Versigent, Honeywell Aerospace, and Mobility Global. One parent is blank. The saved quotes do not establish those fragments as parent names. |
| Distribution dates | NOT KNOWN for 9 records | The corresponding Form 10 evidence did not establish a date. The registry left these blank. No date is estimated. |
| Unavailable vendor prices | NOT KNOWN for 2 tickers | Financial Datasets returned HTTP 400 for OCTLF and BKAIF; those records have no price. The saved response files are under `raw/financialdatasets/`. |

## Generic correction and rerun

The parent extractor now trims generic prose boundaries and drops unresolved parent fragments. A regression test covers these cases. The extractor tests pass. A new timestamped seeker run using refreshed SEC filing indexes is in progress. Its validation result will be added here after the run completes. This file does not mark Lab 06 complete until that audit is finished.

## Teammate-owned evidence

No teammate check is represented as performed. This file records the instructor-authorized Codex evidence audit only. Any fact that the saved filing does not establish remains unavailable.
