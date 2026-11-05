"""Fixed CrewAI Flow for the FIN 67110 equity-research agent team."""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

from crewai.flow import Flow, listen, start
from pydantic import BaseModel, Field


PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parents[1]
WORKSPACE_DIR = PACKAGE_DIR.parents[2]
if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from equity_research_data import (  # noqa: E402
    EquityResearchDataDesk,
    calculate_metrics,
    format_quarterly_release_metrics,
    parse_quarterly_release_metrics,
)
from research_roles import (  # noqa: E402
    ADVISOR_OUTPUT_SCHEMA,
    FINANCIAL_OUTPUT_SCHEMA,
    MANAGER_OUTPUT_SCHEMA,
    RESEARCH_OUTPUT_SCHEMA,
    REPORT_PARTS,
    ROLE_ADVISOR,
    ROLE_FINANCIAL,
    ROLE_MANAGER,
    ROLE_RESEARCH,
    compile_report_markdown,
    extract_ten_k_sections,
    number_document_lines,
    validate_research_citations,
    validate_role_request,
)

from equity_research_team.verifier import verify_run


ROLE_FILES = {
    ROLE_RESEARCH: "research_analyst.md",
    ROLE_FINANCIAL: "financial_analyst.md",
    ROLE_ADVISOR: "investment_advisor.md",
    ROLE_MANAGER: "strategy_manager.md",
    "Verifier": "verifier.md",
}

PART_TO_MANAGER_KEY = {
    "Overview": "overview",
    "Market Positioning and Growth Outlook": "market_positioning_and_growth_outlook",
    "Valuation Insights": "valuation_insights",
    "Future Developments and Strategic Recommendations": (
        "future_developments_and_strategic_recommendations"
    ),
    "Investment Recommendation": "investment_recommendation",
}

ROLE_TO_INSIGHT_PART = {
    ROLE_RESEARCH: "Overview",
    ROLE_FINANCIAL: "Valuation Insights",
    ROLE_ADVISOR: "Investment Recommendation",
}

INSIGHT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "line": {"type": "string"},
        "quote": {"type": "string"},
        "filing": {"type": "string", "enum": ["10-K", "Earnings release"]},
        "accession_number": {"type": "string"},
        "line_start": {"type": "integer"},
        "line_end": {"type": "integer"},
    },
    "required": [
        "line",
        "quote",
        "filing",
        "accession_number",
        "line_start",
        "line_end",
    ],
    "additionalProperties": False,
}


def _with_insight_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    result = deepcopy(dict(schema))
    result["properties"]["insight"] = deepcopy(INSIGHT_SCHEMA)
    result["required"].append("insight")
    return result


TEAM_RESEARCH_OUTPUT_SCHEMA = _with_insight_schema(RESEARCH_OUTPUT_SCHEMA)
TEAM_FINANCIAL_OUTPUT_SCHEMA = _with_insight_schema(FINANCIAL_OUTPUT_SCHEMA)
TEAM_ADVISOR_OUTPUT_SCHEMA = _with_insight_schema(ADVISOR_OUTPUT_SCHEMA)

CORRECTION_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "corrected_parts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "part": {"type": "string", "enum": list(REPORT_PARTS)},
                    "content": {"type": "string"},
                },
                "required": ["part", "content"],
                "additionalProperties": False,
            },
        },
        "insight": deepcopy(INSIGHT_SCHEMA),
    },
    "required": ["corrected_parts", "insight"],
    "additionalProperties": False,
}


NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:\$\s*)?\(?-?\d[\d,]*(?:\.\d+)?\)?(?:\s*(?:%|x|thousand|million|billion))?",
    re.IGNORECASE,
)


