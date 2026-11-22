# MSGR fallback report

**Status: evidence-bound fallback summary**

The joined MSGR run itself completed. Its valuation and view were not computed because the saved evidence does not establish a comparable post-distribution owner-cash-flow baseline or aligned diluted shares. This summary uses only the saved run and evidence below. It is not a recommendation.

## Filing and period

- Selected primary filing: Form 10-Q, accession `0001628280-26-071325`.
- Filing date: November 6, 2026.
- Period end: September 30, 2026.
- Distribution date: October 26, 2026.
- Selection reason in the saved manifest: first available primary 10-Q filed after the distribution date. The reported period is recorded separately.
- The filing period predates the distribution. The 10-Q is not relabeled as a 10-K.
- Annual-only facts: not established from the selected 10-Q.

Sources: [selected 10-Q](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/10-Q_000162828026071325.txt), [agent manifest](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/manifest.json), and [saved facts](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/facts.json). The filing text identifies the quarter ended September 30, 2026; see saved 10-Q lines 629–631 and 1478. The distribution date is recorded in the [corrected Lab 06 registry](../../lab06_runs/SEEKER_2026-11-20_22-29-06-302032/registry.json).

## Deterministic worksheet results

- Owner cash flow: not established; not computed.
- Diluted shares: not established.
- Low value: not established; not computed.
- Midpoint value: not established; not computed.
- View: not computed.
- Conviction: not computed.
- Last eligible price: **$254.55 per share** on November 20, 2026. Source: [saved price and volume observations](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet_closes.json), from Financial Datasets historical closes.
- Liquidity result: median daily dollar volume **$48,814,756.38** from October 27 through November 20, 2026; a $10,000 purchase is **0.02048560874124759894991408743%** of that amount. Source and arithmetic: [worksheet](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet.md) and [worksheet JSON](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet.json).

## Hook and replay evidence

- Clean hook result: **PASS** — [clean result](../desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/clean_result.txt) and [clean status](../desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/clean_status.json).
- Seeded-error refusal: **refused** the changed arithmetic claim `10001` — [refusal result](../desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/seeded_result.txt) and [seeded status](../desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/seeded_status.json).
- Offline replay: **PASS**, with zero network calls, zero model calls, and byte-identical final report hashes — [replay proof](../desk/DESK_2026-11-22_13-31-53-865623/replay/replay_proof.json).

## Saved reports

- [Worksheet](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/worksheet.md)
- [Verified agent-team report](../desk/DESK_2026-11-22_13-31-53-865623/agent/MSG_Rangers_Corp_2026-11-22_13-31-54-793145/verified_report.md)
- [Joined final report](../desk/DESK_2026-11-22_13-31-53-865623/final_report.md)
- [clean hook result](../desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/clean_result.txt) and [seeded refusal result](../desk/DESK_2026-11-22_13-31-53-865623/hook_proofs/seeded_result.txt)
- [Replay proof](../desk/DESK_2026-11-22_13-31-53-865623/replay/replay_proof.json)

**Krishmi manual review: PENDING.**
