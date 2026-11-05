from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

from equity_research_team.team_flow import EquityResearchTeamFlow


ACCESSION = "0000000001-26-000001"


class StubRoleClient:
    def __init__(self, manager_failure: bool = False, missing_insight_role: str = ""):
        self.calls = []
        self.manager_failure = manager_failure
        self.missing_insight_role = missing_insight_role
        self.manager_calls = 0

    def call(self, *, role, instructions, request, schema_name, output_schema):
        assert set(request) == {"task", "context", "expected_output"}
        assert instructions.strip()
        self.calls.append((role, schema_name))
        if role == "Verifier":
            return {"checks": []}
        if schema_name.endswith("_correction"):
            previous_insight = request["context"]["previous_output"].get("insight")
            return {
                "corrected_parts": [
                    {
                        "part": item["part"],
                        "content": f"Corrected {item['part']} with the required evidence.",
                    }
                    for item in request["context"]["manager_feedback"]
                ],
                "insight": previous_insight or _default_insight(role),
            }
        if role == "Research Analyst":
            output = {
                "business_model": [_source_claim("Business text")],
                "competitive_position": [_source_claim("Business text")],
                "catalysts": [_source_claim("Business text")],
                "recent_developments": [_source_claim("Release text")],
                "limitations": [],
                "insight": _insight(
                    "Insight: The business description identifies 12 markets.",
                    "Business text has 12 markets.",
                    "10-K",
                    2,
                ),
            }
            if self.missing_insight_role == role:
                output.pop("insight")
            return output
        if role == "Financial Analyst":
            output = {
                "statement_analysis": [],
                "ratio_analysis": [],
                "quarterly_analysis": [],
                "peer_analysis": [],
                "valuation_insights": [],
                "calculator_requests": [],
                "limitations": [],
                "insight": _insight(
                    "Insight: Quarter total revenue was $1,200.",
                    "Total revenue | $ | 1,200 | $ | 1,000",
                    "Earnings release",
                    4,
                ),
            }
            if self.missing_insight_role == role:
                output.pop("insight")
            return output
        if role == "Investment Advisor":
            output = {
                "thesis": "Evidence is balanced.",
                "recommendation": "Hold",
                "deciding_number": "one sourced measure",
                "deciding_number_source": "Financial Analyst output",
                "rationale": "The measure balances the evidence.",
                "risks": [],
                "insight": _insight(
                    "Insight: Quarter total revenue was $1,200.",
                    "Total revenue | $ | 1,200 | $ | 1,000",
                    "Earnings release",
                    4,
                ),
            }
            if self.missing_insight_role == role:
                output.pop("insight")
            return output
        if role == "Strategy Manager":
            self.manager_calls += 1
            failures = []
            if self.manager_failure and self.manager_calls == 1:
                failures = [
                    {
                        "part": "Overview",
                        "responsible_role": "Research Analyst",
                        "problem": "Clarify the overview.",
                        "required_correction": "Use the exact quote.",
                    }
                ]
            return {
                "failures": failures,
                "overview": "The filing-supported overview is complete.",
                "market_positioning_and_growth_outlook": "Positioning is filing-supported.",
                "valuation_insights": "Valuation evidence is supplied.",
                "future_developments_and_strategic_recommendations": "Recommendations are conditional.",
                "investment_recommendation": "Hold based on one sourced measure.",
            }
        raise AssertionError(role)


def _source_claim(quote):
    return {
        "claim": quote,
        "quote": quote,
        "filing": "Earnings release" if quote == "Release text" else "10-K",
        "accession_number": ACCESSION,
        "line_start": 1 if quote == "Release text" else 2,
        "line_end": 1 if quote == "Release text" else 2,
    }


def _insight(line, quote, filing, source_line):
    return {
        "line": line,
        "quote": quote,
        "filing": filing,
        "accession_number": ACCESSION,
        "line_start": source_line,
        "line_end": source_line,
    }


def _default_insight(role):
    if role == "Research Analyst":
        return _insight(
            "Insight: The business description identifies 12 markets.",
            "Business text has 12 markets.",
            "10-K",
            2,
        )
    return _insight(
        "Insight: Quarter total revenue was $1,200.",
        "Total revenue | $ | 1,200 | $ | 1,000",
        "Earnings release",
        4,
    )


