from __future__ import annotations

import json
from pathlib import Path

from equity_research_team.verifier import (
    MARK_CORRECT,
    MARK_WRONG,
    extract_numeric_claims,
    verify_run,
)


ACCESSION = "0000000001-26-000001"


class PassSemanticClient:
    def call(self, *, request, **kwargs):
        assert set(request) == {"task", "context", "expected_output"}
        return {
            "checks": [
                {
                    "claim_id": item["claim_id"],
                    "supported": True,
                    "explanation": "The supplied evidence states the number for the period.",
                    "corrected_value": "",
                    "source": item["evidence"],
                }
                for item in request["context"]["deterministic_checks"]
            ]
        }


def _write_run(run_dir: Path, report: str) -> None:
    run_dir.mkdir()
    filing_lines = [
        "Cover",
        "Total revenue 303154 275235",
        "Operating income 11685 10383; net income 9226 8099; diluted EPS 20.76 18.21",
        "Quarter total revenue 95723 86156; diluted EPS 6.75 5.87",
        "Cash from operations 15817; property additions 6435; equity 35803 29164; debt 3914 2248",
    ]
    (run_dir / "10-K_000000000126000001.txt").write_text(
        "\n".join(filing_lines) + "\n", encoding="utf-8"
    )
    facts = {
        "company": {"ticker": "TEST", "name": "Test Issuer"},
        "facts": {
            "revenue": _fact("Revenue", "RevenueTag", 303154000000, 275235000000),
            "operating_income": _fact(
                "Operating income", "OperatingIncomeLoss", 11685000000, 10383000000
            ),
            "net_income": _fact("Net income", "NetIncomeLoss", 9226000000, 8099000000),
            "diluted_eps": _fact("Diluted EPS", "EarningsPerShareDiluted", 20.76, 18.21),
            "equity": _fact("Equity", "StockholdersEquity", 35803000000, 29164000000),
        },
    }
    (run_dir / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (run_dir / "equity_research_report.md").write_text(report, encoding="utf-8")


def _fact(label: str, tag: str, current: float, prior: float) -> dict:
    return {
        "label": label,
        "tag": tag,
        "unit": "USD",
        "current": {
            "val": current,
            "start": "2025-09-01",
            "end": "2026-08-30",
            "fy": 2026,
            "accn": ACCESSION,
        },
        "prior": {
            "val": prior,
            "start": "2024-09-02",
            "end": "2025-08-31",
            "fy": 2025,
            "accn": ACCESSION,
        },
    }


def _verify(tmp_path: Path, report: str):
    run_dir = tmp_path / "run"
    _write_run(run_dir, report)
    verified = verify_run(
        run_dir=run_dir,
        report_path=run_dir / "equity_research_report.md",
        output_dir=run_dir,
        semantic_client=PassSemanticClient(),
        verifier_instructions="Check every deterministic claim.",
    )
    output = json.loads((run_dir / "nodes" / "06_verifier_output.json").read_text())
    return verified, output


def test_seeded_diluted_eps_is_wrong_and_corrected(tmp_path):
    report = f"""Filings read: 10-K accession {ACCESSION}
Run time: 2026-11-05T12:00:00-05:00

# Equity Research Report

## Overview

FY2026 diluted EPS was $21.76. [10-K accession {ACCESSION}, line 3; tag `EarningsPerShareDiluted`; period 2025-09-01 to 2026-08-30.]
"""
    verified, output = _verify(tmp_path, report)
    assert output["counts"][MARK_WRONG] == 1
    claim = output["claims"][0]
    assert claim["final_mark"] == MARK_WRONG
    assert claim["corrected_value"] == "$20.76"
    assert "EarningsPerShareDiluted" in claim["evidence"]
    assert "| wrong |" in verified.read_text()


def test_invented_revenue_growth_is_wrong(tmp_path):
    report = f"""Filings read: 10-K accession {ACCESSION}
Run time: 2026-11-05T12:00:00-05:00

# Equity Research Report

## Overview

Revenue growth was ($95,723 - $86,156) / $86,156 = 15.10%. [10-K accession {ACCESSION}, line 4; period 2026-08-30 and 2025-08-31.]
"""
    _, output = _verify(tmp_path, report)
    claim = output["claims"][0]
    assert claim["final_mark"] == MARK_WRONG
    assert claim["corrected_value"] == "11.10%"
    assert "Recomputed in code" in claim["evidence"]


def test_clean_eleven_core_claims_are_correct(tmp_path):
    report = f"""Filings read: 10-K accession {ACCESSION}
Run time: 2026-11-05T12:00:00-05:00

# Equity Research Report

## Overview

1. FY2026 total revenue was $303,154 million. [10-K accession {ACCESSION}, line 2; tag `RevenueTag`; period 2025-09-01 to 2026-08-30.]
2. Revenue growth was ($303,154 - $275,235) / $275,235 = 10.14%. [10-K accession {ACCESSION}, line 2; period 2025-09-01 to 2026-08-30 and 2024-09-02 to 2025-08-31.]
3. Operating margin was $11,685 / $303,154 = 3.85%. [10-K accession {ACCESSION}, lines 2-3; period 2025-09-01 to 2026-08-30.]
4. FY2026 net income was $9,226 million. [10-K accession {ACCESSION}, line 3; tag `NetIncomeLoss`; period 2025-09-01 to 2026-08-30.]
5. FY2026 diluted EPS was $20.76. [10-K accession {ACCESSION}, line 3; tag `EarningsPerShareDiluted`; period 2025-09-01 to 2026-08-30.]
6. Return on average equity is defined as net income divided by average equity: $9,226 / (($35,803 + $29,164) / 2) = 28.40%. [10-K accession {ACCESSION}, lines 3-5; period 2025-09-01 to 2026-08-30.]
7. Debt to equity is defined as current plus noncurrent debt divided by equity: ($3,914 + $2,248) / $35,803 = 0.1721x. [10-K accession {ACCESSION}, line 5; period 2026-08-30.]
8. Free cash flow is defined as cash from operations less property additions: $15,817 - $6,435 = $9,382 million. [10-K accession {ACCESSION}, line 5; period 2025-09-01 to 2026-08-30.]
9. Quarterly revenue was $95,723 million. [10-K accession {ACCESSION}, line 4; period 2026-08-30.]
10. Quarterly revenue growth was ($95,723 - $86,156) / $86,156 = 11.10%. [10-K accession {ACCESSION}, line 4; period 2026-08-30 and 2025-08-31.]
11. Quarterly diluted EPS was $6.75. [10-K accession {ACCESSION}, line 4; period 2026-08-30.]

## Investment Recommendation

The thesis uses a deciding number of 999x, which the Verifier must skip.
"""
    verified, output = _verify(tmp_path, report)
    assert len(output["claims"]) == 11
    assert output["counts"] == {MARK_CORRECT: 11, MARK_WRONG: 0, "unsupported": 0}
    text = verified.read_text()
    assert text.splitlines()[0].startswith("Filings read:")
    assert text.splitlines()[2] == "## Verification marks"


def test_extractor_skips_investment_advisor_thesis():
    report = """Filings read: one filing

## Overview
Revenue was $10. [10-K, line 1.]

## Investment Recommendation
The deciding number is 999x.
"""
    claims = extract_numeric_claims(report)
    assert [claim.reported for claim in claims] == ["$10"]


def test_extractor_checks_advisor_insight_but_skips_advisor_thesis():
    report = f"""Filings read: one filing

## Overview
Revenue was $10. [10-K, line 1.]

## Investment Recommendation
The deciding thesis number is 999x.

Insight: FY2026 diluted EPS was $20.76. [10-K accession {ACCESSION}, line 3; tag `EarningsPerShareDiluted`; period 2025-09-01 to 2026-08-30.]
"""
    claims = extract_numeric_claims(report)
    assert [claim.reported for claim in claims] == ["$10", "$20.76"]
