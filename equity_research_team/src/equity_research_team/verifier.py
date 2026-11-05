"""Deterministic and model-assisted verification of sourced report numbers."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import asdict, dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence


MARK_CORRECT = "correct"
MARK_WRONG = "wrong"
MARK_UNSUPPORTED = "unsupported"

VERIFIER_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "checks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "supported": {"type": "boolean"},
                    "explanation": {"type": "string"},
                    "corrected_value": {"type": "string"},
                    "source": {"type": "string"},
                },
                "required": [
                    "claim_id",
                    "supported",
                    "explanation",
                    "corrected_value",
                    "source",
                ],
                "additionalProperties": False,
            },
        }
    },
    "required": ["checks"],
    "additionalProperties": False,
}

DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
FY_RE = re.compile(r"\bFY\s*(?:19|20)\d{2}\b", re.IGNORECASE)
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
TAG_RE = re.compile(r"`([A-Za-z][A-Za-z0-9]+)`")
VALUE_RE = re.compile(
    r"(?<![A-Za-z0-9])"
    r"(?P<currency>\$)?\s*"
    r"(?P<negative>-)?"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)"
    r"\s*(?P<suffix>%|x|thousand|million|billion)?",
    re.IGNORECASE,
)
LINE_BLOCK_RE = re.compile(
    r"\blines?\s+([\d\s,;\-–—and]+?)(?=;|\]|\||\.|$)",
    re.IGNORECASE,
)
RATIO_RESULT_RE = re.compile(
    r"(?P<left>[\$\d][\$\d,\.\s\(\)+\-*/]+?)\s*=\s*"
    r"(?P<result>\$?\s*-?\d[\d,]*(?:\.\d+)?\s*(?:%|x|thousand|million|billion)?)",
    re.IGNORECASE,
)
AMBIGUOUS_RATIO_NAMES = (
    "debt to equity",
    "return on equity",
    "return on average equity",
    "free cash flow",
)


class SemanticClient(Protocol):
    """The same structured-call boundary used by every role."""

    def call(
        self,
        *,
        role: str,
        instructions: str,
        request: Mapping[str, Any],
        schema_name: str,
        output_schema: Mapping[str, Any],
    ) -> dict[str, Any]: ...


@dataclass
class NumericToken:
    text: str
    value: Decimal
    suffix: str = ""
    decimals: int = 0


@dataclass
class VerificationClaim:
    claim_id: str
    report_line: int
    statement: str
    reported: str
    source_kind: str
    tags: list[str] = field(default_factory=list)
    periods: list[str] = field(default_factory=list)
    accession_number: str = ""
    line_ranges: list[list[int]] = field(default_factory=list)
    expression: str = ""
    deterministic_mark: str = MARK_UNSUPPORTED
    deterministic_reason: str = ""
    corrected_value: str = ""
    evidence: str = ""
    semantic_supported: bool = False
    semantic_explanation: str = ""
    final_mark: str = MARK_UNSUPPORTED


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def _clean_markdown(text: str) -> str:
    return text.replace("**", "").replace("`", "").replace("−", "-")


def _number_token(raw: str) -> NumericToken | None:
    match = VALUE_RE.search(_clean_markdown(raw).strip())
    if not match:
        return None
    number_text = match.group("number").replace(",", "")
    try:
        value = Decimal(number_text)
    except InvalidOperation:
        return None
    if match.group("negative"):
        value = -value
    suffix = (match.group("suffix") or "").lower()
    if suffix == "%":
        value /= Decimal(100)
    elif suffix == "thousand":
        value *= Decimal(1_000)
    elif suffix == "million":
        value *= Decimal(1_000_000)
    elif suffix == "billion":
        value *= Decimal(1_000_000_000)
    decimals = len(number_text.partition(".")[2])
    return NumericToken(raw.strip(), value, suffix, decimals)


def _numeric_tokens(text: str, *, remove_periods: bool = True) -> list[NumericToken]:
    working = _clean_markdown(text)
    if remove_periods:
        working = ACCESSION_RE.sub(" ", working)
        working = DATE_RE.sub(" ", working)
        working = FY_RE.sub(" ", working)
        working = re.sub(
            r"\b(?:January|February|March|April|May|June|July|August|September|"
            r"October|November|December)\s+\d{1,2},\s+(?:19|20)\d{2}\b",
            " ",
            working,
            flags=re.IGNORECASE,
        )
        working = re.sub(
            r"\b\d+(?:\.\d+)?\s+(?:days?|weeks?|months?|years?)\b",
            " ",
            working,
            flags=re.IGNORECASE,
        )
        working = re.sub(r"^\s*\d+[.)]\s+", "", working)

    tokens: list[NumericToken] = []
    for match in VALUE_RE.finditer(working):
        raw = match.group(0).strip()
        token = _number_token(raw)
        if token is None:
            continue
        plain = match.group("number").replace(",", "")
        if (
            not match.group("currency")
            and not match.group("suffix")
            and "." not in plain
            and len(plain) == 4
            and 1900 <= int(plain) <= 2100
        ):
            continue
        tokens.append(token)
    return tokens


def _periods(text: str) -> list[str]:
    result = DATE_RE.findall(text)
    result.extend(item.upper().replace(" ", "") for item in FY_RE.findall(text))
    return list(dict.fromkeys(result))


def _line_ranges(text: str) -> list[list[int]]:
    ranges: list[list[int]] = []
    for block in LINE_BLOCK_RE.findall(text):
        for start, end in re.findall(r"(\d+)(?:\s*[-–—]\s*(\d+))?", block):
            first = int(start)
            last = int(end) if end else first
            if 0 < first <= last:
                ranges.append([first, last])
    return ranges


def _expression_value(expression: str) -> Decimal:
    normalized = _clean_markdown(expression)
    normalized = re.sub(r"\$|,", "", normalized)
    normalized = re.sub(
        r"(\d+(?:\.\d+)?)\s*%",
        lambda match: f"({match.group(1)}/100)",
        normalized,
    )
    normalized = re.sub(r"\b(?:thousand|million|billion)\b", "", normalized, flags=re.I)
    # The extractor starts at the first numeric token. Restore any opening
    # parenthesis that sits immediately before that token.
    missing_opens = normalized.count(")") - normalized.count("(")
    if missing_opens > 0:
        normalized = ("(" * missing_opens) + normalized
    tree = ast.parse(normalized.strip(), mode="eval")

    def calculate(node: ast.AST) -> Decimal:
        if isinstance(node, ast.Expression):
            return calculate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return Decimal(str(node.value))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = calculate(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left = calculate(node.left)
            right = calculate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ValueError("division by zero")
                return left / right
        raise ValueError("unsupported arithmetic")

    return calculate(tree)


def _rounding_tolerance(token: NumericToken) -> Decimal:
    step = Decimal(10) ** -token.decimals
    if token.suffix == "%":
        step /= Decimal(100)
    elif token.suffix == "thousand":
        step *= Decimal(1_000)
    elif token.suffix == "million":
        step *= Decimal(1_000_000)
    elif token.suffix == "billion":
        step *= Decimal(1_000_000_000)
    return step / Decimal(2) + Decimal("0.0000000001")


def _equivalent(left: Decimal, right: Decimal, tolerance: Decimal) -> bool:
    if abs(left - right) <= tolerance:
        return True
    for factor in (Decimal(100), Decimal(1_000), Decimal(1_000_000), Decimal(1_000_000_000)):
        if abs(left - (right * factor)) <= tolerance:
            return True
        if abs((left * factor) - right) <= tolerance * factor:
            return True
    return False


def _format_corrected(value: Decimal, like: NumericToken) -> str:
    decimals = like.decimals
    if like.suffix == "%":
        return f"{value * Decimal(100):,.{decimals}f}%"
    if like.suffix == "x":
        return f"{value:,.{decimals}f}x"
    scale = Decimal(1)
    suffix = ""
    if like.suffix == "thousand":
        scale, suffix = Decimal(1_000), " thousand"
    elif like.suffix == "million":
        scale, suffix = Decimal(1_000_000), " million"
    elif like.suffix == "billion":
        scale, suffix = Decimal(1_000_000_000), " billion"
    amount = value / scale
    currency = "$" if "$" in like.text else ""
    return f"{currency}{amount:,.{decimals}f}{suffix}"


def _is_ratio_definition_present(statement: str) -> bool:
    lowered = statement.casefold()
    ambiguous = any(name in lowered for name in AMBIGUOUS_RATIO_NAMES)
    if not ambiguous:
        return True
    return any(word in lowered for word in ("definition", "divided by", "less", "plus"))


def _split_report_units(report: str) -> list[tuple[int, str, str]]:
    units: list[tuple[int, str, str]] = []
    skip_thesis = False
    for line_number, raw_line in enumerate(report.splitlines(), start=1):
        line = raw_line.strip()
        if re.match(r"^##+\s+(?:\d+\.\s*)?Investment Recommendation\b", line, re.I):
            skip_thesis = True
            continue
        if skip_thesis and line.startswith("## "):
            skip_thesis = False
        if skip_thesis and not line.startswith("Insight:"):
            continue
        if not line or line.startswith("#"):
            continue
        if re.fullmatch(r"\|?[\s:|\-]+\|?", line):
            continue
        if line_number <= 2 or line.casefold().startswith("run time:"):
            continue

        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) < 2 or all(set(cell) <= {"-", ":", " "} for cell in cells):
                continue
            source_index = next(
                (
                    index
                    for index, cell in enumerate(cells)
                    if re.search(r"\b(?:10-K|10-Q|8-K|Earnings release|tag|line)\b", cell, re.I)
                ),
                len(cells) - 1,
            )
            claim_text = " | ".join(cells[:source_index])
            units.append((line_number, claim_text, line))
            continue

        claim_text = line.split("[", 1)[0].strip()
        if re.search(r"\b(?:numeric claims above|core claims)\b", claim_text, re.I):
            continue
        units.append((line_number, claim_text, line))
    return units


def extract_numeric_claims(report: str) -> list[VerificationClaim]:
    """Extract report numbers while excluding dates, accessions, and the thesis."""

    claims: list[VerificationClaim] = []
    for report_line, claim_text, source_text in _split_report_units(report):
        cleaned_claim = _clean_markdown(claim_text)
        ratio_matches = list(RATIO_RESULT_RE.finditer(cleaned_claim))

        # Markdown ratio tables usually put the expression and result in adjacent cells.
        if not ratio_matches and "|" in cleaned_claim:
            cells = [cell.strip() for cell in cleaned_claim.split("|")]
            for index, cell in enumerate(cells[:-1]):
                if re.search(r"[+\-*/]", cell) and _numeric_tokens(cells[index + 1]):
                    synthetic = f"{cell} = {cells[index + 1]}"
                    ratio_matches.extend(RATIO_RESULT_RE.finditer(synthetic))

        tags = list(dict.fromkeys(TAG_RE.findall(source_text)))
        periods = _periods(source_text)
        accessions = ACCESSION_RE.findall(source_text)
        ranges = _line_ranges(source_text)

        if ratio_matches:
            for match in ratio_matches:
                result_text = match.group("result").strip()
                claims.append(
                    VerificationClaim(
                        claim_id=f"N{len(claims) + 1:03d}",
                        report_line=report_line,
                        statement=claim_text,
                        reported=result_text,
                        source_kind="ratio",
                        tags=tags,
                        periods=periods,
                        accession_number=accessions[0] if accessions else "",
                        line_ranges=ranges,
                        expression=match.group("left").strip(),
                    )
                )
            continue

        for token in _numeric_tokens(claim_text):
            source_kind = "xbrl" if tags else "line" if ranges else "unsourced"
            claims.append(
                VerificationClaim(
                    claim_id=f"N{len(claims) + 1:03d}",
                    report_line=report_line,
                    statement=claim_text,
                    reported=token.text,
                    source_kind=source_kind,
                    tags=tags,
                    periods=periods,
                    accession_number=accessions[0] if accessions else "",
                    line_ranges=ranges,
                )
            )
    return claims


def _load_run_materials(run_dir: Path) -> tuple[dict[str, str], dict[str, Any]]:
    filing_texts = {
        path.name: path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(run_dir.glob("*.txt"))
    }
    facts: dict[str, Any] = {}
    for path in sorted(run_dir.glob("facts*.json")):
        try:
            facts[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            facts[path.name] = {"error": "invalid JSON"}
    return filing_texts, facts


def _fact_records(facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for source_file, payload in facts.items():
        if not isinstance(payload, Mapping):
            continue
        company = payload.get("company", {})
        fact_map = payload.get("facts", {})
        if not isinstance(fact_map, Mapping):
            continue
        for metric_key, fact in fact_map.items():
            if not isinstance(fact, Mapping):
                continue
            for period_name in ("current", "prior"):
                value = fact.get(period_name)
                if not isinstance(value, Mapping) or "val" not in value:
                    continue
                try:
                    numeric_value = Decimal(str(value["val"]))
                except InvalidOperation:
                    continue
                records.append(
                    {
                        "source_file": source_file,
                        "ticker": company.get("ticker", "") if isinstance(company, Mapping) else "",
                        "metric": metric_key,
                        "label": fact.get("label", ""),
                        "tag": fact.get("tag", ""),
                        "unit": fact.get("unit", ""),
                        "period_name": period_name,
                        "value": numeric_value,
                        "start": value.get("start", ""),
                        "end": value.get("end", ""),
                        "fy": value.get("fy", ""),
                        "accession_number": value.get("accn", ""),
                    }
                )
    return records


def _period_matches(record: Mapping[str, Any], periods: Sequence[str]) -> bool:
    if not periods:
        return False
    record_values = {
        str(record.get("start", "")),
        str(record.get("end", "")),
        f"FY{record.get('fy', '')}",
    }
    return any(period.upper().replace(" ", "") in record_values for period in periods)


def _filing_candidates(
    filing_texts: Mapping[str, str], accession_number: str, source_text: str
) -> list[tuple[str, str]]:
    compact = accession_number.replace("-", "")
    candidates = [
        (name, text)
        for name, text in filing_texts.items()
        if compact and compact in name
    ]
    if candidates:
        return candidates
    lowered = source_text.casefold()
    prefixes = []
    if "earnings release" in lowered or "exhibit 99.1" in lowered:
        prefixes = ["8-K_EX-99.1"]
    elif "10-k" in lowered:
        prefixes = ["10-K_"]
    elif "10-q" in lowered:
        prefixes = ["10-Q_"]
    elif "8-k" in lowered:
        prefixes = ["8-K_"]
    return [
        (name, text)
        for name, text in filing_texts.items()
        if any(name.startswith(prefix) for prefix in prefixes)
    ]


def _line_evidence(
    claim: VerificationClaim, filing_texts: Mapping[str, str]
) -> tuple[str, list[NumericToken]]:
    excerpts: list[str] = []
    for name, text in _filing_candidates(
        filing_texts, claim.accession_number, claim.statement
    ):
        lines = text.splitlines()
        for start, end in claim.line_ranges:
            if start < 1 or end > len(lines):
                continue
            excerpt = " ".join(line.strip() for line in lines[start - 1 : end] if line.strip())
            if excerpt:
                excerpts.append(f"{name}, lines {start}-{end}: {excerpt}")
    combined = "\n".join(excerpts)
    return combined, _numeric_tokens(combined)


def _closest_token(target: NumericToken, choices: Sequence[NumericToken]) -> NumericToken | None:
    if not choices:
        return None
    return min(choices, key=lambda item: abs(item.value - target.value))


def _verify_ratio(claim: VerificationClaim) -> None:
    result = _number_token(claim.reported)
    if result is None:
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The reported ratio result is not parseable."
        return
    if not _is_ratio_definition_present(claim.statement):
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = (
            "The ratio has more than one plausible definition, but the report gives no definition."
        )
        return
    try:
        calculated = _expression_value(claim.expression)
    except (SyntaxError, ValueError, InvalidOperation):
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The quoted ratio inputs do not form supported arithmetic."
        return
    normalized_calculated = calculated
    if result.suffix == "thousand":
        normalized_calculated *= Decimal(1_000)
    elif result.suffix == "million":
        normalized_calculated *= Decimal(1_000_000)
    elif result.suffix == "billion":
        normalized_calculated *= Decimal(1_000_000_000)
    claim.evidence = f"Recomputed in code: {claim.expression} = {calculated}"
    if _equivalent(
        result.value,
        normalized_calculated,
        _rounding_tolerance(result),
    ):
        claim.deterministic_mark = MARK_CORRECT
        claim.deterministic_reason = "The code recomputation agrees within displayed rounding."
    else:
        claim.deterministic_mark = MARK_WRONG
        claim.deterministic_reason = "The code recomputation does not equal the reported result."
        claim.corrected_value = _format_corrected(normalized_calculated, result)


def _verify_xbrl(claim: VerificationClaim, records: Sequence[Mapping[str, Any]]) -> None:
    reported = _number_token(claim.reported)
    if reported is None:
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The reported value is not parseable."
        return
    matching_tags = [record for record in records if record.get("tag") in claim.tags]
    if claim.accession_number:
        matching_tags = [
            record
            for record in matching_tags
            if record.get("accession_number") == claim.accession_number
        ]
    if not matching_tags:
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The cited XBRL tag and accession are not in a saved facts file."
        return
    period_records = [record for record in matching_tags if _period_matches(record, claim.periods)]
    if not period_records:
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The cited period does not match the saved fact period exactly."
        claim.evidence = "; ".join(
            f"{item['tag']} {item.get('start', '')} to {item.get('end', '')}"
            for item in matching_tags[:4]
        )
        return
    tolerance = _rounding_tolerance(reported)
    exact = next(
        (
            record
            for record in period_records
            if _equivalent(reported.value, Decimal(str(record["value"])), tolerance)
        ),
        None,
    )
    selected = exact or min(
        period_records,
        key=lambda record: abs(Decimal(str(record["value"])) - reported.value),
    )
    claim.evidence = (
        f"{selected['source_file']}: tag {selected['tag']}; value {selected['value']} "
        f"{selected.get('unit', '')}; period {selected.get('start', '')} to "
        f"{selected.get('end', '')}; accession {selected.get('accession_number', '')}"
    )
    if exact is not None:
        claim.deterministic_mark = MARK_CORRECT
        claim.deterministic_reason = "The value, tag, accession, and period match the saved fact."
    else:
        claim.deterministic_mark = MARK_WRONG
        claim.deterministic_reason = "The cited tag and period contain a different value."
        claim.corrected_value = _format_corrected(Decimal(str(selected["value"])), reported)


def _verify_line(claim: VerificationClaim, filing_texts: Mapping[str, str]) -> None:
    reported = _number_token(claim.reported)
    if reported is None:
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The reported value is not parseable."
        return
    evidence, evidence_tokens = _line_evidence(claim, filing_texts)
    claim.evidence = evidence
    if not evidence:
        claim.deterministic_mark = MARK_UNSUPPORTED
        claim.deterministic_reason = "The cited filing line is absent from the saved filing text."
        return
    tolerance = _rounding_tolerance(reported)
    exact = next(
        (
            token
            for token in evidence_tokens
            if _equivalent(reported.value, token.value, tolerance)
        ),
        None,
    )
    if exact is not None:
        claim.deterministic_mark = MARK_CORRECT
        claim.deterministic_reason = (
            "The number appears on the cited saved line after spacing and formatting normalization."
        )
        return
    claim.deterministic_mark = MARK_WRONG
    claim.deterministic_reason = "The cited saved line contains a different number."
    closest = _closest_token(reported, evidence_tokens)
    if closest is not None:
        claim.corrected_value = _format_corrected(closest.value, reported)


def _find_unsupported_correction(
    claim: VerificationClaim,
    records: Sequence[Mapping[str, Any]],
    filing_texts: Mapping[str, str],
) -> None:
    reported = _number_token(claim.reported)
    if reported is None:
        return
    tolerance = _rounding_tolerance(reported)
    for record in records:
        value = Decimal(str(record["value"]))
        if _equivalent(reported.value, value, tolerance):
            claim.evidence = (
                f"Possible filing support: {record['source_file']}; tag {record['tag']}; "
                f"value {record['value']} {record.get('unit', '')}; period "
                f"{record.get('start', '')} to {record.get('end', '')}."
            )
            claim.corrected_value = claim.reported
            return
    claim.corrected_value = "Remove this number until a filing source is supplied."
    claim.evidence = "No matching saved filing fact or cited filing line was found."


def run_deterministic_checks(
    claims: Sequence[VerificationClaim],
    filing_texts: Mapping[str, str],
    facts: Mapping[str, Any],
) -> None:
    records = _fact_records(facts)
    for claim in claims:
        if claim.source_kind == "ratio":
            _verify_ratio(claim)
        elif claim.source_kind == "xbrl":
            _verify_xbrl(claim, records)
        elif claim.source_kind == "line":
            _verify_line(claim, filing_texts)
        else:
            claim.deterministic_mark = MARK_UNSUPPORTED
            claim.deterministic_reason = "The report supplies no filing line or XBRL tag for this number."
        if claim.deterministic_mark == MARK_UNSUPPORTED and not claim.corrected_value:
            _find_unsupported_correction(claim, records, filing_texts)


def _semantic_request(
    report: str,
    claims: Sequence[VerificationClaim],
    facts: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "task": (
            "Check whether each cited line or fact states the reported number for the "
            "reported period and definition. Skip the Investment Advisor thesis."
        ),
        "context": {
            "compiled_report": report,
            "saved_filing_texts": {
                claim.claim_id: claim.evidence for claim in claims if claim.evidence
            },
            "saved_facts": facts,
            "deterministic_checks": [
                {
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "reported": claim.reported,
                    "source_kind": claim.source_kind,
                    "deterministic_mark": claim.deterministic_mark,
                    "deterministic_reason": claim.deterministic_reason,
                    "evidence": claim.evidence,
                }
                for claim in claims
            ],
        },
        "expected_output": {
            "checks": (
                "One object per claim_id with supported, explanation, corrected_value, "
                "and the real line or tag source."
            )
        },
    }


def _apply_semantic_checks(
    claims: Sequence[VerificationClaim], semantic_output: Mapping[str, Any]
) -> None:
    raw_checks = semantic_output.get("checks", [])
    checks = {
        str(item.get("claim_id")): item
        for item in raw_checks
        if isinstance(item, Mapping) and item.get("claim_id")
    }
    for claim in claims:
        check = checks.get(claim.claim_id)
        if check is None:
            claim.semantic_supported = False
            claim.semantic_explanation = "The model did not return a semantic check for this claim."
        else:
            claim.semantic_supported = bool(check.get("supported"))
            claim.semantic_explanation = str(check.get("explanation", "")).strip()
            if not claim.corrected_value and check.get("corrected_value"):
                claim.corrected_value = str(check["corrected_value"]).strip()
            if check.get("source") and str(check["source"]).strip() not in claim.evidence:
                source = str(check["source"]).strip()
                claim.evidence = f"{claim.evidence}\nModel source: {source}".strip()

        if claim.deterministic_mark == MARK_WRONG:
            claim.final_mark = MARK_WRONG
        elif claim.deterministic_mark == MARK_UNSUPPORTED:
            claim.final_mark = MARK_UNSUPPORTED
        elif claim.semantic_supported:
            claim.final_mark = MARK_CORRECT
        else:
            claim.final_mark = MARK_UNSUPPORTED
            if not claim.corrected_value:
                claim.corrected_value = "Remove or replace this number with filing-supported text."


def _table_text(value: str, limit: int = 300) -> str:
    collapsed = " ".join(value.split())
    if len(collapsed) > limit:
        collapsed = collapsed[: limit - 1] + "…"
    return collapsed.replace("|", "\\|")


def render_verified_report(report: str, claims: Sequence[VerificationClaim]) -> str:
    lines = report.splitlines()
    first_line = lines[0] if lines else "Filings read: unavailable"
    remainder = "\n".join(lines[1:]).lstrip("\n")
    table = [
        "## Verification marks",
        "",
        "The Verifier skipped the Investment Advisor thesis but checked its Insight line. "
        "The mark combines the code check and the model check.",
        "",
        "| ID | Reported claim | Code check | Model check | Mark | Correction and real source |",
        "|---|---|---|---|---|---|",
    ]
    for claim in claims:
        correction = claim.corrected_value or "No correction required."
        source = claim.evidence or "No filing source found."
        table.append(
            "| "
            + " | ".join(
                (
                    claim.claim_id,
                    _table_text(f"{claim.statement} [reported: {claim.reported}]"),
                    _table_text(claim.deterministic_reason),
                    _table_text(claim.semantic_explanation),
                    claim.final_mark,
                    _table_text(f"{correction} — {source}", limit=500),
                )
            )
            + " |"
        )
    table.extend(("", "---", ""))
    return first_line + "\n\n" + "\n".join(table) + remainder.rstrip() + "\n"


def verify_run(
    *,
    run_dir: Path,
    report_path: Path,
    output_dir: Path,
    semantic_client: SemanticClient,
    verifier_instructions: str,
) -> Path:
    """Run the mandatory verifier and save its exact input, output, and report."""

    run_dir = run_dir.resolve()
    report_path = report_path.resolve()
    output_dir = output_dir.resolve()
    if not report_path.is_file():
        raise FileNotFoundError(f"Compiled report not found: {report_path}")
    filing_texts, facts = _load_run_materials(run_dir)
    if not filing_texts:
        raise ValueError(f"No saved filing texts were found in {run_dir}.")
    if not facts:
        raise ValueError(f"No saved facts files were found in {run_dir}.")

    report = report_path.read_text(encoding="utf-8")
    claims = extract_numeric_claims(report)
    run_deterministic_checks(claims, filing_texts, facts)
    request = _semantic_request(report, claims, facts)

    nodes_dir = output_dir / "nodes"
    _write_json(
        nodes_dir / "06_verifier_input.json",
        {
            "compiled_report": report,
            "saved_filing_texts": filing_texts,
            "saved_facts": facts,
            "model_request": request,
        },
    )
    semantic_output = semantic_client.call(
        role="Verifier",
        instructions=verifier_instructions,
        request=request,
        schema_name="verifier_output",
        output_schema=VERIFIER_OUTPUT_SCHEMA,
    )
    _apply_semantic_checks(claims, semantic_output)
    output_payload = {
        "claims": [asdict(claim) for claim in claims],
        "counts": {
            mark: sum(claim.final_mark == mark for claim in claims)
            for mark in (MARK_CORRECT, MARK_WRONG, MARK_UNSUPPORTED)
        },
        "semantic_output": semantic_output,
    }
    _write_json(nodes_dir / "06_verifier_output.json", output_payload)

    output_dir.mkdir(parents=True, exist_ok=True)
    verified_path = output_dir / "verified_report.md"
    verified_path.write_text(render_verified_report(report, claims), encoding="utf-8")
    return verified_path
