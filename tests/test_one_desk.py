import json
import sys
from pathlib import Path

import pytest

import one_desk
from one_desk import DeskRunError, assemble_final, finalize_outputs, replay, run_command, run_desk


def test_non_registry_ticker_has_not_applicable_spinoff_sections(tmp_path):
    report = assemble_final(tmp_path, None, None, "UNLISTED", None)
    assert "Ticker: UNLISTED" in report
    assert "## Spinoff screen\nnot applicable" in report
    assert "not applicable: screen has no ranked ticker." in report


def test_execution_order_is_code_defined_and_not_model_selected():
    source=Path(one_desk.__file__).read_text()
    seeker=source.index('run_command("seeker"')
    team=source.index('run_command("agent_team"')
    worksheet=source.index('run_command("worksheet"')
    guard=source.index('final=finalize_outputs',worksheet)
    assert seeker < team < worksheet < guard
    assert "OpenAIRoleClient" not in source and "model" not in source.lower()


def test_replay_is_byte_identical_and_file_only(tmp_path, monkeypatch):
    import requests
    run_dir = tmp_path / "saved-run"
    run_dir.mkdir()
    report = assemble_final(run_dir, None, None, "UNLISTED", None)
    (run_dir / "final_report.md").write_text(report)
    (run_dir / "run_manifest.json").write_text(json.dumps({
        "ticker": "UNLISTED", "team_run": None, "worksheet": None,
        "registry_path": None, "final_report": str(run_dir / "final_report.md")
    }))
    def no_network(*args, **kwargs):
        raise AssertionError("replay attempted network access")
    monkeypatch.setattr(requests.sessions.Session, "request", no_network)
    assert replay(run_dir)
    proof = json.loads((run_dir / "replay" / "replay_proof.json").read_text())
    assert proof["network_calls"] == 0
    assert proof["byte_identical"] is True


def test_screen_empty_report_and_manifest_are_not_applicable(tmp_path):
    report = assemble_final(tmp_path, None, None, "not applicable", None)
    assert "Ticker: NOT APPLICABLE" in report
    assert "## Spinoff screen\nnot applicable" in report


def test_screen_empty_saves_all_part_timings_and_does_not_pick(tmp_path,monkeypatch):
    def fake_run(name,command,run_dir,**kwargs):
        (run_dir/"seeker_timing.json").write_text(json.dumps({"part":"seeker","elapsed_seconds":0.1,"return_code":0}))
        seeker=run_dir/"seeker"/"SEEKER_fixture";seeker.mkdir(parents=True)
        (seeker/"registry.json").write_text(json.dumps({"records":[]}))
        (seeker/"manifest.json").write_text(json.dumps({"ranked_count":0}))
        (seeker/"evaluation_final.json").write_text(json.dumps({"ranked":[]}))
        return f"Run folder: {seeker}\n"
    monkeypatch.setattr(one_desk,"run_command",fake_run)
    final=run_desk("SCREEN",run_root=tmp_path)
    run_dir=final.parent
    manifest=json.loads((run_dir/"run_manifest.json").read_text())
    assert manifest["ticker"] is None and manifest["screen"] is True
    assert json.loads((run_dir/"picker.json").read_text())["status"]=="not applicable"
    assert (run_dir/"deterministic_picker_timing.json").is_file()
    assert (run_dir/"seeker_timing.json").is_file()
    assert (run_dir/"final_assembler_timing.json").is_file()
    assert json.loads((run_dir/"worksheet_hook_timing.json").read_text())["status"].startswith("not applicable")
    assert "not applicable" in final.read_text().lower()


def test_seeded_worksheet_blocks_agent_completion_before_final_report(tmp_path):
    team=tmp_path/"team";team.mkdir()
    run=tmp_path/"desk";run.mkdir()
    (team/"facts.json").write_text(json.dumps({"supported_amount":10}))
    worksheet=team/"worksheet.md"
    worksheet.write_text("Supported amount: 11\n")
    with pytest.raises(ValueError,match="line 1"):
        finalize_outputs(run,team,worksheet,"TST",None)
    assert not (run/"final_report.md").exists()


def test_failed_part_preserves_run_folder_and_exact_error(tmp_path,capsys):
    with pytest.raises(DeskRunError,match="ERROR: seeded failure"):
        run_command("seeded",[sys.executable,"-c","import sys;print('ERROR: seeded failure',file=sys.stderr);sys.exit(7)"],tmp_path)
    record=json.loads((tmp_path/"failure.json").read_text())
    assert record["return_code"]==7
    assert record["stderr"].strip()=="ERROR: seeded failure"
    assert f"Run folder: {tmp_path}" in capsys.readouterr().out
