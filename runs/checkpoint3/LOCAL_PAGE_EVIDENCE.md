# Local webpage evidence

- Start command: `cd equity_research_team && UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run page`
- Local URL: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- Health request: `GET /health` returned HTTP 200 with `{"status": "ok"}`. This checks the page process only. It does not show that the research desk completed.
- Command wiring: `equity_research_team/src/equity_research_team/web.py` builds the child command as the current Python executable plus `one_desk.py run <ticker>`. This is the same `one_desk.py run` command used from the terminal.
- MSGR UI request: status **failed** after the `agent_team` process returned HTTP 429 `credit_balance_exhausted`. The saved event stream has no completed node sequence, report path, or report content.
- Saved UI evidence: [ui_evidence.json](../desk/DESK_2026-11-22_13-40-27-300160/ui_evidence.json); [saved failure record](../desk/DESK_2026-11-22_13-40-27-300160/failure.json).
- No final report was displayed because the command failed before it wrote a joined final report.
- Screenshot: not captured because browser automation was unavailable.
- Successful model-assisted report display: not completed.
