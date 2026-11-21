from __future__ import annotations

import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest


SCRIPTS_DIR = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "spinoff-seeker"
    / "scripts"
)
WORKSPACE_DIR = SCRIPTS_DIR.parents[2]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))
from equity_research_data import DownloadedResource
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from closes_reader import (  # noqa: E402
    FINANCIAL_DATASETS_PRICES_URL,
    CloseReaderError,
    DailyClose,
    FinancialDatasetsClosesReader,
    build_closes_reader,
    first_close_after,
)
from seeker import (  # noqa: E402
    FINAL_FACTORS_PATH,
    evaluate_snapshot,
    load_factors,
    _save_cited_fact_sources,
    extract_parent_name,
    prove_zero_weight,
    render_report,
    validate_report_contract,
)


def test_parent_extractor_trims_prose_and_rejects_unresolved_fragments():
    cleaned = extract_parent_name(
        "Our parent, Honeywell’s other businesses following the Internal Reorganization, will remain.",
        form="10-12B", accession="0000000000-26-000001", url="https://www.sec.gov/example",
    )
    assert cleaned["value"] == "Honeywell"
    exact_parent = extract_parent_name(
        "the distribution by Madison Square Garden Sports Corp. (\u201cMSG Sports\u201d) to holders",
        form="10-12B/A", accession="0000000000-26-000001", url="https://www.sec.gov/example",
    )
    assert exact_parent["value"] == "Madison Square Garden Sports Corp"
    unresolved = extract_parent_name(
        "The company, which is resident for tax purposes in Switzerland, distributed shares.",
        form="10-12B", accession="0000000000-26-000001", url="https://www.sec.gov/example",
    )
    assert unresolved is None


def test_cited_fact_source_is_saved_once(tmp_path):
    class Client:
        calls=0
        def fetch(self,url):
            self.calls+=1
            return DownloadedResource(url,b"source evidence","text/plain","utf-8")
    client=Client()
    records=[{"facts":{"distribution_date":{"source":{"url":"https://www.sec.gov/Archives/edgar/data/123/000000000126000001/doc.txt","accession":"0000000001-26-000001","form":"8-K"}}}}]
    saved=_save_cited_fact_sources(client,tmp_path,records)
    assert client.calls==1 and len(saved)==1
    _save_cited_fact_sources(client,tmp_path,records)
    assert client.calls==1


