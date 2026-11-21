Filings read: 10-K (accession 0000063296-25-000070); 10-Q (accession 0000063296-26-000076); 8-K (accession 0000063296-26-000118); 8-K_EX-99.1 (accession 0000063296-26-000118)

## Live record

- Filing Accepted: 2026-11-20 08:22:14 EST (UTC−05:00), accession 0000063296-26-000118.
- First saved agent-team run: 2026-11-20T22:05:09-05:00. This was after the November 20 market close.
- Pre-reaction view time: not captured. No pre-reaction view can be asserted from these files.
- First report commit: `bda922d626e4c59cd0ba1129063360731b01e421` at 2026-11-20 22:52:13 EST (UTC−05:00).
- Twenty-four-hour result: **inside the window**. The first report commit was before 2026-11-21 08:22:14 EST.
- Twenty-four-hour deadline: 2026-11-21 08:22:14 EST.

## Team and verifier evidence

The mandatory team Verifier ran and saved `verified_report.md` and `nodes/06_verifier_output.json`. The Verifier counted 16 correct, 4 wrong, and 37 unsupported claim instances. This is not a clean verification. The full team report and every Verifier mark are preserved beside this file. The final claims below use only the filing-supported numbers stated in the evidence audit.

## Worksheet view

The view is **Not computed**. The saved facts do not establish a valid reported-after-spin trailing-twelve-month basis or a comparable annual Form 10 pro-forma basis. The worksheet leaves owner cash flow, diluted shares, and both per-share values unknown. It does not publish a value range.

The last saved regular close before the release date was $19.38 per share on 2026-11-19. This is a saved prior close, not a post-release reaction price.

Liquidity: $10,000 purchase / 12,792,983.26 median daily dollar volume = 0.1%; dates: 2026-07-23 to 2026-11-19.

## Core claim evidence audit

Codex evidence audit, authorized by the instructor and relayed by Zainab on November 20, 2026.

- **PASS:** The earnings release states operating cash flow of (57,977) and (23,550), in thousands, in the fiscal 2026 and fiscal 2025 columns. Exhibit 99.1 lines 139–141 identify units and column periods; line 150 gives the row. No conversion is used in this claim.
- **PASS:** The saved financial-datasets daily-close response records the November 19 close of $19.37 for MATW. This predates the filing acceptance and is the last eligible close saved before the release. Source: `worksheet_closes.json`.
- **NOT COMPUTED:** The value range and margin of safety. The required valid base cash flow and share inputs are not established by the source hierarchy.

## Preserved artifacts

- Verified team report: `verified_report.md`
- Worksheet: `worksheet.md`
- Hook result: PASS at generation time; the same hook must be rerun after the commit-time update.
- SEC manifest and source documents: `manifest.json`, `10-K_*.txt`, `10-Q_*.txt`, `8-K_*.txt`, and `8-K_EX-99.1_*.txt`.
- Saved closing prices and volumes: `worksheet_closes.json`. The normalized dated data, rather than the raw provider response, is preserved.
