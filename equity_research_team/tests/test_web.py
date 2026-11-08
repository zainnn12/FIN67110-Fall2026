import json
import os
import subprocess
import sys

import equity_research_team.web as web
from equity_research_team.web import (
    AMD_FALLBACK_DIR,
    PACKAGE_SOURCE_DIR,
    STATIC_DIR,
    WORKSPACE_DIR,
    RunInput,
    build_command,
    build_environment,
    fallback_report_for,
    is_credit_balance_exhausted,
)


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
    assert 'item.kind === \'fallback\'' in page
    assert "reportTitle.textContent = item.label" in page


def test_subprocess_can_import_src_package_from_outside_project(tmp_path):
    environment = build_environment({"PATH": os.environ.get("PATH", "")})
    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import equity_research_team; print(equity_research_team.__file__)",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=True,
        text=True,
    )
    package_init = PACKAGE_SOURCE_DIR / "equity_research_team" / "__init__.py"
    assert completed.stdout.strip() == str(package_init)
    assert str(WORKSPACE_DIR) in environment["PYTHONPATH"].split(os.pathsep)


def test_amd_credit_error_selects_only_matching_saved_fallback():
    run_input = RunInput.from_payload(
        {"ticker": "AMD", "peers": "NVDA,INTC,AVGO", "price": "466.84"}
    )
    fallback = fallback_report_for(run_input)
    assert fallback == AMD_FALLBACK_DIR / "fallback_report.md"
    report = fallback.read_text(encoding="utf-8")
    assert "Partner manual checks: PASS" in report
    assert sum(line.startswith("Insight:") for line in report.splitlines()) == 3
    assert is_credit_balance_exhausted("ERROR: HTTP 429 credit_balance_exhausted")
    assert not is_credit_balance_exhausted("ModuleNotFoundError: no module")


def test_fallback_is_not_used_for_other_inputs():
    cost = RunInput.from_payload(
        {"ticker": "COST", "peers": "WMT,TGT,BJ", "price": "992.13"}
    )
    other_amd = RunInput.from_payload(
        {"ticker": "AMD", "peers": "NVDA,INTC", "price": "466.84"}
    )
    assert fallback_report_for(cost) is None
    assert fallback_report_for(other_amd) is None


def test_429_ui_run_displays_and_saves_fallback_evidence(tmp_path, monkeypatch):
    run_dir = tmp_path / "amd-attempt"
    run_dir.mkdir()

    class FailedProcess:
        stdout = iter(
            [
                "Node: SEC Step 1\n",
                f"Run folder: {run_dir}\n",
                "Node: Research Analyst\n",
                "ERROR: Error code: 429 credit_balance_exhausted\n",
            ]
        )

        def wait(self):
            return 1

    monkeypatch.setattr(
        web.subprocess, "Popen", lambda *args, **kwargs: FailedProcess()
    )
    run_input = RunInput.from_payload(
        {"ticker": "AMD", "peers": "NVDA,INTC,AVGO", "price": "466.84"}
    )
    record = web.RunRecord(run_id="a" * 32)
    web._runs[record.run_id] = record
    try:
        web._run_team(record.run_id, run_input)
        assert record.status == "fallback"
        fallback_event = next(
            event for event in record.events if event["kind"] == "fallback"
        )
        assert fallback_event["label"] == "Fallback — not a live agent-team run"
        evidence = json.loads(
            (run_dir / "ui_evidence.json").read_text(encoding="utf-8")
        )
        assert evidence["status"] == "fallback"
        assert evidence["node_order"] == ["SEC Step 1", "Research Analyst"]
        assert evidence["fallback_label"] == "Fallback — not a live agent-team run"
    finally:
        web._runs.pop(record.run_id, None)