def release_first_paragraph(text: str) -> str:
    """Return the first sentence-like release paragraph after its headings."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for line in lines:
        if len(line) >= 60 and re.search(r"[.!?](?:[\"'’)]*)$", line):
            return line
    return lines[0] if lines else ""


def _number_signatures(text: str) -> set[str]:
    signatures: set[str] = set()
    for match in NUMBER_RE.finditer(text):
        value = re.sub(r"[\s,$()]", "", match.group(0)).casefold()
        if value.startswith("-"):
            value = value[1:]
        if value:
            signatures.add(value)
    return signatures


def _render_insight(insight: Mapping[str, Any]) -> str:
    line = str(insight.get("line", "")).strip()
    filing = str(insight.get("filing", "")).strip()
    accession = str(insight.get("accession_number", "")).strip()
    start = insight.get("line_start")
    end = insight.get("line_end")
    line_label = f"line {start}" if start == end else f"lines {start}-{end}"
    quote = " ".join(str(insight.get("quote", "")).split())
    return (
        f"{line} [{filing} accession {accession}, {line_label}; "
        f'exact line: "{quote}"]'
    )


def role_instructions(role: str) -> str:
    path = PROJECT_DIR / "roles" / ROLE_FILES[role]
    return path.read_text(encoding="utf-8").strip()


def _save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def _expected_research_output() -> dict[str, Any]:
    return {
        "business_model": "Claims with exact quotes and filing line citations",
        "competitive_position": "Claims with exact quotes and filing line citations",
        "catalysts": "Claims with exact quotes and filing line citations",
        "recent_developments": "Claims with exact quotes and filing line citations",
        "limitations": "Unsupported or unavailable points",
        "insight": (
            "One object. Its line starts with 'Insight:' and states a numeric filing-supported "
            "claim that the earnings release first paragraph does not state. Include the exact "
            "filing line, accession number, line range, and quote."
        ),
    }


def _expected_financial_output() -> dict[str, Any]:
    return {
        "statement_analysis": "Findings with number provenance",
        "ratio_analysis": "Findings with supplied arithmetic and definitions",
        "quarterly_analysis": "Findings with release line and period provenance",
        "peer_analysis": "Findings with peer filing provenance",
        "valuation_insights": "Price-based insights with supplied arithmetic",
        "calculator_requests": "An empty list; no additional model arithmetic is permitted",
        "limitations": "Unavailable or incomparable items",
        "insight": (
            "One object. Its line starts with 'Insight:' and states a numeric filing-supported "
            "claim that the earnings release first paragraph does not state. Include the exact "
            "filing line, accession number, line range, and quote."
        ),
    }


def _expected_advisor_output() -> dict[str, Any]:
    return {
        "thesis": "One evidence-bound thesis",
        "recommendation": "Exactly Buy, Hold, or Sell",
        "deciding_number": "Exactly one number from the analyst outputs",
        "deciding_number_source": "The analyst-output source of that number",
        "rationale": "Why the one number decides the recommendation",
        "risks": "Material risks already present in the analyst outputs",
        "insight": (
            "One numeric Insight line copied or derived only from an analyst output, with the "
            "same filing quote, accession number, and line range. It must not restate only a "
            "figure in the earnings release first paragraph."
        ),
    }


def _expected_manager_output() -> dict[str, Any]:
    return {
        "failures": "Any failing report part and one responsible role",
        "overview": "Overview prose",
        "market_positioning_and_growth_outlook": "Positioning and outlook prose",
        "valuation_insights": "Valuation prose",
        "future_developments_and_strategic_recommendations": "Forward view prose",
        "investment_recommendation": "Recommendation prose with one deciding number",
    }


class TeamState(BaseModel):
    """Only the data that fixed graph edges pass between nodes."""

    ticker: str = ""
    peers: list[str] = Field(default_factory=list)
    price: str = ""
    model: str = ""
    run_dir: str = ""
    report_path: str = ""
    verified_report_path: str = ""
    node_order: list[str] = Field(default_factory=list)
    role_call_counts: dict[str, int] = Field(default_factory=dict)
    research_request: dict[str, Any] = Field(default_factory=dict)
    financial_request: dict[str, Any] = Field(default_factory=dict)
    research_output: dict[str, Any] = Field(default_factory=dict)
    financial_output: dict[str, Any] = Field(default_factory=dict)
    advisor_output: dict[str, Any] = Field(default_factory=dict)
    manager_output: dict[str, Any] = Field(default_factory=dict)


class EquityResearchTeamFlow(Flow[TeamState]):
    """A fixed graph. No model selects the next node."""

    desk: Any = None
    role_client: Any = None

    def _run_dir(self) -> Path:
        if self.state.run_dir:
            return Path(self.state.run_dir)
        if self.desk is None:
            raise ValueError("The Steps node has no desk instance.")
        path = self.desk.ensure_output_dir()
        self.state.run_dir = str(path)
        return path

    def _record_node(self, name: str) -> None:
        print(f"Node: {name}")
        self.state.node_order.append(name)

    def _call_role(
        self,
        *,
        role: str,
        request: Mapping[str, Any],
        schema_name: str,
        output_schema: Mapping[str, Any],
        artifact_name: str,
        correction: bool = False,
    ) -> dict[str, Any]:
        if self.role_client is None:
            raise ValueError("No role client was supplied.")
        validate_role_request(request)
        calls = self.state.role_call_counts.get(role, 0) + 1
        if calls > 2:
            raise RuntimeError(f"{role} cannot run more than two times in one run.")
        self.state.role_call_counts[role] = calls
        if correction:
            print(f"Node: {role} (correction)")
        nodes_dir = self._run_dir() / "nodes"
        _save_json(nodes_dir / f"{artifact_name}_input.json", dict(request))
        output = self.role_client.call(
            role=role,
            instructions=role_instructions(role),
            request=request,
            schema_name=schema_name,
            output_schema=output_schema,
        )
        _save_json(nodes_dir / f"{artifact_name}_output.json", output)
        return output

    def _selected_filings(self) -> Mapping[str, Any]:
        if self.desk is None:
            raise ValueError("The desk is unavailable.")
        return self.desk.ensure_filings()

    def _ten_k_text(self) -> str:
        if self.desk is None:
            raise ValueError("The desk is unavailable.")
        text = self.desk.document_texts.get("10-K")
        if text is None:
            raise ValueError("The Steps node did not retain the saved 10-K text.")
        return text

    def _insight_issues(self, role: str, output: Mapping[str, Any]) -> list[str]:
        insight = output.get("insight")
        if not isinstance(insight, Mapping):
            return ["The output has no Insight object."]

        issues: list[str] = []
        line = str(insight.get("line", "")).strip()
        if not line.startswith("Insight:"):
            issues.append('The Insight line does not start with "Insight:".')
        insight_numbers = _number_signatures(line)
        if not insight_numbers:
            issues.append("The Insight line has no number for the Verifier to check.")

        filing = str(insight.get("filing", ""))
        sources = {
            "10-K": (
                self._ten_k_text().splitlines(),
                self._selected_filings()["10-K"].accession_number,
            ),
            "Earnings release": (
                self.desk.ensure_release_text().splitlines(),
                self._selected_filings()["8-K"].accession_number,
            ),
        }
        if filing not in sources:
            issues.append("The Insight cites neither the 10-K nor the earnings release.")
            return issues

        source_lines, expected_accession = sources[filing]
        if str(insight.get("accession_number", "")) != expected_accession:
            issues.append("The Insight has the wrong accession number.")
        start = insight.get("line_start")
        end = insight.get("line_end")
        if (
            not isinstance(start, int)
            or not isinstance(end, int)
            or start < 1
            or end < start
            or end > len(source_lines)
        ):
            issues.append("The Insight has an invalid filing line range.")
        else:
            excerpt = " ".join(source_lines[start - 1 : end])
            normalized_excerpt = " ".join(excerpt.split()).casefold()
            quote = " ".join(str(insight.get("quote", "")).split()).casefold()
            if not quote or quote not in normalized_excerpt:
                issues.append("The Insight quote is not on its cited filing line range.")
            if insight_numbers and not insight_numbers.issubset(_number_signatures(excerpt)):
                issues.append("The cited filing line does not contain every Insight number.")

        first_paragraph = release_first_paragraph(self.desk.ensure_release_text())
        paragraph_numbers = _number_signatures(first_paragraph)
        if insight_numbers and insight_numbers.issubset(paragraph_numbers):
            issues.append(
                "The Insight only restates a figure in the earnings release first paragraph."
            )
        return issues

    def _all_insight_issues(self) -> dict[str, list[str]]:
        outputs = {
            ROLE_RESEARCH: self.state.research_output,
            ROLE_FINANCIAL: self.state.financial_output,
            ROLE_ADVISOR: self.state.advisor_output,
        }
        return {
            role: self._insight_issues(role, output)
            for role, output in outputs.items()
        }

    def _set_role_insight(self, role: str, insight: Mapping[str, Any]) -> None:
        if role == ROLE_RESEARCH:
            self.state.research_output["insight"] = dict(insight)
        elif role == ROLE_FINANCIAL:
            self.state.financial_output["insight"] = dict(insight)
        elif role == ROLE_ADVISOR:
            self.state.advisor_output["insight"] = dict(insight)
        else:
            raise ValueError(f"Unknown Insight role: {role}")

    def _append_insights(self, manager_output: dict[str, Any]) -> None:
        outputs = {
            ROLE_RESEARCH: self.state.research_output,
            ROLE_FINANCIAL: self.state.financial_output,
            ROLE_ADVISOR: self.state.advisor_output,
        }
        for role, part in ROLE_TO_INSIGHT_PART.items():
            insight = outputs[role].get("insight")
            if not isinstance(insight, Mapping):
                continue
            key = PART_TO_MANAGER_KEY[part]
            content = str(manager_output.get(key, "")).strip()
            rendered = _render_insight(insight)
            if rendered not in content:
                manager_output[key] = f"{content}\n\n{rendered}".strip()

    @start()
    def run_steps(self) -> str:
        self._record_node("Steps")
        if self.desk is None:
            raise ValueError("The Flow requires an EquityResearchDataDesk.")
        input_payload = {
            "task": "Run the seven deterministic SEC desk tools in numeric order.",
            "context": {
                "ticker": self.state.ticker,
                "peers": self.state.peers,
                "price": self.state.price,
            },
            "expected_output": "Saved filing texts, facts, and deterministic arithmetic.",
        }
        for step_number in range(1, 8):
            getattr(self.desk, f"step_{step_number}")()
        run_dir = self._run_dir()
        _save_json(run_dir / "nodes" / "01_steps_input.json", input_payload)
        output_payload = {
            "run_dir": str(run_dir),
            "saved_files": sorted(path.name for path in run_dir.iterdir() if path.is_file()),
            "completed_steps": list(range(1, 8)),
        }
        _save_json(run_dir / "nodes" / "01_steps_output.json", output_payload)
        return str(run_dir)

    @listen(run_steps)
    def research_analyst(self, _: str) -> dict[str, Any]:
        self._record_node(ROLE_RESEARCH)
        selected = self._selected_filings()
        sections = extract_ten_k_sections(self._ten_k_text())
        release_text = self.desk.ensure_release_text()
        request = {
            "task": (
                "Analyze the supplied filing sections for the business model, competitive "
                "position, catalysts, risks, and recent developments."
            ),
            "context": {
                "ten_k": {
                    "accession_number": selected["10-K"].accession_number,
                    "business_section": sections["business"],
                    "md_and_a_section": sections["md_and_a"],
                },
                "earnings_release": {
                    "accession_number": selected["8-K"].accession_number,
                    "text": number_document_lines(release_text),
                    "first_paragraph": release_first_paragraph(release_text),
                },
            },
            "expected_output": _expected_research_output(),
        }
        self.state.research_request = request
        self.state.research_output = self._call_role(
            role=ROLE_RESEARCH,
            request=request,
            schema_name="research_analyst_output",
            output_schema=TEAM_RESEARCH_OUTPUT_SCHEMA,
            artifact_name="02_research_analyst",
        )
        return self.state.research_output

    @listen(research_analyst)
    def financial_analyst(self, _: Mapping[str, Any]) -> dict[str, Any]:
        self._record_node(ROLE_FINANCIAL)
        selected = self._selected_filings()
        fact_set = self.desk.ensure_fact_set()
        release_text = self.desk.ensure_release_text()
        ten_k_sections = extract_ten_k_sections(self._ten_k_text())
        peer_context = []
        for ticker in self.state.peers:
            peer_facts = self.desk.peer_fact_sets.get(ticker)
            if peer_facts is None:
                raise ValueError(f"Step 7 did not retain facts for peer {ticker}.")
            peer_context.append(
                {
                    "facts": peer_facts,
                    "operating_margin": dict(calculate_metrics(peer_facts, None))[
                        "Operating margin"
                    ],
                }
            )
        request = {
            "task": (
                "Analyze the saved facts and the deterministic arithmetic. Preserve every "
                "source, tag or line, period, input, and ratio definition."
            ),
            "context": {
                "step_4_facts": fact_set,
                "step_5_ratios": [
                    {"name": name, "arithmetic": arithmetic}
                    for name, arithmetic in calculate_metrics(fact_set, self.desk.price)
                ],
                "step_6_quarter": {
                    "filing": "8-K Exhibit 99.1",
                    "accession_number": selected["8-K"].accession_number,
                    "deterministic_output": format_quarterly_release_metrics(
                        parse_quarterly_release_metrics(release_text),
                        selected["8-K"].accession_number,
                    ),
                    "line_numbered_earnings_release": number_document_lines(release_text),
                    "earnings_release_first_paragraph": release_first_paragraph(
                        release_text
                    ),
                },
                "ten_k_md_and_a_for_insight": ten_k_sections["md_and_a"],
                "step_7_peers": peer_context,
            },
            "expected_output": _expected_financial_output(),
        }
        self.state.financial_request = request
        output = self._call_role(
            role=ROLE_FINANCIAL,
            request=request,
            schema_name="financial_analyst_output",
            output_schema=TEAM_FINANCIAL_OUTPUT_SCHEMA,
            artifact_name="03_financial_analyst",
        )
        if output.get("calculator_requests"):
            raise RuntimeError(
                "The Financial Analyst requested model arithmetic; the seven steps already "
                "supply all permitted calculations."
            )
        self.state.financial_output = output
        return output

    @listen(financial_analyst)
    def investment_advisor(self, _: Mapping[str, Any]) -> dict[str, Any]:
        self._record_node(ROLE_ADVISOR)
        request = {
            "task": (
                "Create one thesis and one Buy, Hold, or Sell recommendation from the two "
                "analyst outputs. Use exactly one deciding number."
            ),
            "context": {
                "research_analyst_output": self.state.research_output,
                "financial_analyst_output": self.state.financial_output,
                "earnings_release_first_paragraph": release_first_paragraph(
                    self.desk.ensure_release_text()
                ),
            },
            "expected_output": _expected_advisor_output(),
        }
        self.state.advisor_output = self._call_role(
            role=ROLE_ADVISOR,
            request=request,
            schema_name="investment_advisor_output",
            output_schema=TEAM_ADVISOR_OUTPUT_SCHEMA,
            artifact_name="04_investment_advisor",
        )
        return self.state.advisor_output

    def _manager_request(self) -> dict[str, Any]:
        citation_issues = validate_research_citations(
            self.state.research_output,
            ten_k_text=self._ten_k_text(),
            release_text=self.desk.ensure_release_text(),
            ten_k_accession=self._selected_filings()["10-K"].accession_number,
            release_accession=self._selected_filings()["8-K"].accession_number,
        )
        insight_issues = self._all_insight_issues()
        return {
            "task": "Check and draft the five required report parts.",
            "context": {
                "research_analyst_output": self.state.research_output,
                "financial_analyst_output": self.state.financial_output,
                "investment_advisor_output": self.state.advisor_output,
                "deterministic_citation_issues": citation_issues,
                "deterministic_insight_issues": insight_issues,
                "earnings_release_first_paragraph": release_first_paragraph(
                    self.desk.ensure_release_text()
                ),
                "final_pass": False,
            },
            "expected_output": _expected_manager_output(),
        }

    def _correct_role(
        self, role: str, failures: Sequence[Mapping[str, Any]]
    ) -> list[dict[str, str]]:
        expected = {
            "corrected_parts": (
                "One corrected Markdown-ready part for each failed part in manager_feedback."
            ),
            "insight": (
                "The role's complete corrected Insight object. Its line starts with Insight:, "
                "contains a number, cites an exact filing line, and does not only restate a "
                "figure in the earnings release first paragraph."
            ),
        }
        if role == ROLE_RESEARCH:
            request = {
                "task": "Correct the returned failing report parts one time.",
                "context": {
                    "original_assignment": self.state.research_request,
                    "previous_output": self.state.research_output,
                    "manager_feedback": list(failures),
                },
                "expected_output": expected,
            }
            output = self._call_role(
                role=role,
                request=request,
                schema_name="research_analyst_correction",
                output_schema=CORRECTION_OUTPUT_SCHEMA,
                artifact_name="05a_research_analyst_correction",
                correction=True,
            )
        elif role == ROLE_FINANCIAL:
            request = {
                "task": "Correct the returned failing report parts one time.",
                "context": {
                    "original_assignment": self.state.financial_request,
                    "previous_output": self.state.financial_output,
                    "manager_feedback": list(failures),
                },
                "expected_output": expected,
            }
            output = self._call_role(
                role=role,
                request=request,
                schema_name="financial_analyst_correction",
                output_schema=CORRECTION_OUTPUT_SCHEMA,
                artifact_name="05b_financial_analyst_correction",
                correction=True,
            )
        elif role == ROLE_ADVISOR:
            request = {
                "task": (
                    "Correct the returned report part one time using the current analyst "
                    "outputs and exactly one deciding number."
                ),
                "context": {
                    "research_analyst_output": self.state.research_output,
                    "financial_analyst_output": self.state.financial_output,
                    "previous_output": self.state.advisor_output,
                    "manager_feedback": list(failures),
                },
                "expected_output": expected,
            }
            output = self._call_role(
                role=role,
                request=request,
                schema_name="investment_advisor_correction",
                output_schema=CORRECTION_OUTPUT_SCHEMA,
                artifact_name="05c_investment_advisor_correction",
                correction=True,
            )
        else:
            raise ValueError(f"Unknown correction role: {role}")

        assigned_parts = {str(item.get("part")) for item in failures}
        corrected_parts = [
            {"part": str(item.get("part", "")), "content": str(item.get("content", ""))}
            for item in output.get("corrected_parts", [])
            if isinstance(item, Mapping)
            and item.get("part") in assigned_parts
            and str(item.get("content", "")).strip()
        ]
        returned_parts = {item["part"] for item in corrected_parts}
        missing = sorted(assigned_parts - returned_parts)
        if missing:
            raise RuntimeError(
                f"{role} did not return corrected content for: {', '.join(missing)}."
            )
        insight = output.get("insight")
        if not isinstance(insight, Mapping):
            raise RuntimeError(f"{role} did not return a corrected Insight object.")
        self._set_role_insight(role, insight)
        return corrected_parts

    @listen(investment_advisor)
    def strategy_manager(self, _: Mapping[str, Any]) -> str:
        self._record_node(ROLE_MANAGER)
        initial_request = self._manager_request()
        manager_output = self._call_role(
            role=ROLE_MANAGER,
            request=initial_request,
            schema_name="strategy_manager_review",
            output_schema=MANAGER_OUTPUT_SCHEMA,
            artifact_name="05_strategy_manager_review",
        )
        failures = [
            dict(item)
            for item in manager_output.get("failures", [])
            if isinstance(item, Mapping)
        ]
        citation_issues = initial_request["context"]["deterministic_citation_issues"]
        if citation_issues and not any(
            item.get("responsible_role") == ROLE_RESEARCH for item in failures
        ):
            failures.append(
                {
                    "part": "Overview",
                    "responsible_role": ROLE_RESEARCH,
                    "problem": "; ".join(str(item) for item in citation_issues),
                    "required_correction": "Restore exact quotes, lines, and accession numbers.",
                }
            )
        insight_issues = initial_request["context"]["deterministic_insight_issues"]
        for role in (ROLE_RESEARCH, ROLE_FINANCIAL, ROLE_ADVISOR):
            role_issues = insight_issues.get(role, [])
            if role_issues and not any(
                item.get("responsible_role") == role
                and item.get("part") == ROLE_TO_INSIGHT_PART[role]
                for item in failures
            ):
                failures.append(
                    {
                        "part": ROLE_TO_INSIGHT_PART[role],
                        "responsible_role": role,
                        "problem": "; ".join(str(item) for item in role_issues),
                        "required_correction": (
                            "Return one numeric Insight line with an exact filing line. "
                            "Do not only restate a figure in the earnings release first paragraph."
                        ),
                    }
                )
        valid_parts = set(REPORT_PARTS)
        failures = [item for item in failures if item.get("part") in valid_parts]

        if failures:
            failures_by_role = {
                role: [item for item in failures if item.get("responsible_role") == role]
                for role in (ROLE_RESEARCH, ROLE_FINANCIAL, ROLE_ADVISOR)
            }
            analyst_changed = False
            for role in (ROLE_RESEARCH, ROLE_FINANCIAL):
                if failures_by_role[role]:
                    for corrected in self._correct_role(role, failures_by_role[role]):
                        manager_output[PART_TO_MANAGER_KEY[corrected["part"]]] = corrected[
                            "content"
                        ]
                    analyst_changed = True
            if failures_by_role[ROLE_ADVISOR] or analyst_changed:
                advisor_feedback = failures_by_role[ROLE_ADVISOR] or [
                    {
                        "part": "Investment Recommendation",
                        "responsible_role": ROLE_ADVISOR,
                        "problem": "An analyst output changed during the one correction pass.",
                        "required_correction": (
                            "Reconcile the thesis and deciding number with the current outputs."
                        ),
                    }
                ]
                for corrected in self._correct_role(ROLE_ADVISOR, advisor_feedback):
                    manager_output[PART_TO_MANAGER_KEY[corrected["part"]]] = corrected["content"]

        manager_output["failures"] = []
        self._append_insights(manager_output)
        self.state.manager_output = manager_output
        _save_json(
            self._run_dir() / "nodes" / "05_strategy_manager_compiled_output.json",
            manager_output,
        )
        selected = self._selected_filings()
        report = compile_report_markdown(
            manager_output,
            {
                "10-K": selected["10-K"].accession_number,
                "10-Q": selected["10-Q"].accession_number,
                "8-K": selected["8-K"].accession_number,
            },
            self.desk.run_started,
        )
        report_path = self._run_dir() / "equity_research_report.md"
        report_path.write_text(report, encoding="utf-8")
        self.state.report_path = str(report_path)
        return str(report_path)

    @listen(strategy_manager)
    def verifier(self, report_path: str) -> str:
        self._record_node("Verifier")
        self.state.role_call_counts["Verifier"] = 1
        verified_path = verify_run(
            run_dir=self._run_dir(),
            report_path=Path(report_path),
            output_dir=self._run_dir(),
            semantic_client=self.role_client,
            verifier_instructions=role_instructions("Verifier"),
        )
        self.state.verified_report_path = str(verified_path)
        _save_json(
            self._run_dir() / "node_order.json",
            {
                "node_order": self.state.node_order,
                "role_call_counts": self.state.role_call_counts,
            },
        )
        print(f"Verified report: {verified_path}")
        return str(verified_path)


def build_desk(
    *,
    ticker: str,
    peers: Sequence[str],
    price: Decimal | None,
    client: Any,
    base_dir: Path = WORKSPACE_DIR,
) -> EquityResearchDataDesk:
    return EquityResearchDataDesk(
        client=client,
        ticker=ticker,
        peers=peers,
        price=price,
        base_dir=base_dir,
    )


def new_verification_output_dir(run_dir: Path) -> Path:
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S-%f")
    output_dir = run_dir / "verifications" / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    return output_dir
