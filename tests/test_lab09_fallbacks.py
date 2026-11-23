import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NVDA_RUN = ROOT / "runs/lab09/DESK_2026-11-22_13-37-32-104848"
NVDA_TEAM = NVDA_RUN / "agent/NVIDIA_CORP_2026-11-22_13-37-33-357977"
NVDA_EXHIBIT = NVDA_TEAM / "8-K_EX-99.1_000104581026000088.txt"
WMT_RUN = ROOT / "runs/lab09/DESK_2026-11-22_13-37-44-279695"
WMT_TEAM = WMT_RUN / "agent/Walmart_Inc_2026-11-22_13-37-46-216137"
WMT_EXHIBIT = WMT_TEAM / "8-K_EX-99.1_000010416926000168.txt"


def _line(path: Path, number: int) -> str:
    return path.read_text(encoding="utf-8").splitlines()[number - 1]


def test_nvda_release_date_acceptance_time_and_citations_are_exact():
    assert "Nov. 17, 2026" in _line(NVDA_EXHIBIT, 13)
    assert "115,844" in _line(NVDA_EXHIBIT, 145)
    assert "103%" in _line(NVDA_EXHIBIT, 8)
    assert "103%" in _line(NVDA_EXHIBIT, 14)
    assert "103" in _line(NVDA_EXHIBIT, 21)
    assert "$107.6 billion" in _line(NVDA_EXHIBIT, 10)
    assert "110%" in _line(NVDA_EXHIBIT, 10)
    assert "$107.6 billion" in _line(NVDA_EXHIBIT, 50)
    assert "110%" in _line(NVDA_EXHIBIT, 50)
    assert "65,287" in _line(NVDA_EXHIBIT, 156)
    assert "$65.3" in _line(NVDA_EXHIBIT, 25)
    assert "77,520" in _line(NVDA_EXHIBIT, 152)
    assert "74.8" in _line(NVDA_EXHIBIT, 22)
    assert "2.70" in _line(NVDA_EXHIBIT, 159)
    assert "$130.0 billion" in _line(NVDA_EXHIBIT, 40)
    assert "$150 billion" in _line(NVDA_EXHIBIT, 16)
    assert "$28.1 billion" in _line(NVDA_EXHIBIT, 16)
    assert "$227.3 billion" in _line(NVDA_EXHIBIT, 16)

    manifest = json.loads((NVDA_TEAM / "manifest.json").read_text())
    exhibit_record = next(
        item for item in manifest["documents"] if item["label"] == "8-K_EX-99.1"
    )
    assert exhibit_record["accession_number"] == "0001045810-26-000088"
    assert exhibit_record["accepted"] == "2026-11-17 16:20:51"

    comparison = (ROOT / "LAB09_NVDA_COMPARISON.md").read_text()
    assert "November 17, 2026" in comparison
    assert "16:20:51 Eastern Time" in comparison
    assert "November 19, 2026" not in comparison
    assert "Exact revenue: Exhibit 99.1 line 145" in comparison
    assert "Reported 103% growth: lines 8, 14, and 21" in comparison
    assert "Exhibit 99.1 lines 10 and 50" in comparison
    assert "Exact amount: Exhibit 99.1 line 156" in comparison
    assert "line 25 is only the rounded $65.3 billion" in comparison


def test_fallback_worksheets_preserve_periods_and_do_not_invent_valuation():
    nvda = json.loads((NVDA_RUN / "fallback_worksheet.json").read_text())
    wmt = json.loads((WMT_RUN / "fallback_worksheet.json").read_text())

    assert nvda["model_calls"] == 0 and nvda["network_calls"] == 0
    assert {item["status"] for item in nvda["inputs"]} == {
        "unavailable",
        "unsupported",
    }
    assert nvda["results"]["owner_cash_flow"]["value"] == "NOT COMPUTABLE"
    assert all(
        result["value"] == "NOT COMPUTABLE" for result in nvda["results"].values()
    )

    diagnostic = wmt["deterministic_calculations"][0]
    assert diagnostic["formula"] == "17114 + 11763 - abs(-22621)"
    assert diagnostic["value"] == 6256
    assert diagnostic["period"] == "nine months ended 2026-10-31"
    assert diagnostic["valuation_use"] is False
    assert wmt["results"]["owner_cash_flow_annual_or_ttm"]["value"] == "NOT COMPUTABLE"
    assert all(
        result["value"] == "NOT COMPUTABLE" for result in wmt["results"].values()
    )
    assert "17,114" in _line(WMT_EXHIBIT, 216)
    assert "11,763" in _line(WMT_EXHIBIT, 218)
    assert "(22,621)" in _line(WMT_EXHIBIT, 230)


def test_fallback_manifests_map_saved_evidence_and_preserve_failed_runs():
    for run_dir in (NVDA_RUN, WMT_RUN):
        manifest = json.loads((run_dir / "fallback_manifest.json").read_text())
        assert manifest["status"] == "fallback_only_not_live_joined_output"
        assert manifest["model_calls"] == 0 and manifest["network_calls"] == 0
        assert manifest["failure"]["reason"] == "HTTP 429 credit_balance_exhausted"
        assert manifest["failure"]["stage"] == "Investment Advisor"
        assert "joined_final_report" in manifest["not_produced"]
        assert "parts_alone_output" in manifest["not_produced"]
        for item in manifest["saved_filing_evidence"]:
            assert (run_dir / item).is_file(), item
        for item in manifest["partial_unverified_role_outputs"]:
            assert (run_dir / item).is_file(), item
        for item in manifest["fallback_artifacts"][:3]:
            assert (run_dir / item["path"]).is_file(), item["path"]

        failure = json.loads((run_dir / "failure.json").read_text())
        assert failure["part"] == "agent_team"
        assert failure["return_code"] == 1
        assert not (run_dir / "final_report.md").exists()
        assert not (run_dir / "worksheet.md").exists()


def test_comparison_does_not_claim_missing_live_outputs():
    comparison = (ROOT / "LAB09_NVDA_COMPARISON.md").read_text()
    assert "Parts-alone output | **NOT PRODUCED**" not in comparison
    assert comparison.count("**NOT PRODUCED**") >= 20
    assert comparison.count("**NOT ASSESSABLE**") >= 10
    assert "do not replace the missing live outputs" in comparison
    assert "not used as parts-alone output" in comparison
