# Lab 04 verifier proof copies

Each folder is a copy of the saved Costco run and contains the same filing texts
and facts files.

| Folder | Report change | Deterministic result |
|---|---|---|
| `COST_clean` | The 11 audited core claims, including quarterly revenue growth of 11.10% | 11 correct, 0 wrong, 0 unsupported |
| `COST_seeded_eps_error` | FY2026 diluted EPS changed from $20.76 to $21.76 | 10 correct, 1 wrong, 0 unsupported; corrected to $20.76 with tag `EarningsPerShareDiluted` |
| `COST_invented_growth_error` | Quarterly revenue growth changed to 15.10% while keeping inputs $95,723 and $86,156 | 11 correct, 1 wrong, 0 unsupported; recomputed as 11.10% |

Each folder contains `verified_report.md` and `nodes/06_verifier_output.json`.
The seeded-error table marks FY2026 diluted EPS of $21.76 as `wrong`, corrects
it to $20.76, and gives tag `EarningsPerShareDiluted`, its period, accession
number, and facts-file record.

These saved tables use the deterministic offline semantic client in
`../equity_research_team/scripts/generate_offline_proof_marks.py`. The client
accepts a semantic claim only after the code check supplies evidence. It cannot
change a code mark of `wrong` or `unsupported`.

The model-assisted `--verify-only` commands are in `../LAB04_SUBMISSION.md`.
The configured API reached the model call but returned HTTP 429
`credit_balance_exhausted` on 2026-11-05. Run those commands after API credit is
available. Each command writes to a new timestamped `verifications/` folder and
does not overwrite an earlier result.
