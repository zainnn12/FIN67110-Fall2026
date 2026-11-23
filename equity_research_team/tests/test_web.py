import json
import os
import subprocess
import sys

import equity_research_team.web as web
from equity_research_team.web import (
    FALLBACK_BANNER,
    ONE_DESK,
    PACKAGE_SOURCE_DIR,
    STATIC_DIR,
    WORKSPACE_DIR,
    RunInput,
    build_command,
    build_environment,
)


def test_one_desk_command_uses_fixed_order_and_accepts_screen():
    run_input = RunInput.from_payload({"ticker": "msgr"})
    assert run_input.ticker == "MSGR"
    assert build_command(run_input) == [sys.executable, "-u", str(ONE_DESK), "run", "MSGR"]
    assert build_command(RunInput.from_payload({"ticker": "SCREEN"}))[-1] == "SCREEN"
    assert "--" not in " ".join(build_command(run_input))


def test_page_posts_one_desk_input_and_displays_final_report():
    page = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert "Run joined desk" in page
    assert 'id="ticker"' in page and "MSGR or SCREEN" in page
    assert "one-desk pipeline" in page
    assert "final report" in page
    assert "peers:" not in page and "price:" not in page
    assert "Open saved fallback" in page
    assert FALLBACK_BANNER in page
    assert "Saved fallback report and worksheet" in page


def test_subprocess_can_import_src_package_from_outside_project(tmp_path):
    environment = build_environment({"PATH": os.environ.get("PATH", "")})
    completed = subprocess.run(
        [sys.executable, "-S", "-c", "import equity_research_team; print(equity_research_team.__file__)"],
        cwd=tmp_path, env=environment, capture_output=True, check=True, text=True,
    )
    package_init = PACKAGE_SOURCE_DIR / "equity_research_team" / "__init__.py"
    assert completed.stdout.strip() == str(package_init)
    assert str(WORKSPACE_DIR) in environment["PYTHONPATH"].split(os.pathsep)


def test_ui_runs_joined_command_and_displays_saved_final_report(tmp_path, monkeypatch):
    run_dir = tmp_path / "desk-run"
    run_dir.mkdir()
    final = run_dir / "final_report.md"
    final.write_text("saved joined report\n")

    class Process:
        stdout = iter([f"Run folder: {run_dir}\n", f"Final report: {final}\n"])
        def wait(self): return 0

    captured = {}
    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Process()

    monkeypatch.setattr(web.subprocess, "Popen", fake_popen)
    run_input = RunInput.from_payload({"ticker": "NVDA"})
    record = web.RunRecord(run_id="a" * 32)
    web._runs[record.run_id] = record
    try:
        web._run_team(record.run_id, run_input)
        assert captured["command"] == build_command(run_input)
        assert record.status == "complete"
        assert record.report == "saved joined report\n"
        evidence = json.loads((run_dir / "ui_evidence.json").read_text())
        assert evidence["status"] == "complete"
        assert evidence["report_path"] == str(final)
    finally:
        web._runs.pop(record.run_id, None)


def test_ui_preserves_exact_joined_command_failure(tmp_path, monkeypatch):
    run_dir = tmp_path / "failed-run"
    run_dir.mkdir()
    class Process:
        stdout = iter([f"Run folder: {run_dir}\n", "ERROR: credit_balance_exhausted\n"])
        def wait(self): return 1
    monkeypatch.setattr(web.subprocess, "Popen", lambda *a, **k: Process())
    record = web.RunRecord(run_id="b" * 32)
    web._runs[record.run_id] = record
    try:
        web._run_team(record.run_id, RunInput.from_payload({"ticker": "NVDA"}))
        assert record.status == "failed"
        assert any(x.get("message") == "ERROR: credit_balance_exhausted" for x in record.events)
    finally:
        web._runs.pop(record.run_id, None)


def test_saved_fallback_path_reads_files_without_subprocess_or_external_call(
    tmp_path, monkeypatch
):
    run_dir = tmp_path / "DESK_saved"
    run_dir.mkdir()
    (run_dir / "fallback_report.md").write_text("fallback report\n")
    (run_dir / "fallback_worksheet.md").write_text("fallback worksheet\n")
    (run_dir / "failure.json").write_text('{"preserved": true}\n')
    (run_dir / "fallback_manifest.json").write_text(json.dumps({
        "failure": {"reason": "HTTP 429 credit_balance_exhausted"},
        "not_produced": ["joined_final_report", "investment_view"],
    }))
    monkeypatch.setitem(web.FALLBACK_RUNS, "NVDA", run_dir)
    monkeypatch.setattr(
        web.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("fallback path must not start a subprocess")
        ),
    )
    monkeypatch.setattr(web, "WORKSPACE_DIR", tmp_path)

    record = web.RunRecord(run_id="c" * 32)
    web._runs[record.run_id] = record
    try:
        web._load_saved_fallback(record.run_id, "NVDA")
        assert record.status == "fallback"
        assert record.report == "fallback report\n\n---\n\nfallback worksheet\n"
        event = record.events[-1]
        assert event["kind"] == "fallback"
        assert event["banner"] == FALLBACK_BANNER
        assert event["ticker"] == "NVDA"
        assert event["saved_run"] == "DESK_saved"
        assert event["failure_reason"] == "HTTP 429 credit_balance_exhausted"
        assert event["missing_outputs"] == ["joined_final_report", "investment_view"]
        evidence = json.loads((run_dir / "fallback_ui_evidence.json").read_text())
        assert evidence["status"] == "fallback_displayed"
        assert evidence["network_calls"] == 0
        assert evidence["model_calls"] == 0
        assert evidence["live_joined_report_succeeded"] is False
    finally:
        web._runs.pop(record.run_id, None)


def test_saved_fallback_rejects_ticker_without_declared_package():
    record = web.RunRecord(run_id="d" * 32)
    web._runs[record.run_id] = record
    try:
        try:
            web._load_saved_fallback(record.run_id, "MSGR")
        except ValueError as exc:
            assert "only for NVDA and WMT" in str(exc)
        else:
            raise AssertionError("an undeclared fallback ticker must fail")
    finally:
        web._runs.pop(record.run_id, None)
