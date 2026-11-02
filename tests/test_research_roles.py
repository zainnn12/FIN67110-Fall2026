from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from research_roles import (
    ROLE_ADVISOR,
    ROLE_FINANCIAL,
    ROLE_MANAGER,
    ROLE_RESEARCH,
    calculate_ratio_request,
    compile_report_markdown,
    extract_ten_k_sections,
    run_four_role_workflow,
    validate_role_request,
)


TEN_K_TEXT = """Cover
Item 1—Business
The registrant sells a limited selection through a membership format.
Item 1A—Risk Factors
Competition can affect results.
Item 7—Management's Discussion and Analysis
Revenue increased because unit volume increased.
Item 7A—Quantitative and Qualitative Disclosures About Market Risk
Market-risk text.
"""

RELEASE_TEXT = """Press Release
The registrant launched a new service during the quarter.
Revenue | 120 | 100
"""


def source_claim(
    claim: str,
    quote: str,
    filing: str,
    accession: str,
    line: int,
) -> dict[str, Any]:
    return {
        "claim": claim,
        "quote": quote,
        "filing": filing,
        "accession_number": accession,
        "line_start": line,
        "line_end": line,
    }


def research_output() -> dict[str, Any]:
    business = source_claim(
        "The business uses a membership format.",
        "membership format",
        "10-K",
        "annual-accession",
        3,
    )
    development = source_claim(
        "A new service launched during the quarter.",
        "launched a new service during the quarter",
        "Earnings release",
        "current-accession",
        2,
    )
    return {
        "business_model": [business],
        "competitive_position": [business],
        "catalysts": [development],
        "recent_developments": [development],
        "limitations": [],
    }


def financial_output() -> dict[str, Any]:
    return {
        "statement_analysis": [],
        "ratio_analysis": [],
        "quarterly_analysis": [],
        "peer_analysis": [],
        "valuation_insights": [],
        "calculator_requests": [],
        "limitations": [],
    }


def advisor_output() -> dict[str, Any]:
    return {
        "thesis": "The supplied operating evidence supports a neutral view.",
        "recommendation": "Hold",
        "deciding_number": "10x",
        "deciding_number_source": "Financial Analyst P/E arithmetic",
        "rationale": "The cited multiple is the deciding number.",
        "risks": [],
    }


def manager_output(failures: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "failures": failures or [],
        "overview": "The business uses a membership format (10-K, line 3).",
        "market_positioning_and_growth_outlook": "The launch can support growth.",
        "valuation_insights": "The supplied P/E is 10x.",
        "future_developments_and_strategic_recommendations": (
            "Monitor the new service."
        ),
        "investment_recommendation": "Hold; the deciding number is 10x.",
    }


class FakeRoleClient:
    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []

    def call(self, **kwargs: Any) -> dict[str, Any]:
        validate_role_request(kwargs["request"])
        self.calls.append(kwargs)
        if not self.outputs:
            raise AssertionError("No fake role output remains.")
        return self.outputs.pop(0)


class SourceAndCalculatorTests(unittest.TestCase):
    def test_extracts_full_document_business_and_mda_line_ranges(self) -> None:
        sections = extract_ten_k_sections(TEN_K_TEXT)

        self.assertEqual(sections["business"]["line_start"], 2)
        self.assertEqual(sections["business"]["line_end"], 3)
        self.assertIn("L3: The registrant sells", sections["business"]["text"])
        self.assertEqual(sections["md_and_a"]["line_start"], 6)
        self.assertEqual(sections["md_and_a"]["line_end"], 7)
        self.assertIn("L7: Revenue increased", sections["md_and_a"]["text"])

    def test_ignores_short_table_of_contents_sections_with_pipe_headings(self) -> None:
        text = """Table of Contents
Item 1 | Business | 4
Item 1A | Risk Factors | 8
Item 7 | Management's Discussion | 20
Item 7A | Market Risk | 30
ITEM 1. | BUSINESS
Business detail one.
Business detail two.
ITEM 1A. | RISK FACTORS
Risk detail.
ITEM 7. | MANAGEMENT'S DISCUSSION AND ANALYSIS
MD&A detail one.
MD&A detail two.
ITEM 7A. | QUANTITATIVE AND QUALITATIVE DISCLOSURES
"""
        sections = extract_ten_k_sections(text)

        self.assertEqual(sections["business"]["line_start"], 6)
        self.assertEqual(sections["business"]["line_end"], 8)
        self.assertEqual(sections["md_and_a"]["line_start"], 11)
        self.assertEqual(sections["md_and_a"]["line_end"], 13)

    def test_calculator_executes_growth_without_model_arithmetic(self) -> None:
        result = calculate_ratio_request(
            {
                "name": "Revenue growth",
                "operation": "growth",
                "operands": ["120", "100"],
                "operand_labels": ["current revenue", "prior revenue"],
                "operand_sources": ["tag A", "tag A"],
                "result_format": "percent",
            }
        )

        self.assertEqual(result["result"], "20.00%")
        self.assertEqual(result["arithmetic"], "(120 - 100) / 100 = 20.00%")


class RoleWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.run_started = datetime(2026, 10, 28, 21, 39, tzinfo=timezone.utc)
        self.filings = {
            "10-K": "annual-accession",
            "10-Q": "quarterly-accession",
            "8-K": "current-accession",
        }

    def test_report_has_required_first_two_lines(self) -> None:
        report = compile_report_markdown(
            manager_output(), self.filings, self.run_started
        )
        lines = report.splitlines()

        self.assertEqual(
            lines[0],
            "Filings read: 10-K (accession annual-accession); "
            "10-Q (accession quarterly-accession); 8-K Item 2.02 and "
            "Exhibit 99.1 (accession current-accession)",
        )
        self.assertEqual(lines[1], "Run time: 2026-10-28T21:39:00+00:00")
        for heading in (
            "## Overview",
            "## Market Positioning and Growth Outlook",
            "## Valuation Insights",
            "## Future Developments and Strategic Recommendations",
            "## Investment Recommendation",
        ):
            self.assertIn(heading, lines)

    def test_each_role_receives_manager_json_and_advisor_gets_only_two_outputs(
        self,
    ) -> None:
        client = FakeRoleClient(
            [
                research_output(),
                financial_output(),
                advisor_output(),
                manager_output(),
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            report_path = run_four_role_workflow(
                role_client=client,
                output_dir=Path(temporary),
                run_started=self.run_started,
                filings=self.filings,
                ten_k_text=TEN_K_TEXT,
                release_text=RELEASE_TEXT,
                financial_context={"step_4_facts": {}, "step_5_ratios": []},
            )

            self.assertTrue(report_path.is_file())

        self.assertEqual(
            [call["role"] for call in client.calls],
            [ROLE_RESEARCH, ROLE_FINANCIAL, ROLE_ADVISOR, ROLE_MANAGER],
        )
        for call in client.calls:
            self.assertEqual(
                set(call["request"]), {"task", "context", "expected_output"}
            )
        advisor_context = client.calls[2]["request"]["context"]
        self.assertEqual(
            set(advisor_context),
            {"research_analyst_output", "financial_analyst_output"},
        )

    def test_manager_returns_a_failed_part_to_its_role_only_once(self) -> None:
        failure = {
            "part": "Overview",
            "responsible_role": ROLE_RESEARCH,
            "problem": "The overview needs a clearer supported claim.",
            "required_correction": "Revise the supported overview claim.",
        }
        client = FakeRoleClient(
            [
                research_output(),
                financial_output(),
                advisor_output(),
                manager_output([failure]),
                research_output(),
                advisor_output(),
                manager_output(),
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_four_role_workflow(
                role_client=client,
                output_dir=Path(temporary),
                run_started=self.run_started,
                filings=self.filings,
                ten_k_text=TEN_K_TEXT,
                release_text=RELEASE_TEXT,
                financial_context={},
            )

        roles = [call["role"] for call in client.calls]
        self.assertEqual(roles.count(ROLE_RESEARCH), 2)
        self.assertEqual(roles.count(ROLE_FINANCIAL), 1)
        self.assertEqual(roles.count(ROLE_ADVISOR), 2)
        self.assertEqual(roles.count(ROLE_MANAGER), 2)

    def test_financial_analyst_can_request_one_calculator_pass(self) -> None:
        requested = financial_output()
        requested["calculator_requests"] = [
            {
                "name": "Revenue growth",
                "operation": "growth",
                "operands": ["120", "100"],
                "operand_labels": ["current revenue", "prior revenue"],
                "operand_sources": ["tag A current period", "tag A prior period"],
                "result_format": "percent",
            }
        ]
        client = FakeRoleClient(
            [
                research_output(),
                requested,
                financial_output(),
                advisor_output(),
                manager_output(),
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            run_four_role_workflow(
                role_client=client,
                output_dir=Path(temporary),
                run_started=self.run_started,
                filings=self.filings,
                ten_k_text=TEN_K_TEXT,
                release_text=RELEASE_TEXT,
                financial_context={},
            )

        roles = [call["role"] for call in client.calls]
        self.assertEqual(
            roles,
            [ROLE_RESEARCH, ROLE_FINANCIAL, ROLE_FINANCIAL, ROLE_ADVISOR, ROLE_MANAGER],
        )
        calculator_results = client.calls[2]["request"]["context"][
            "calculator_results"
        ]
        self.assertEqual(
            calculator_results[0]["arithmetic"],
            "(120 - 100) / 100 = 20.00%",
        )


if __name__ == "__main__":
    unittest.main()
