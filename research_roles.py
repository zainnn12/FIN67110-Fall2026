"""Run the four-role equity-research workflow after the seven data steps.

The module keeps orchestration deterministic. Each model receives one JSON
object with exactly three top-level keys: task, context, and expected_output.
The official OpenAI Python SDK is imported only when the role client is built.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol


DEFAULT_OPENAI_MODEL = "gpt-6-astra"

ROLE_RESEARCH = "Research Analyst"
ROLE_FINANCIAL = "Financial Analyst"
ROLE_ADVISOR = "Investment Advisor"
ROLE_MANAGER = "Strategy Manager"

REPORT_PARTS = (
    "Overview",
    "Market Positioning and Growth Outlook",
    "Valuation Insights",
    "Future Developments and Strategic Recommendations",
    "Investment Recommendation",
)


class RoleWorkflowError(RuntimeError):
    """A concise error from the model-driven workflow."""


class StructuredRoleClient(Protocol):
    """Interface used by the workflow and its unit tests."""

    def call(
        self,
        *,
        role: str,
        instructions: str,
        request: Mapping[str, Any],
        schema_name: str,
        output_schema: Mapping[str, Any],
    ) -> dict[str, Any]: ...


def _strict_object(properties: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


SOURCE_CLAIM_SCHEMA = _strict_object(
    {
        "claim": {"type": "string"},
        "quote": {"type": "string"},
        "filing": {
            "type": "string",
            "enum": ["10-K", "Earnings release"],
        },
        "accession_number": {"type": "string"},
        "line_start": {"type": "integer"},
        "line_end": {"type": "integer"},
    }
)

RESEARCH_OUTPUT_SCHEMA = _strict_object(
    {
        "business_model": {
            "type": "array",
            "items": SOURCE_CLAIM_SCHEMA,
        },
        "competitive_position": {
            "type": "array",
            "items": SOURCE_CLAIM_SCHEMA,
        },
        "catalysts": {
            "type": "array",
            "items": SOURCE_CLAIM_SCHEMA,
        },
        "recent_developments": {
            "type": "array",
            "items": SOURCE_CLAIM_SCHEMA,
        },
        "limitations": {"type": "array", "items": {"type": "string"}},
    }
)

NUMBER_EVIDENCE_SCHEMA = _strict_object(
    {
        "metric": {"type": "string"},
        "value": {"type": "string"},
        "filing": {"type": "string"},
        "accession_number": {"type": "string"},
        "source_reference": {"type": "string"},
        "period": {"type": "string"},
    }
)

FINANCIAL_FINDING_SCHEMA = _strict_object(
    {
        "conclusion": {"type": "string"},
        "evidence": {
            "type": "array",
            "items": NUMBER_EVIDENCE_SCHEMA,
        },
        "ratio_arithmetic": {"type": "string"},
        "definition": {"type": "string"},
    }
)

CALCULATOR_REQUEST_SCHEMA = _strict_object(
    {
        "name": {"type": "string"},
        "operation": {
            "type": "string",
            "enum": [
                "divide",
                "growth",
                "subtract",
                "sum_then_divide",
                "average_then_divide",
            ],
        },
        "operands": {"type": "array", "items": {"type": "string"}},
        "operand_labels": {
            "type": "array",
            "items": {"type": "string"},
        },
        "operand_sources": {
            "type": "array",
            "items": {"type": "string"},
        },
        "result_format": {
            "type": "string",
            "enum": ["percent", "multiple", "number", "currency"],
        },
    }
)

FINANCIAL_OUTPUT_SCHEMA = _strict_object(
    {
        "statement_analysis": {
            "type": "array",
            "items": FINANCIAL_FINDING_SCHEMA,
        },
        "ratio_analysis": {
            "type": "array",
            "items": FINANCIAL_FINDING_SCHEMA,
        },
        "quarterly_analysis": {
            "type": "array",
            "items": FINANCIAL_FINDING_SCHEMA,
        },
        "peer_analysis": {
            "type": "array",
            "items": FINANCIAL_FINDING_SCHEMA,
        },
        "valuation_insights": {
            "type": "array",
            "items": FINANCIAL_FINDING_SCHEMA,
        },
        "calculator_requests": {
            "type": "array",
            "items": CALCULATOR_REQUEST_SCHEMA,
        },
        "limitations": {"type": "array", "items": {"type": "string"}},
    }
)

ADVISOR_OUTPUT_SCHEMA = _strict_object(
    {
        "thesis": {"type": "string"},
        "recommendation": {
            "type": "string",
            "enum": ["Buy", "Hold", "Sell"],
        },
        "deciding_number": {"type": "string"},
        "deciding_number_source": {"type": "string"},
        "rationale": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
    }
)

FAILURE_SCHEMA = _strict_object(
    {
        "part": {"type": "string", "enum": list(REPORT_PARTS)},
        "responsible_role": {
            "type": "string",
            "enum": [ROLE_RESEARCH, ROLE_FINANCIAL, ROLE_ADVISOR],
        },
        "problem": {"type": "string"},
        "required_correction": {"type": "string"},
    }
)

MANAGER_OUTPUT_SCHEMA = _strict_object(
    {
        "failures": {"type": "array", "items": FAILURE_SCHEMA},
        "overview": {"type": "string"},
        "market_positioning_and_growth_outlook": {"type": "string"},
        "valuation_insights": {"type": "string"},
        "future_developments_and_strategic_recommendations": {
            "type": "string"
        },
        "investment_recommendation": {"type": "string"},
    }
)


RESEARCH_INSTRUCTIONS = """You are the Research Analyst in a four-role equity-research team.
Use only the JSON message sent by the Strategy Manager. Analyze only the supplied
10-K Business section, 10-K MD&A section, and earnings release. Cover the business
model, competitive position, catalysts, and recent developments. Every claim must
include an exact supporting quote and the supplied filing name, accession number,
and full-document line number or line range. Do not use outside knowledge. Do not
make a financial recommendation. If the sources do not support a point, put the
gap in limitations instead of inferring it. Return only the required structured
output."""

FINANCIAL_INSTRUCTIONS = """You are the Financial Analyst in a four-role equity-research team.
Use only the JSON message sent by the Strategy Manager. Analyze the statement facts
from Step 4, the deterministic ratios from Step 5, the quarter from Step 6, and the
peer facts from Step 7. Every number in your conclusions must have an evidence item
that states its filing and accession number, its line or XBRL tag, and its period.
Every ratio must reproduce arithmetic supplied by the deterministic calculator.
Never calculate, estimate, round, or derive a ratio yourself. If another ratio is
material, request it through calculator_requests and omit that ratio conclusion
until the calculator result is returned. State the definition used whenever the
filing supplies two possible definitions or components. Do not use outside
knowledge. Return only the required structured output."""

ADVISOR_INSTRUCTIONS = """You are the Investment Advisor in a four-role equity-research team.
Use only the Research Analyst output and Financial Analyst output in the JSON
context. Use no filings, raw facts, market knowledge, or assumptions that are not
in those two outputs. Produce one thesis and exactly one Buy, Hold, or Sell
recommendation. Identify exactly one deciding number, preserve its source, and
explain why it determines the recommendation. Return only the required structured
output."""

MANAGER_INSTRUCTIONS = """You are the Strategy Manager in a four-role equity-research team.
Use only the role outputs in the JSON context. Check that these five report parts
are present and mutually consistent: Overview; Market Positioning and Growth
Outlook; Valuation Insights; Future Developments and Strategic Recommendations;
Investment Recommendation. Check that cited claims remain attached to their
quotes, that numbers retain filing and line or tag and period provenance, that
ratios retain calculator arithmetic, and that the recommendation uses exactly one
deciding number. Assign each failing part to the Research Analyst, Financial
Analyst, or Investment Advisor. Do not invent facts, numbers, citations, or
arithmetic. Also draft or compile each report part in Markdown-ready prose without
adding section headings. Preserve citations and material conditions. On a final
pass after one correction opportunity, compile the best supported report and list
any remaining defect in failures and in the relevant prose. Return only the
required structured output."""


class OpenAIRoleClient:
    """Call role models with the official OpenAI Python SDK."""

    def __init__(self, api_key: str, model: str = DEFAULT_OPENAI_MODEL) -> None:
        if not api_key.strip():
            raise RoleWorkflowError("API_KEY is empty in .env.")
        if not model.strip():
            raise RoleWorkflowError("The OpenAI model name is empty.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RoleWorkflowError(
                "The openai package is not installed. Install requirements.txt."
            ) from exc
        self._client = OpenAI(api_key=api_key.strip())
        self.model = model.strip()

    def call(
        self,
        *,
        role: str,
        instructions: str,
        request: Mapping[str, Any],
        schema_name: str,
        output_schema: Mapping[str, Any],
    ) -> dict[str, Any]:
        validate_role_request(request)
        print(f"\nRole: {role}")
        try:
            response = self._client.responses.create(
                model=self.model,
                instructions=instructions,
                input=json.dumps(request, ensure_ascii=False),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": dict(output_schema),
                    }
                },
            )
        except Exception as exc:
            raise RoleWorkflowError(f"{role} model call failed: {exc}") from exc

        raw_output = getattr(response, "output_text", "")
        if not raw_output:
            raise RoleWorkflowError(f"{role} returned no structured text output.")
        try:
            parsed = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise RoleWorkflowError(f"{role} returned invalid JSON.") from exc
        if not isinstance(parsed, dict):
            raise RoleWorkflowError(f"{role} returned a non-object JSON value.")
        return parsed


def validate_role_request(request: Mapping[str, Any]) -> None:
    """Require the manager-to-role JSON envelope."""
    required = {"task", "context", "expected_output"}
    if set(request) != required:
        raise RoleWorkflowError(
            "Each role request must contain only task, context, and expected_output."
        )
    if not isinstance(request["task"], str) or not request["task"].strip():
        raise RoleWorkflowError("A role request has an empty task.")
    if not isinstance(request["context"], Mapping):
        raise RoleWorkflowError("A role request context must be a JSON object.")
    if not isinstance(request["expected_output"], Mapping):
        raise RoleWorkflowError("A role expected_output must be a JSON object.")


def _is_heading(line: str, item: str, title_word: str | None = None) -> bool:
    normalized = line.strip().replace("’", "'")
    pattern = rf"^item\s+{re.escape(item)}\b[.\s:—–-]*"
    match = re.match(pattern, normalized, flags=re.IGNORECASE)
    if not match:
        return False
    if title_word is None:
        return True
    return title_word.casefold() in normalized[match.end() :].casefold()


def extract_ten_k_sections(text: str) -> dict[str, dict[str, Any]]:
    """Extract Item 1 and Item 7 while preserving full-document line numbers."""
    lines = text.splitlines()

    def section(
        start_item: str,
        title_word: str,
        end_item: str,
        label: str,
    ) -> dict[str, Any]:
        starts = [
            index
            for index, line in enumerate(lines)
            if _is_heading(line, start_item, title_word)
        ]
        if not starts:
            raise RoleWorkflowError(f"Could not find the 10-K {label} heading.")
        candidates: list[tuple[int, int]] = []
        for possible_start in starts:
            possible_ends = [
                index
                for index in range(possible_start + 1, len(lines))
                if _is_heading(lines[index], end_item)
            ]
            if possible_ends:
                candidates.append((possible_start, possible_ends[0]))
        if not candidates:
            raise RoleWorkflowError(f"Could not find the end of the 10-K {label} section.")
        start, end = max(candidates, key=lambda pair: pair[1] - pair[0])
        numbered = "\n".join(
            f"L{index + 1}: {lines[index]}" for index in range(start, end)
        )
        return {
            "label": label,
            "line_start": start + 1,
            "line_end": end,
            "text": numbered,
        }

    return {
        "business": section("1", "business", "1A", "Business"),
        "md_and_a": section("7", "management", "7A", "MD&A"),
    }


def number_document_lines(text: str) -> str:
    return "\n".join(
        f"L{index}: {line}" for index, line in enumerate(text.splitlines(), start=1)
    )


def _normalized_quote(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def validate_research_citations(
    output: Mapping[str, Any],
    *,
    ten_k_text: str,
    release_text: str,
    ten_k_accession: str,
    release_accession: str,
) -> list[str]:
    """Check line ranges, accession numbers, and exact quotes deterministically."""
    sources = {
        "10-K": (ten_k_text.splitlines(), ten_k_accession),
        "Earnings release": (release_text.splitlines(), release_accession),
    }
    issues: list[str] = []
    for category in (
        "business_model",
        "competitive_position",
        "catalysts",
        "recent_developments",
    ):
        claims = output.get(category)
        if not isinstance(claims, list) or not claims:
            issues.append(f"{category} has no supported claim.")
            continue
        for claim_index, claim in enumerate(claims, start=1):
            if not isinstance(claim, Mapping):
                issues.append(f"{category} claim {claim_index} is not an object.")
                continue
            filing = claim.get("filing")
            if filing not in sources:
                issues.append(f"{category} claim {claim_index} has an invalid filing.")
                continue
            lines, accession = sources[str(filing)]
            if claim.get("accession_number") != accession:
                issues.append(
                    f"{category} claim {claim_index} has the wrong accession number."
                )
            start = claim.get("line_start")
            end = claim.get("line_end")
            if (
                not isinstance(start, int)
                or not isinstance(end, int)
                or start < 1
                or end < start
                or end > len(lines)
            ):
                issues.append(f"{category} claim {claim_index} has invalid lines.")
                continue
            source_excerpt = _normalized_quote(" ".join(lines[start - 1 : end]))
            quote = _normalized_quote(str(claim.get("quote", "")))
            if not quote or quote not in source_excerpt:
                issues.append(
                    f"{category} claim {claim_index} quote is not on its cited line range."
                )
    return issues


def _decimal_text(value: Decimal) -> str:
    return f"{value:,.8f}".rstrip("0").rstrip(".")


def _format_result(value: Decimal, result_format: str) -> str:
    if result_format == "percent":
        return f"{value * Decimal(100):,.2f}%"
    if result_format == "multiple":
        return f"{_decimal_text(value)}x"
    if result_format == "currency":
        sign = "-" if value < 0 else ""
        return f"{sign}${_decimal_text(abs(value))}"
    return _decimal_text(value)


def calculate_ratio_request(request: Mapping[str, Any]) -> dict[str, Any]:
    """Execute an analyst ratio request without model arithmetic."""
    try:
        operands = [Decimal(str(value)) for value in request["operands"]]
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise RoleWorkflowError("A calculator request has an invalid operand.") from exc
    if not operands or any(not value.is_finite() for value in operands):
        raise RoleWorkflowError("Calculator operands must be finite numbers.")

    operation = request.get("operation")
    if operation in {"divide", "growth", "subtract"} and len(operands) != 2:
        raise RoleWorkflowError(f"Calculator operation {operation} requires 2 operands.")
    if operation == "sum_then_divide" and len(operands) < 3:
        raise RoleWorkflowError("sum_then_divide requires at least 3 operands.")
    if operation == "average_then_divide" and len(operands) < 3:
        raise RoleWorkflowError("average_then_divide requires at least 3 operands.")

    if operation == "divide":
        if operands[1] == 0:
            raise RoleWorkflowError("The calculator cannot divide by zero.")
        result = operands[0] / operands[1]
        arithmetic = f"{_decimal_text(operands[0])} / {_decimal_text(operands[1])}"
    elif operation == "growth":
        if operands[1] == 0:
            raise RoleWorkflowError("The calculator cannot use a zero prior value.")
        result = (operands[0] - operands[1]) / operands[1]
        arithmetic = (
            f"({_decimal_text(operands[0])} - {_decimal_text(operands[1])}) / "
            f"{_decimal_text(operands[1])}"
        )
    elif operation == "subtract":
        result = operands[0] - operands[1]
        arithmetic = f"{_decimal_text(operands[0])} - {_decimal_text(operands[1])}"
    elif operation == "sum_then_divide":
        denominator = operands[-1]
        if denominator == 0:
            raise RoleWorkflowError("The calculator cannot divide by zero.")
        result = sum(operands[:-1], Decimal(0)) / denominator
        sum_text = " + ".join(_decimal_text(value) for value in operands[:-1])
        arithmetic = f"({sum_text}) / {_decimal_text(denominator)}"
    elif operation == "average_then_divide":
        average_values = operands[1:]
        average = sum(average_values, Decimal(0)) / Decimal(len(average_values))
        if average == 0:
            raise RoleWorkflowError("The calculator cannot divide by a zero average.")
        result = operands[0] / average
        average_text = " + ".join(_decimal_text(value) for value in average_values)
        arithmetic = (
            f"{_decimal_text(operands[0])} / "
            f"(({average_text}) / {len(average_values)})"
        )
    else:
        raise RoleWorkflowError(f"Unknown calculator operation: {operation}")

    result_format = str(request.get("result_format", "number"))
    formatted = _format_result(result, result_format)
    return {
        "name": str(request.get("name", "Requested ratio")),
        "operation": operation,
        "operand_labels": list(request.get("operand_labels", [])),
        "operand_sources": list(request.get("operand_sources", [])),
        "arithmetic": f"{arithmetic} = {formatted}",
        "result": formatted,
    }


def _expected_research_output() -> dict[str, Any]:
    return {
        "business_model": "Claims with exact quotes and filing line citations",
        "competitive_position": "Claims with exact quotes and filing line citations",
        "catalysts": "Claims with exact quotes and filing line citations",
        "recent_developments": "Claims with exact quotes and filing line citations",
        "limitations": "Unsupported or unavailable points",
    }


def _expected_financial_output() -> dict[str, Any]:
    return {
        "statement_analysis": "Findings with number provenance",
        "ratio_analysis": "Findings with calculator arithmetic",
        "quarterly_analysis": "Findings with release line and period provenance",
        "peer_analysis": "Findings with peer filing provenance",
        "valuation_insights": "Price-based insights with arithmetic",
        "calculator_requests": "Only additional ratios needed",
        "limitations": "Unavailable or incomparable items",
    }


def _expected_advisor_output() -> dict[str, Any]:
    return {
        "thesis": "One evidence-bound thesis",
        "recommendation": "Exactly Buy, Hold, or Sell",
        "deciding_number": "Exactly one number from the analyst outputs",
        "deciding_number_source": "The analyst-output source of that number",
        "rationale": "Why the one number decides the recommendation",
        "risks": "Material risks already present in the analyst outputs",
    }


def _expected_manager_output() -> dict[str, Any]:
    return {
        "failures": "Any failing report part and its responsible role",
        "overview": "Overview prose",
        "market_positioning_and_growth_outlook": "Positioning and outlook prose",
        "valuation_insights": "Valuation prose",
        "future_developments_and_strategic_recommendations": "Forward view prose",
        "investment_recommendation": "Recommendation prose with one deciding number",
    }


def _run_financial_role(
    role_client: StructuredRoleClient,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    output = role_client.call(
        role=ROLE_FINANCIAL,
        instructions=FINANCIAL_INSTRUCTIONS,
        request=request,
        schema_name="financial_analyst_output",
        output_schema=FINANCIAL_OUTPUT_SCHEMA,
    )
    calculator_requests = output.get("calculator_requests", [])
    if not calculator_requests:
        return output
    if not isinstance(calculator_requests, list):
        raise RoleWorkflowError("Financial Analyst calculator_requests is not a list.")
    calculator_results = [
        calculate_ratio_request(item)
        for item in calculator_requests
        if isinstance(item, Mapping)
    ]
    follow_up = {
        "task": (
            "Complete the financial analysis with the deterministic calculator "
            "results. Do not request the same calculation again."
        ),
        "context": {
            "manager_assignment": dict(request),
            "previous_financial_output": output,
            "calculator_results": calculator_results,
        },
        "expected_output": _expected_financial_output(),
    }
    completed = role_client.call(
        role=ROLE_FINANCIAL,
        instructions=FINANCIAL_INSTRUCTIONS,
        request=follow_up,
        schema_name="financial_analyst_output_after_calculator",
        output_schema=FINANCIAL_OUTPUT_SCHEMA,
    )
    if completed.get("calculator_requests"):
        raise RoleWorkflowError(
            "Financial Analyst requested more calculator work after one calculator pass."
        )
    return completed


def _manager_review_request(
    research_output: Mapping[str, Any],
    financial_output: Mapping[str, Any],
    advisor_output: Mapping[str, Any],
    citation_issues: Sequence[str],
    *,
    final_pass: bool,
) -> dict[str, Any]:
    task = (
        "Compile the final five-part report after the one allowed correction pass."
        if final_pass
        else "Check the five required report parts for presence and consistency."
    )
    return {
        "task": task,
        "context": {
            "research_analyst_output": dict(research_output),
            "financial_analyst_output": dict(financial_output),
            "investment_advisor_output": dict(advisor_output),
            "deterministic_citation_issues": list(citation_issues),
            "final_pass": final_pass,
        },
        "expected_output": _expected_manager_output(),
    }


def _corrections_for_role(
    failures: Sequence[Mapping[str, Any]], role: str
) -> list[dict[str, Any]]:
    return [dict(item) for item in failures if item.get("responsible_role") == role]


def _append_deterministic_failures(
    failures: list[dict[str, Any]], citation_issues: Sequence[str]
) -> None:
    if not citation_issues:
        return
    failures.append(
        {
            "part": "Overview",
            "responsible_role": ROLE_RESEARCH,
            "problem": "; ".join(citation_issues),
            "required_correction": (
                "Replace every invalid citation with an exact quote from the "
                "cited full-document line range and the correct accession number."
            ),
        }
    )


def compile_report_markdown(
    manager_output: Mapping[str, Any],
    filings: Mapping[str, str],
    run_started: datetime,
) -> str:
    """Put the filing list and run time on the required first two lines."""
    first_line = (
        "Filings read: "
        f"10-K (accession {filings['10-K']}); "
        f"10-Q (accession {filings['10-Q']}); "
        f"8-K Item 2.02 and Exhibit 99.1 (accession {filings['8-K']})"
    )
    second_line = f"Run time: {run_started.isoformat(timespec='seconds')}"
    sections = (
        ("Overview", "overview"),
        (
            "Market Positioning and Growth Outlook",
            "market_positioning_and_growth_outlook",
        ),
        ("Valuation Insights", "valuation_insights"),
        (
            "Future Developments and Strategic Recommendations",
            "future_developments_and_strategic_recommendations",
        ),
        ("Investment Recommendation", "investment_recommendation"),
    )
    lines = [first_line, second_line, "", "# Equity Research Report", ""]
    for title, key in sections:
        value = str(manager_output.get(key, "")).strip()
        if not value:
            raise RoleWorkflowError(f"Strategy Manager omitted report part: {title}.")
        lines.extend((f"## {title}", "", value, ""))
    return "\n".join(lines).rstrip() + "\n"


def run_four_role_workflow(
    *,
    role_client: StructuredRoleClient,
    output_dir: Path,
    run_started: datetime,
    filings: Mapping[str, str],
    ten_k_text: str,
    release_text: str,
    financial_context: Mapping[str, Any],
) -> Path:
    """Run all four roles, permit one correction pass, and save the report."""
    sections = extract_ten_k_sections(ten_k_text)
    research_request = {
        "task": (
            "Analyze the business model, competitive position, catalysts, and "
            "recent developments from the supplied filing sections."
        ),
        "context": {
            "ten_k": {
                "accession_number": filings["10-K"],
                "business_section": sections["business"],
                "md_and_a_section": sections["md_and_a"],
            },
            "earnings_release": {
                "accession_number": filings["8-K"],
                "text": number_document_lines(release_text),
            },
        },
        "expected_output": _expected_research_output(),
    }
    financial_request = {
        "task": (
            "Analyze Step 4 facts, Step 5 ratios, the Step 6 quarter, and Step 7 "
            "peers with complete numeric provenance and calculator arithmetic."
        ),
        "context": dict(financial_context),
        "expected_output": _expected_financial_output(),
    }

    research_output = role_client.call(
        role=ROLE_RESEARCH,
        instructions=RESEARCH_INSTRUCTIONS,
        request=research_request,
        schema_name="research_analyst_output",
        output_schema=RESEARCH_OUTPUT_SCHEMA,
    )
    financial_output = _run_financial_role(role_client, financial_request)

    advisor_request = {
        "task": (
            "Create one thesis and a Buy, Hold, or Sell recommendation from the "
            "two analyst outputs and nothing else. Use exactly one deciding number."
        ),
        "context": {
            "research_analyst_output": research_output,
            "financial_analyst_output": financial_output,
        },
        "expected_output": _expected_advisor_output(),
    }
    advisor_output = role_client.call(
        role=ROLE_ADVISOR,
        instructions=ADVISOR_INSTRUCTIONS,
        request=advisor_request,
        schema_name="investment_advisor_output",
        output_schema=ADVISOR_OUTPUT_SCHEMA,
    )

    citation_issues = validate_research_citations(
        research_output,
        ten_k_text=ten_k_text,
        release_text=release_text,
        ten_k_accession=filings["10-K"],
        release_accession=filings["8-K"],
    )
    manager_output = role_client.call(
        role=ROLE_MANAGER,
        instructions=MANAGER_INSTRUCTIONS,
        request=_manager_review_request(
            research_output,
            financial_output,
            advisor_output,
            citation_issues,
            final_pass=False,
        ),
        schema_name="strategy_manager_review",
        output_schema=MANAGER_OUTPUT_SCHEMA,
    )
    raw_failures = manager_output.get("failures", [])
    failures = [dict(item) for item in raw_failures if isinstance(item, Mapping)]
    _append_deterministic_failures(failures, citation_issues)

    if failures:
        research_corrections = _corrections_for_role(failures, ROLE_RESEARCH)
        financial_corrections = _corrections_for_role(failures, ROLE_FINANCIAL)
        advisor_corrections = _corrections_for_role(failures, ROLE_ADVISOR)

        if research_corrections:
            research_output = role_client.call(
                role=ROLE_RESEARCH,
                instructions=RESEARCH_INSTRUCTIONS,
                request={
                    "task": "Correct the returned failing report parts once.",
                    "context": {
                        "original_manager_assignment": research_request,
                        "previous_output": research_output,
                        "manager_feedback": research_corrections,
                    },
                    "expected_output": _expected_research_output(),
                },
                schema_name="research_analyst_revision",
                output_schema=RESEARCH_OUTPUT_SCHEMA,
            )

        if financial_corrections:
            financial_output = _run_financial_role(
                role_client,
                {
                    "task": "Correct the returned failing report parts once.",
                    "context": {
                        "original_manager_assignment": financial_request,
                        "previous_output": financial_output,
                        "manager_feedback": financial_corrections,
                    },
                    "expected_output": _expected_financial_output(),
                },
            )

        if research_corrections or financial_corrections or advisor_corrections:
            advisor_output = role_client.call(
                role=ROLE_ADVISOR,
                instructions=ADVISOR_INSTRUCTIONS,
                request={
                    "task": (
                        "Reissue the thesis and recommendation once from the two "
                        "current analyst outputs. Use exactly one deciding number "
                        "and preserve its analyst-output source."
                    ),
                    "context": {
                        "research_analyst_output": research_output,
                        "financial_analyst_output": financial_output,
                    },
                    "expected_output": _expected_advisor_output(),
                },
                schema_name="investment_advisor_revision",
                output_schema=ADVISOR_OUTPUT_SCHEMA,
            )

        final_citation_issues = validate_research_citations(
            research_output,
            ten_k_text=ten_k_text,
            release_text=release_text,
            ten_k_accession=filings["10-K"],
            release_accession=filings["8-K"],
        )
        manager_output = role_client.call(
            role=ROLE_MANAGER,
            instructions=MANAGER_INSTRUCTIONS,
            request=_manager_review_request(
                research_output,
                financial_output,
                advisor_output,
                final_citation_issues,
                final_pass=True,
            ),
            schema_name="strategy_manager_final_report",
            output_schema=MANAGER_OUTPUT_SCHEMA,
        )

    report = compile_report_markdown(manager_output, filings, run_started)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "equity_research_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Report: {report_path}")
    return report_path