class FakeResponse:
    def __init__(self, payload, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class RecordingSession:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


def test_financial_datasets_endpoint_header_and_response_parsing():
    session = RecordingSession(
        [
            FakeResponse(
                {
                    "ticker": "TEST",
                    "prices": [
                        {
                            "ticker": "TEST",
                            "time": "2026-11-17",
                            "close": 24.5,
                        },
                        {
                            "ticker": "TEST",
                            "time": "2026-11-18T00:00:00Z",
                            "close": "25.75",
                        },
                    ],
                }
            )
        ]
    )
    reader = FinancialDatasetsClosesReader("synthetic-test-key", session=session)

    closes = reader.daily_closes(
        "test", date(2026, 11, 17), date(2026, 11, 18)
    )

    assert session.calls == [
        (
            FINANCIAL_DATASETS_PRICES_URL,
            {
                "params": {
                    "ticker": "TEST",
                    "interval": "day",
                    "start_date": "2026-11-17",
                    "end_date": "2026-11-18",
                },
                "headers": {"X-API-KEY": "synthetic-test-key"},
                "timeout": 45,
            },
        )
    ]
    assert FINANCIAL_DATASETS_PRICES_URL == "https://api.financialdatasets.ai/prices"
    assert [item.trading_date for item in closes] == [
        date(2026, 11, 17),
        date(2026, 11, 18),
    ]
    assert [item.close for item in closes] == [Decimal("24.5"), Decimal("25.75")]
    assert {item.source for item in closes} == {
        "Financial Datasets historical close"
    }


def test_market_data_builder_does_not_use_openai_api_key(tmp_path):
    (tmp_path / ".env").write_text(
        "API_KEY=synthetic-openai-key\n", encoding="utf-8"
    )

    with pytest.raises(
        CloseReaderError,
        match="FINANCIAL_DATASETS_API_KEY is missing or empty",
    ):
        build_closes_reader(tmp_path)


@pytest.mark.parametrize(
    ("response", "expected_calls"),
    [
        (FakeResponse({"ticker": "NONE", "prices": []}), 1),
        (FakeResponse({"error": "Not Found"}, status_code=404), 1),
    ],
)
def test_unavailable_price_returns_no_closes(response, expected_calls):
    session = RecordingSession([response])
    reader = FinancialDatasetsClosesReader("synthetic-test-key", session=session)

    assert reader.daily_closes(
        "NONE", date(2026, 11, 17), date(2026, 11, 18)
    ) == []
    assert len(session.calls) == expected_calls


def _synthetic_snapshot():
    return {
        "start_date": "2025-11-18",
        "run_date": "2026-11-19",
        "index_date": "2026-11-19",
        "window_days": 90,
        "records": [
            {
                "cik": 1,
                "company": "Fabricated Spin Co",
                "ticker": "FSC",
                "classification": "spinoff",
                "stage": "in_window",
                "facts": {
                    "parent": {"value": "Fabricated Parent"},
                    "distribution_date": {"value": "2026-10-01"},
                },
                "first_price": {
                    "trading_date": "2026-10-02",
                    "close": "10.00",
                },
                "day20_price": {
                    "trading_date": "2026-10-30",
                    "close": "9.00",
                },
                "factor_inputs": {
                    "relative_company_size_ratio": "0.05",
                    "price_decline_percent": "10",
                    "distinct_qualifying_insiders": 2,
                },
                "unavailable_facts": [],
            },
            {
                "cik": 2,
                "company": "Fabricated Watch Co",
                "ticker": "",
                "classification": "spinoff",
                "stage": "registered",
                "classification_filing": {
                    "form": "10-12B",
                    "accession": "0000000002-26-000001",
                    "url": "https://www.sec.gov/example-watch",
                },
                "facts": {},
                "factor_inputs": {},
                "unavailable_facts": ["Distribution date", "Trading ticker"],
            },
        ],
        "dropped": [
            {
                "cik": 3,
                "company": "Fabricated Fund",
                "reason": "Registrant is a fund, not a spinoff.",
                "classification_filing": {
                    "form": "10-12G",
                    "accession": "0000000003-26-000001",
                    "url": "https://www.sec.gov/example-drop",
                },
            }
        ],
    }


def test_report_contract_rank_watch_drop_and_missing_fact():
    snapshot = _synthetic_snapshot()
    evaluation = evaluate_snapshot(snapshot, load_factors(FINAL_FACTORS_PATH))

    report = render_report(snapshot, evaluation)
    validate_report_contract(report)

    assert report.splitlines()[0] == (
        "Run date: 2026-11-19 | Price date: 2026-10-30 | "
        "Index date: 2026-11-19"
    )
    assert "Fabricated Spin Co (FSC)" in report
    assert "Relative company size: 2 points" in report
    assert "Post-distribution price weakness: 1 points" in report
    assert "Insider open-market buying: 2 points" in report
    assert "Fabricated Watch Co" in report
    assert "Fabricated Fund: Registrant is a fund, not a spinoff." in report
    assert "Distribution date. Left blank; not estimated." in report
    assert report.splitlines()[-1] == "screens, not recommendations"


def test_first_price_is_strictly_after_distribution():
    closes = [
        DailyClose(date(2026, 10, 1), Decimal("20"), "FSC", "test"),
        DailyClose(date(2026, 10, 2), Decimal("19"), "FSC", "test"),
    ]

    selected = first_close_after(closes, date(2026, 10, 1))

    assert selected is not None
    assert selected.trading_date == date(2026, 10, 2)


def test_weight_zero_proof_removes_only_zero_factor_points(tmp_path):
    base_run = tmp_path / "base-run"
    base_run.mkdir()
    snapshot = _synthetic_snapshot()
    final = evaluate_snapshot(snapshot, load_factors(FINAL_FACTORS_PATH))
    (base_run / "evaluation_snapshot.json").write_text(
        __import__("json").dumps(snapshot), encoding="utf-8"
    )
    (base_run / "evaluation_final.json").write_text(
        __import__("json").dumps(final), encoding="utf-8"
    )

    proof_dir = prove_zero_weight(base_run)
    proof = __import__("json").loads((proof_dir / "proof.json").read_text())
    proof_report = (proof_dir / "seeker_report_weight_zero.md").read_text()

    assert proof["status"] == "PASS"
    assert proof["final_configuration_preserved"] is True
    checks = proof["comparisons"][0]["factor_checks"]
    by_factor = {item["factor_id"]: item for item in checks}
    assert by_factor["post_distribution_price_weakness"]["proof_points"] is None
    assert by_factor["relative_company_size"]["proof_points"] == 2
    assert by_factor["insider_open_market_buying"]["proof_points"] == 2
    assert "Post-distribution price weakness: disabled (0% weight)" in proof_report
