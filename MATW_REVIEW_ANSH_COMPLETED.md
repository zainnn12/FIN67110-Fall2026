# Ansh MATW live-record manual review

Reviewer: Ansh Doshi
Review date: November 23, 2026

## Files reviewed

- `runs/live/MATW_TEAM_WORKSHEET_FINAL/MATW_LIVE_REPORT.md`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/live_record.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/manifest.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/8-K_000006329626000118.txt`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/8-K_EX-99.1_000006329626000118.txt`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/10-K_000006329625000070.txt` (line 2798)
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/worksheet_closes.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/verification_summary.json`
- `runs/live/MATW_TEAM_WORKSHEET_FINAL/nodes/06_verifier_output.json`
- `CHECKPOINT3_SUBMISSION.md` (GitHub, branch `checkpoint3-completion`, commit `8254e6e`)
- Git commit `bda922d626e4c59cd0ba1129063360731b01e421` (GitHub commit page)
- GitHub activity log for branch `checkpoint3-completion`

## Checks

| Check | Evidence inspected | Result | Explanation |
|---|---|---|---|
| Filing accession and acceptance time | `live_record.json` lines 4–5; `manifest.json` 8-K and EX-99.1 entries; 8-K lines 14–15, 60 and 67 | PASS | Form 8-K (Item 2.02), accession 0000063296-26-000118. `manifest.json` and `live_record.json` both record acceptance at 2026-11-20 08:22:14 EST (UTC−05:00). Limitation: the saved 8-K text has no SEC header, so the acceptance time is confirmed only from the saved manifest and live record, not from SEC's header text. The 8-K report date and the press release date are November 19, 2026. |
| Report commit time | GitHub commit `bda922d626e4c59cd0ba1129063360731b01e421`; `MATW_LIVE_REPORT.md` at that commit; GitHub activity log | PASS | Git commit time is 2026-11-20 22:52:13 EST, and this commit adds `MATW_LIVE_REPORT.md`. The GitHub activity log shows the branch pushed with child commit `e39959e` at 2026-11-21 03:53:12 UTC (2026-11-20 22:53:12 EST). The parent of `e39959e` is `bda922d`. A Git commit time is set by the committer's computer. The push time is set by GitHub's server and supports the commit time. |
| Within 24-hour requirement | `live_record.json` lines 5 and 9–11; times above | PASS | Deadline 2026-11-21 08:22:14 EST. Commit − acceptance = 22:52:13 − 08:22:14 = 14:29:59 (margin 09:30:01). Push − acceptance = 22:53:12 − 08:22:14 = 14:30:58 (margin 09:29:02). Limitation: the time is measured from SEC acceptance. The saved files do not show the time of day of the November 19, 2026 press release. |
| Financial claims and citations | EX-99.1 lines 138–152; `worksheet_closes.json` lines 510–513; `MATW_LIVE_REPORT.md` lines 22 and 28–30 | PASS | EX-99.1 line 139 "(In thousands)", lines 140–141 "Year Ended September 30, 2026 \| 2025", line 150 "Net cash (used in) provided by operating activities \| (57,977) \| (23,550)". These match the report's core claim. Lines 143–149 add to −57,977 (2026) and −23,550 (2025). `worksheet_closes.json` records the 2026-11-19 close as 19.37, and this is the last saved close. Liquidity: 10,000 ÷ 12,792,983.26 = 0.0782%, shown as 0.1%. The median-volume input was not separately checked. The value range and margin of safety are not computed. This PASS covers the report's core cited claims only. The full team report is not clean (see the next row). |
| Verifier totals | `verification_summary.json`; `nodes/06_verifier_output.json`; `MATW_LIVE_REPORT.md` line 14 | PASS | `verification_summary.json` and the verifier `counts` give 16 correct, 4 wrong and 37 unsupported. The `final_mark` values of the 57 claims give the same totals (16 + 4 + 37 = 57). The report states the same totals and says "This is not a clean verification." Wrong marks: N015, N050 and N054 flag "30" from "September 30" (a date-token issue). N042 flags a derived 4.53% that is not printed on cited 10-K line 2798, but the arithmetic is correct: (1,795,737 − 1,880,896) ÷ 1,880,896 = −4.53%. N049 was correct in the code check but changed to unsupported by the model check. This PASS is for the recorded totals only. The verification status is NOT CLEAN. |
| Pre-reaction investment view | `live_record.json` line 6; `MATW_LIVE_REPORT.md` line 7; `CHECKPOINT3_SUBMISSION.md` lines 54 and 117 | NOT CAPTURED | `view_time` is "not captured". The report and the Checkpoint 3 page disclose this accurately. The first saved team run was 2026-11-20 22:05:09 EST, after the November 20 market close. The $19.37 prior close is a market price, not a recorded investment view. |

## Overall conclusion

The MATW filing accession, the recorded acceptance time, the first report commit time and the 24-hour result are supported by the saved evidence, and the report was committed 14:29:59 after SEC acceptance. The report's core cited cash-flow and prior-close claims match the saved filing and price evidence, and the verifier totals of 16 correct, 4 wrong and 37 unsupported are recorded accurately, but the full team verification is not clean. No pre-reaction investment view was captured, and the report discloses this correctly.

I personally opened the listed evidence and recorded these conclusions.

Signed: Ansh Doshi
