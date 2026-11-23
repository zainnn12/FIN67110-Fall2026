# Local webpage evidence

- Start command: `UV_CACHE_DIR=/private/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked page`
- Local URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health request: `GET /health` returned HTTP 200 with `{"status": "ok"}`. This checks the page process only. It does not show that the research desk completed.
- Command wiring: `equity_research_team/src/equity_research_team/web.py` builds the child command as the current Python executable plus `one_desk.py run <ticker>`. This is the same `one_desk.py run` command used from the terminal.

## Offline fallback-display result

- Result: **SUCCESSFUL OFFLINE FALLBACK DISPLAY PATH** for the saved NVDA and WMT runs.
- Route used: `POST /api/fallbacks` with ticker `NVDA`, then with ticker `WMT`.
- Both responses returned HTTP 202 with status `fallback`.
- The page loads the saved fallback report, deterministic fallback worksheet, fallback manifest, and sanitized saved failure reason. It does not start `one_desk.py`, access the network, or call a model.
- Required banner: **Fallback evidence — not a successful live model-assisted report**.
- The displayed metadata identifies the ticker, saved run, HTTP 429 `credit_balance_exhausted` failure reason, fallback-report path, fallback-worksheet path, and missing outputs.
- NVDA deterministic UI response: [fallback_ui_evidence.json](../lab09/DESK_2026-11-22_13-37-32-104848/fallback_ui_evidence.json).
- WMT deterministic UI response: [fallback_ui_evidence.json](../lab09/DESK_2026-11-22_13-37-44-279695/fallback_ui_evidence.json).
- Automated fallback and webpage tests: 11 targeted tests passed. The fallback test prevents subprocess execution and checks zero recorded network and model calls.
- Browser screenshot: not captured. The available browser-capture host returned `The browser access host is unavailable`. The actual loopback HTTP route and saved deterministic UI response evidence were tested instead.

This successful fallback display is not a successful joined-model display, a verified report, a recommendation, or a completed Lab 09 live run.

## Live joined-model result

- MSGR UI request: status **failed** after the `agent_team` process returned HTTP 429 `credit_balance_exhausted`. The saved event stream has no completed node sequence, report path, or report content.
- Saved UI evidence: [ui_evidence.json](../desk/DESK_2026-11-22_13-40-27-300160/ui_evidence.json); [saved failure record](../desk/DESK_2026-11-22_13-40-27-300160/failure.json).
- No final report was displayed because the command failed before it wrote a joined final report.
- Successful live model-assisted report display: **not completed**.