class DummyDesk:
    def __init__(self, run_dir: Path):
        self.output_dir = run_dir
        self.run_started = datetime(2026, 11, 5, 12, 0, 0)
        self.price = Decimal("100")
        self.steps = []
        self.document_texts = {
            "10-K": (
                "ITEM 1. BUSINESS\nBusiness text has 12 markets.\nITEM 1A. RISK FACTORS\n"
                "ITEM 7. MANAGEMENT DISCUSSION\nManagement text\nITEM 7A. DISCLOSURES\n"
            ),
            "10-Q": "Quarter text\n",
            "8-K": "Release text\n",
            "8-K_EX-99.1": _release_text(),
        }
        self.release_text = self.document_texts["8-K_EX-99.1"]
        self.fact_set = _facts("TEST")
        self.peer_fact_sets = {"PEER": _facts("PEER")}
        self.selected = {
            name: SimpleNamespace(accession_number=ACCESSION) for name in ("10-K", "10-Q", "8-K")
        }

    def ensure_output_dir(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def ensure_filings(self):
        return self.selected

    def ensure_release_text(self):
        return self.release_text

    def ensure_fact_set(self):
        return self.fact_set

    def _step(self, number):
        self.steps.append(number)
        run_dir = self.ensure_output_dir()
        if number == 3:
            for label, text in self.document_texts.items():
                (run_dir / f"{label}_{ACCESSION.replace('-', '')}.txt").write_text(text)
        if number == 4:
            (run_dir / "facts.json").write_text(json.dumps(self.fact_set))
        if number == 7:
            (run_dir / "facts_PEER.json").write_text(json.dumps(self.peer_fact_sets["PEER"]))

    def step_1(self): self._step(1)
    def step_2(self): self._step(2)
    def step_3(self): self._step(3)
    def step_4(self): self._step(4)
    def step_5(self): self._step(5)
    def step_6(self): self._step(6)
    def step_7(self): self._step(7)


def _fact(tag, current, prior):
    return {
        "label": tag,
        "tag": tag,
        "unit": "USD",
        "current": {"val": current, "start": "2025-01-01", "end": "2025-12-31", "accn": ACCESSION},
        "prior": {"val": prior, "start": "2024-01-01", "end": "2024-12-31", "accn": ACCESSION},
    }


def _facts(ticker):
    return {
        "company": {"ticker": ticker, "name": f"{ticker} issuer"},
        "facts": {
            "revenue": _fact("Revenue", 1000, 900),
            "operating_income": _fact("OperatingIncomeLoss", 100, 90),
            "net_income": _fact("NetIncomeLoss", 80, 70),
            "diluted_eps": _fact("EarningsPerShareDiluted", 2, 1.8),
            "stockholders_equity": _fact("StockholdersEquity", 400, 350),
            "long_term_debt": _fact("LongTermDebtNoncurrent", 50, 60),
            "current_long_term_debt": _fact("LongTermDebtCurrent", 10, 8),
            "cash_from_operations": _fact("OperatingCashFlow", 120, 110),
            "property_additions": _fact("PropertyAdditions", 30, 25),
        },
    }


def _release_text():
    return """Release text
CONSOLIDATED STATEMENTS OF INCOME
16 weeks ended
Total revenue | $ | 1,200 | $ | 1,000
NET INCOME PER SHARE
Diluted | $ | 2.00 | $ | 1.80
"""


def _run_flow(tmp_path, manager_failure=False, missing_insight_role=""):
    run_dir = tmp_path / "run"
    desk = DummyDesk(run_dir)
    client = StubRoleClient(
        manager_failure=manager_failure,
        missing_insight_role=missing_insight_role,
    )
    flow = EquityResearchTeamFlow(desk=desk, role_client=client)
    result = flow.kickoff(
        inputs={"ticker": "TEST", "peers": ["PEER"], "price": "100", "model": "stub"}
    )
    return flow, desk, client, Path(result)


def test_fixed_flow_runs_all_nodes_and_mandatory_verifier(tmp_path):
    flow, desk, client, verified = _run_flow(tmp_path)
    assert desk.steps == list(range(1, 8))
    assert flow.state.node_order == [
        "Steps",
        "Research Analyst",
        "Financial Analyst",
        "Investment Advisor",
        "Strategy Manager",
        "Verifier",
    ]
    assert verified.name == "verified_report.md"
    assert verified.is_file()
    assert (verified.parent / "nodes" / "06_verifier_input.json").is_file()
    assert client.calls[-1][0] == "Verifier"
    assert (verified.parent / "equity_research_report.md").read_text().count("Insight:") == 3


def test_one_correction_pass_never_runs_a_role_more_than_twice(tmp_path):
    flow, _, _, _ = _run_flow(tmp_path, manager_failure=True)
    assert flow.state.role_call_counts == {
        "Research Analyst": 2,
        "Financial Analyst": 1,
        "Investment Advisor": 2,
        "Strategy Manager": 1,
        "Verifier": 1,
    }
    assert max(flow.state.role_call_counts.values()) == 2


def test_missing_insight_sends_part_back_once(tmp_path):
    flow, _, _, _ = _run_flow(tmp_path, missing_insight_role="Research Analyst")
    assert flow.state.role_call_counts["Research Analyst"] == 2
    assert flow.state.role_call_counts["Investment Advisor"] == 2
    assert flow.state.role_call_counts["Strategy Manager"] == 1
    assert Path(flow.state.report_path).read_text().count("Insight:") == 3


def test_first_paragraph_restatement_fails_insight_check(tmp_path):
    desk = DummyDesk(tmp_path / "run")
    first_paragraph = (
        "The company announced that quarter total revenue was $1,200 for the current "
        "reporting period."
    )
    desk.release_text = first_paragraph + "\nA later paragraph has other evidence.\n"
    flow = EquityResearchTeamFlow(desk=desk, role_client=StubRoleClient())
    issues = flow._insight_issues(
        "Financial Analyst",
        {
            "insight": _insight(
                "Insight: Quarter total revenue was $1,200.",
                first_paragraph,
                "Earnings release",
                1,
            )
        },
    )
    assert any("only restates" in issue for issue in issues)
