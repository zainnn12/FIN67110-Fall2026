from equity_research_team.web import STATIC_DIR, RunInput, build_command


def test_input_and_command_use_fixed_arguments_without_a_shell():
    run_input = RunInput.from_payload(
        {"ticker": "cost", "peers": "wmt, tgt,bj", "price": "992.13"}
    )
    command = build_command(run_input)
    assert command[4:] == ["COST", "--peers", "WMT,TGT,BJ", "--price", "992.13"]
    assert command[1:4] == ["-u", "-m", "equity_research_team.main"]


def test_page_has_run_controls_and_report_area():
    page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "Run agent team" in page
    assert 'id="ticker"' in page
    assert 'id="report"' in page
