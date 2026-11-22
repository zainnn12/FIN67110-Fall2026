# Lab 06 evidence audit

Reviewer: **Automated evidence audit, November 20, 2026.**

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

No teammate check is represented as performed. This file records an automated evidence audit. Any fact that the saved filing does not establish remains unavailable.

## Corrected evidence audit

Corrected run: `lab06_runs/SEEKER_2026-11-20_22-29-06-302032/`.

Reviewer: **Automated evidence audit, November 20, 2026.**

| Check | Result | Saved evidence |
|---|---|---|
| Final factor configuration | PASS | `skills/spinoff-seeker/references/factors.json` has 35%, 40%, and 25%; corrected run `manifest.json` records these weights and factor hash `3b81c64be6d5fdadbb4b96d8d8cda4b987c03cc401853012fb21c354b1b52007`. |
| Report date header and exact ending | PASS | Corrected `seeker_report.md` starts `Run date: 2026-11-20 | Price date: 2026-10-27 | Index date: 2026-11-20`; its final line is exactly `screens, not recommendations`. |
| Ranked names and watch list | PASS, none ranked | Corrected `manifest.json` has `ranked_count: 0`, 17 classified spinoffs, and 132 dropped records. The report lists unranked trading names, registered/watch records, and their missing inputs. No company is ranked. |
| Filing support for registry facts | PASS for 62 cited fact entries | `lab06_runs/SEEKER_2026-11-20_22-29-06-302032/citation_audit.json` records 62/62 cited quotes found in saved SEC raw filing evidence after whitespace normalization. The cited filing accession and URL are stored with each fact. The raw filing documents are retained in the corrected run folder. |
| First regular close after distribution | PASS for all 8 saved prices | Each of the 8 saved `first_price.trading_date` values is later than its recorded distribution date. The source is the Financial Datasets daily historical close. The reader excludes when-issued symbols. No price is inferred for unavailable tickers. |
| Missing distribution dates | NOT KNOWN for 7 of 17 records | The corresponding `facts.distribution_date.value` is null; `unavailable_facts` and report text state missing inputs. |
| Missing parent identity | NOT KNOWN for 2 records | Mobility Global and Enviri have no established parent value in the corrected registry. No name is inferred. Other parent names are full entity names; the former prose-fragment cases now resolve to full names or remain blank. |
| Zero-weight experiment | PASS | `weight_zero_proof_2026-11-20_22-49-34-990421/proof.json` reports `PASS`; the zero-weight factor points are disabled and the other active factor points are compared with their base-run points. The final factor file remains unchanged. |
| Dropped filings | PASS | The 132 rows in the report’s Dropped filers section each include a reason and supporting accession; see `seeker_report.md` and `registry.json`. |

### Corrections and unavailable information

The generic parent extractor now trims prose boundaries and rejects incomplete fragments. `equity_research_team/tests/test_seeker.py` contains regression coverage. The corrected run also uses refreshed SEC indexes. Solstice Advanced Materials does not appear among the corrected run’s 17 classified records; it is not silently restored from the earlier run. The earlier 18-record run remains preserved and is separately summarized in `LAB06_SPINOFF_PARTNER_TABLE.md`.

Some Financial Datasets price requests remain unavailable (including OCTLF and BKAIF). Their price fields stay blank. The first price is not a when-issued price. The 90-day factor points are missing when required distribution dates, first prices, day-20 prices, size inputs, or insider facts are missing; the rules are unchanged.

### Manual and teammate checks

No teammate or partner check is marked PASS. Checks that require another team member remain **PENDING**: (1) independent verification of two supporting filing claims, (2) independent check of the parent-asset comparison, (3) independent check of each qualifying Form 4 code-P buyer, and (4) teammate confirmation of the final registered/watch list. The automated audit above is not represented as a human review.
