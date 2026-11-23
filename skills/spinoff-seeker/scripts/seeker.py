#!/usr/bin/env python3
"""Deterministic SEC spinoff seeker for FIN 67110 Lab 06."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urljoin
from zoneinfo import ZoneInfo


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
WORKSPACE_DIR = SKILL_DIR.parents[1]
PROJECT_DIR = WORKSPACE_DIR / "equity_research_team"
FINAL_FACTORS_PATH = SKILL_DIR / "references" / "factors.json"
ZERO_FACTORS_PATH = SKILL_DIR / "references" / "factors_weight_zero.json"
TEAM_INPUTS_PATH = SKILL_DIR / "references" / "team_inputs.json"
DEFAULT_OUTPUT_ROOT = WORKSPACE_DIR / "lab06_runs"
EASTERN = ZoneInfo("America/New_York")

if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from equity_research_data import (  # noqa: E402
    Company,
    DownloadedResource,
    Filing,
    SecClient,
    decode_resource,
    fetch_submission_filings,
    read_sec_user_agent,
    resource_to_plain_text,
)

from closes_reader import (  # noqa: E402
    ClosesReader,
    DailyClose,
    FinancialDatasetsClosesReader,
    build_closes_reader,
    first_close_after,
    trading_day_close,
)


FORM_INDEX_URL = "https://www.sec.gov/Archives/edgar/full-index/{year}/QTR{quarter}/form.idx"
SEC_ARCHIVES = "https://www.sec.gov/Archives/"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
SEC_COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
FORM10_FORMS = {"10-12B", "10-12B/A", "10-12G", "10-12G/A"}
TRADING_PROOF_FORMS = {"10-Q", "10-K", "4"}
FORM_INDEX_RE = re.compile(
    r"^(?P<form>10-12[BG](?:/A)?|CERT)\s{2,}"
    r"(?P<company>.+?)\s{2,}(?P<cik>\d+)\s{2,}"
    r"(?P<filed>\d{4}-\d{2}-\d{2})\s{2,}(?P<filename>\S+)\s*$"
)
MONTH_DATE = (
    r"(?:January|February|March|April|May|June|July|August|September|October|"
    r"November|December)\s+\d{1,2},\s+20\d{2}"
)
ISO_DATE = r"20\d{2}-\d{2}-\d{2}"
DATE_TOKEN_RE = re.compile(rf"\b(?:{MONTH_DATE}|{ISO_DATE})\b", re.IGNORECASE)


class SeekerError(RuntimeError):
    """A seeker invariant or required source failed."""


@dataclass(frozen=True)
class IndexRow:
    form: str
    company: str
    cik: int
    filed_date: date
    filename: str

    @property
    def url(self) -> str:
        return urljoin(SEC_ARCHIVES, self.filename)

    @property
    def accession(self) -> str:
        return Path(self.filename).stem

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["filed_date"] = self.filed_date.isoformat()
        payload["url"] = self.url
        payload["accession"] = self.accession
        return payload


@dataclass(frozen=True)
class SubmissionDocument:
    form_type: str
    sequence: str
    filename: str
    description: str
    text: str


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SeekerError(f"Could not read JSON: {path}") from exc


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _payload_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        return None
    return result if result.is_finite() else None


def _format_decimal(value: object, places: int = 2) -> str:
    number = _decimal(value)
    if number is None:
        return "not available"
    quantum = Decimal(1).scaleb(-places)
    return f"{number.quantize(quantum, rounding=ROUND_HALF_UP):,.{places}f}"


def _parse_date(value: str) -> date | None:
    cleaned = re.sub(r"\s+", " ", value.strip().replace("\u00a0", " "))
    for format_string in ("%Y-%m-%d", "%B %d, %Y"):
        try:
            return datetime.strptime(cleaned, format_string).date()
        except ValueError:
            continue
    return None


def load_factors(path: Path, *, allow_proof: bool = False) -> dict[str, Any]:
    payload = _read_json(path)
    if not isinstance(payload, dict) or not isinstance(payload.get("factors"), list):
        raise SeekerError("The factor file must contain a factors list.")
    if payload.get("window_days_after_distribution") != 90:
        raise SeekerError("The confirmed Lab 06 window must be 90 calendar days.")
    expected_ids = [
        "relative_company_size",
        "post_distribution_price_weakness",
        "insider_open_market_buying",
    ]
    factor_ids = [item.get("id") for item in payload["factors"]]
    if factor_ids != expected_ids:
        raise SeekerError("The confirmed three factors or their order changed.")
    weights = [item.get("weight_percent") for item in payload["factors"]]
    if payload.get("configuration") == "final":
        if weights != [35, 40, 25] or sum(weights) != 100:
            raise SeekerError("The final factor weights must be 35%, 40%, and 25%.")
    elif not allow_proof:
        raise SeekerError("A proof-only factor file cannot replace the final configuration.")
    return payload


def parse_form_index(
    text: str, start_date: date, end_date: date
) -> list[IndexRow]:
    results = []
    for line in text.splitlines():
        match = FORM_INDEX_RE.match(line)
        if not match:
            continue
        filed_date = date.fromisoformat(match.group("filed"))
        if not start_date <= filed_date <= end_date:
            continue
        results.append(
            IndexRow(
                form=match.group("form"),
                company=match.group("company").strip(),
                cik=int(match.group("cik")),
                filed_date=filed_date,
                filename=match.group("filename"),
            )
        )
    return results


def quarters_between(start_date: date, end_date: date) -> list[tuple[int, int]]:
    if end_date < start_date:
        raise SeekerError("The end date is before the start date.")
    year, quarter = start_date.year, (start_date.month - 1) // 3 + 1
    end_value = (end_date.year, (end_date.month - 1) // 3 + 1)
    values = []
    while (year, quarter) <= end_value:
        values.append((year, quarter))
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1
    return values


def parse_submission_documents(raw_text: str, source_url: str) -> list[SubmissionDocument]:
    results = []
    blocks = re.findall(r"<DOCUMENT>(.*?)</DOCUMENT>", raw_text, re.I | re.S)
    for block in blocks:
        def field(name: str) -> str:
            match = re.search(rf"<{name}>\s*([^\r\n<]+)", block, re.I)
            return match.group(1).strip() if match else ""

        text_match = re.search(r"<TEXT>(.*)", block, re.I | re.S)
        body = text_match.group(1) if text_match else block
        resource = DownloadedResource(
            url=source_url,
            content=body.encode("utf-8", errors="replace"),
            content_type="text/html" if re.search(r"<html|<body|<table", body, re.I) else "text/plain",
            encoding="utf-8",
        )
        plain = resource_to_plain_text(resource)
        results.append(
            SubmissionDocument(
                form_type=field("TYPE"),
                sequence=field("SEQUENCE"),
                filename=field("FILENAME"),
                description=field("DESCRIPTION"),
                text=plain,
            )
        )
    if results:
        return results
    resource = DownloadedResource(
        url=source_url,
        content=raw_text.encode("utf-8", errors="replace"),
        content_type="text/plain",
        encoding="utf-8",
    )
    return [SubmissionDocument("", "", "submission.txt", "", resource_to_plain_text(resource))]


def select_information_document(
    documents: Sequence[SubmissionDocument],
) -> SubmissionDocument | None:
    scored: list[tuple[int, int, SubmissionDocument]] = []
    for document in documents:
        description = document.description.lower()
        text = document.text.lower()
        score = 0
        if "information statement" in description:
            score += 20
        if "information statement" in text[:80_000]:
            score += 8
        if document.form_type.upper().startswith("EX-99"):
            score += 4
        if document.form_type.upper() in FORM10_FORMS:
            score += 2
        if score:
            scored.append((score, len(document.text), document))
    return max(scored, default=(0, 0, None), key=lambda item: (item[0], item[1]))[2]


def has_parent_distribution(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text).lower()
    patterns = (
        r"distribution by .{1,180}? to (?:the )?holders? of",
        r"will distribute (?:all|approximately \d+(?:\.\d+)?%) .{1,180}?shares",
        r"distribution of (?:all|\d+(?:\.\d+)?%) of the (?:issued and )?outstanding shares",
        r"spin[- ]off .{1,180}? through the distribution",
    )
    return any(re.search(pattern, normalized) for pattern in patterns)


def classify_registration_history(
    filings: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Classify in filing order; a later distribution proof overrides an exclusion."""
    ordered = sorted(filings, key=lambda item: str(item.get("filed_date", "")))
    latest_reason = "Form 10 could not be classified."
    latest_filing: Mapping[str, Any] = ordered[-1] if ordered else {}
    accepted = None
    for filing in ordered:
        text = str(filing.get("text", ""))
        lowered = text.lower()
        has_info = "information statement" in lowered
        distribution = has_parent_distribution(text)
        if has_info and distribution:
            accepted = filing
            continue
        if not has_info:
            latest_reason = "Form 10 has no information statement."
        elif re.search(
            r"\b(?:investment|credit|income|private equity|hedge|infrastructure)\s+fund\b|"
            r"\bbusiness development company\b|\bregistered investment company\b",
            lowered,
        ):
            latest_reason = "Registrant is a fund, not a spinoff."
        elif re.search(
            r"register(?:s|ing|ed)? .{0,100} shares .{0,100} already (?:issued|outstanding)|"
            r"shares .{0,80} currently outstanding",
            lowered,
        ):
            latest_reason = "Registrant is registering shares it already has; no parent distribution is shown."
        else:
            latest_reason = "Information statement does not show a parent distributing the business."
        latest_filing = filing
    if accepted is not None:
        return {
            "classification": "spinoff",
            "reason": "A Form 10 information statement shows a parent distributing the business.",
            "filing": dict(accepted),
            "later_filing_override": accepted is not ordered[0],
        }
    return {
        "classification": "dropped",
        "reason": latest_reason,
        "filing": dict(latest_filing),
        "later_filing_override": False,
    }


def classify_parent_transaction_updates(
    filings: Sequence[Mapping[str, Any]],
    *,
    accepted_filed_date: str,
) -> dict[str, Any]:
    """Reconcile a Form 10 classification with later parent transaction filings."""

    ordered = sorted(
        (
            filing
            for filing in filings
            if str(filing.get("filed_date", "")) > accepted_filed_date
        ),
        key=lambda item: str(item.get("filed_date", "")),
    )
    withdrawn_record_date: Mapping[str, Any] | None = None
    reinstated_record_date: Mapping[str, Any] | None = None
    merger: Mapping[str, Any] | None = None
    completed_spinoff: Mapping[str, Any] | None = None

    for filing in ordered:
        text = re.sub(r"\s+", " ", str(filing.get("text", ""))).strip()
        lowered = text.lower()
        if re.search(
            r"withdraw(?:s|n|ing)?\b.{0,180}\brecord date\b|"
            r"\brecord date\b.{0,180}\bwithdraw(?:s|n|ing)?\b",
            lowered,
        ) and re.search(r"spin[- ]?off", lowered):
            withdrawn_record_date = filing
        elif re.search(r"\brecord date\b", lowered) and re.search(
            r"spin[- ]?off", lowered
        ):
            reinstated_record_date = filing

        if re.search(
            r"\bwill merge with and into\b.{0,500}\bmerger\s*sub\b|"
            r"\bmerge with and into\b.{0,500}\bwholly owned subsidiary\b",
            lowered,
        ):
            merger = filing
        if re.search(
            r"\b(?:completed|consummated)\b.{0,180}\b(?:spin[- ]?off|distribution)\b|"
            r"\b(?:spin[- ]?off|distribution)\b.{0,180}\b(?:completed|consummated)\b",
            lowered,
        ):
            completed_spinoff = filing

    record_date_withdrawn = bool(
        withdrawn_record_date
        and (
            reinstated_record_date is None
            or str(reinstated_record_date.get("filed_date", ""))
            <= str(withdrawn_record_date.get("filed_date", ""))
        )
    )
    merger_conflict = bool(
        merger
        and (
            completed_spinoff is None
            or str(completed_spinoff.get("filed_date", ""))
            <= str(merger.get("filed_date", ""))
        )
    )

    def source(filing: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if filing is None:
            return None
        return {
            key: filing.get(key)
            for key in ("form", "accession", "filed_date", "url")
            if filing.get(key)
        }

    if merger_conflict:
        reason = (
            "Later parent filing evidence contradicts the pending spin-off status: "
            "the registrant is subject to a pending merger that would make it a "
            "wholly owned subsidiary of another company."
        )
        if record_date_withdrawn:
            reason = (
                "Later parent filing evidence contradicts the record date and pending "
                "spin-off status: the announced record date was withdrawn, and the "
                "registrant is subject to a pending merger that would make it a wholly "
                "owned subsidiary of another company."
            )
        return {
            "classification": "status_conflict",
            "reason": reason,
            "record_date_withdrawn": record_date_withdrawn,
            "record_date_withdrawal_filing": source(withdrawn_record_date),
            "merger_filing": source(merger),
        }

    return {
        "classification": "spinoff",
        "reason": None,
        "record_date_withdrawn": record_date_withdrawn,
        "record_date_withdrawal_filing": source(withdrawn_record_date),
        "merger_filing": None,
    }


def _line_source(
    text: str,
    character_offset: int,
    *,
    form: str,
    accession: str,
    url: str,
    quote: str | None = None,
) -> dict[str, Any]:
    lines = text.splitlines()
    line_index = text[:character_offset].count("\n")
    line_index = min(line_index, max(0, len(lines) - 1))
    section = "Information statement"
    for prior in reversed(lines[max(0, line_index - 60) : line_index + 1]):
        candidate = re.sub(r"\s+", " ", prior).strip()
        letters = [character for character in candidate if character.isalpha()]
        if 3 <= len(candidate) <= 120 and letters and candidate.upper() == candidate:
            section = candidate
            break
    source_quote = re.sub(r"\s+", " ", quote or (lines[line_index] if lines else "")).strip()
    return {
        "form": form,
        "accession": accession,
        "url": url,
        "section": section,
        "line": line_index + 1,
        "quote": source_quote[:1200],
    }


def _dated_fact(
    text: str,
    patterns: Sequence[str],
    *,
    form: str,
    accession: str,
    url: str,
) -> dict[str, Any] | None:
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if not match:
            continue
        token = match.group("date")
        parsed = _parse_date(token)
        if parsed is None:
            continue
        return {
            "value": parsed.isoformat(),
            "source": _line_source(
                text,
                match.start(),
                form=form,
                accession=accession,
                url=url,
                quote=match.group(0),
            ),
        }
    return None


def extract_distribution_date(
    text: str, *, form: str, accession: str, url: str
) -> dict[str, Any] | None:
    return _dated_fact(
        text,
        (
            rf"distribution (?:will be |is )?(?:effective|completed|occur(?:s|red)?)"
            rf".{{0,120}}?(?:on|as of)\s+(?P<date>{MONTH_DATE}|{ISO_DATE})",
            rf"(?P<date>{MONTH_DATE}|{ISO_DATE})\s*\([^)]{{0,40}}distribution date[^)]*\)",
            rf"distribution date\s*(?:is|will be|:)?\s*(?P<date>{MONTH_DATE}|{ISO_DATE})",
        ),
        form=form,
        accession=accession,
        url=url,
    )


def extract_record_date(
    text: str, *, form: str, accession: str, url: str
) -> dict[str, Any] | None:
    return _dated_fact(
        text,
        (
            rf"record date.{0,100}?(?:is|will be|of|:)\s*(?P<date>{MONTH_DATE}|{ISO_DATE})",
            rf"(?P<date>{MONTH_DATE}|{ISO_DATE})\s*\([^)]{{0,40}}record date[^)]*\)",
            rf"holders? of record.{0,120}?(?:on|as of)\s+(?P<date>{MONTH_DATE}|{ISO_DATE})",
        ),
        form=form,
        accession=accession,
        url=url,
    )


def extract_distribution_ratio(
    text: str, *, form: str, accession: str, url: str
) -> dict[str, Any] | None:
    patterns = (
        r"(?:receive|distribution of)\s+(?P<quote>(?:one|two|three|\d+(?:\.\d+)?)\s+"
        r"shares?.{0,160}?for every\s+(?:one|two|three|\d+(?:\.\d+)?)\s+shares?)",
        r"(?P<quote>(?:one|two|three|\d+(?:\.\d+)?)\s+shares?.{0,160}?for each\s+"
        r"(?:one|two|three|\d+(?:\.\d+)?)\s+shares?)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I | re.S)
        if match:
            value = re.sub(r"\s+", " ", match.group("quote")).strip()
            return {
                "value": value,
                "source": _line_source(
                    text,
                    match.start(),
                    form=form,
                    accession=accession,
                    url=url,
                    quote=match.group(0),
                ),
            }
    return None


def extract_parent_name(
    text: str, *, form: str, accession: str, url: str
) -> dict[str, Any] | None:
    patterns = (
        r"distribution by\s+(?P<parent>[A-Z][A-Za-z0-9&.,'’\- ]{2,100}?)"
        r"(?:\s*\([^)]*\))?\s+to (?:the )?holders?",
        r"(?:our parent|parent company),\s*(?P<parent>[A-Z][A-Za-z0-9&.,'’\- ]{2,100}?)"
        r"(?:\s*\([^)]*\))?(?:,|\.|\s+will)",
        r"separation (?:of .{0,80}? )?from\s+(?P<parent>[A-Z][A-Za-z0-9&.,'’\- ]{2,100}?)"
        r"(?:\s*\([^)]*\))?(?:,|\.|\s+was)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        value = re.sub(r"\s+", " ", match.group("parent")).strip(" ,.;")
        value = _trim_parent_candidate(value)
        if not _plausible_parent_entity_name(value):
            continue
        return {
            "value": value,
            "source": _line_source(
                text,
                match.start(),
                form=form,
                accession=accession,
                url=url,
                quote=match.group(0),
            ),
        }
    return None


def _trim_parent_candidate(value: str) -> str:
    """Cut a parent-name match at generic prose boundaries to avoid fragments."""
    value = re.sub(r"[’']s\s+(?:other|remaining|non-spin|non-spun)\b.*$", "", value, flags=re.I)
    value = re.split(
        r"\s+(?:and\s+(?:the\s+)?distribution\b|following\b|which\b|who\b|that\b|"
        r"is resident\b|in\s+20\d{2}\b|from\s+20\d{2}\b)",
        value,
        maxsplit=1,
        flags=re.I,
    )[0]
    return value.strip(" ,.;:’'\"()")


def _plausible_parent_entity_name(value: str) -> bool:
    """Accept only short entity-style names; leave unmatched facts unavailable."""
    value = value.strip()
    if not value or len(value) > 100:
        return False
    if re.search(r"\b(?:resident for tax purposes|functional currency|from 20\d{2} until 20\d{2})\b", value, re.I):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z&.'’\-]*", value)
    if not words or len(words) > 7 or not words[0][0].isupper():
        return False
    particles = {"de", "del", "der", "di", "du", "and", "the", "of", "for"}
    return all(word[0].isupper() or word.casefold() in particles for word in words)


def extract_total_assets(
    text: str, *, form: str, accession: str, url: str
) -> dict[str, Any] | None:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        normalized = re.sub(r"\s+", " ", line).strip()
        if not re.search(r"(?:^|\|)\s*Total assets\b", normalized, re.I):
            continue
        numbers = re.findall(r"(?<![A-Za-z])\(?\$?\s*(\d[\d,]*(?:\.\d+)?)\)?", normalized)
        if not numbers:
            continue
        raw = Decimal(numbers[0].replace(",", ""))
        context = "\n".join(lines[max(0, index - 50) : index + 1])
        multiplier = Decimal(1)
        unit = "units"
        if re.search(r"\bin millions\b|\$\s*in\s*millions", context, re.I):
            multiplier, unit = Decimal(1_000_000), "USD millions"
        elif re.search(r"\bin thousands\b|\$\s*in\s*thousands", context, re.I):
            multiplier, unit = Decimal(1_000), "USD thousands"
        dates = [_parse_date(item.group(0)) for item in DATE_TOKEN_RE.finditer(context)]
        dates = [item for item in dates if item is not None]
        source = _line_source(
            text,
            sum(len(item) + 1 for item in lines[:index]),
            form=form,
            accession=accession,
            url=url,
            quote=normalized,
        )
        return {
            "value": str(raw * multiplier),
            "display_value": str(raw),
            "unit": unit,
            "as_of_date": max(dates).isoformat() if dates else None,
            "source": source,
        }
    return None


def extract_registry_facts(
    text: str, *, form: str, accession: str, url: str
) -> dict[str, Any]:
    return {
        "parent": extract_parent_name(text, form=form, accession=accession, url=url),
        "distribution_ratio": extract_distribution_ratio(
            text, form=form, accession=accession, url=url
        ),
        "record_date": extract_record_date(text, form=form, accession=accession, url=url),
        "distribution_date": extract_distribution_date(
            text, form=form, accession=accession, url=url
        ),
        "spinoff_total_assets": extract_total_assets(
            text, form=form, accession=accession, url=url
        ),
    }


def _normalize_company_name(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"\b(the|incorporated|inc|corp|corporation|company|co|plc|llc|ltd|holdings?)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def resolve_company_by_name(
    name: str, companies: Sequence[Mapping[str, Any]]
) -> Mapping[str, Any] | None:
    wanted = _normalize_company_name(name)
    if len(wanted) < 3:
        return None
    scored = []
    for company in companies:
        title = str(company.get("title", ""))
        normalized = _normalize_company_name(title)
        if not normalized:
            continue
        score = SequenceMatcher(None, wanted, normalized).ratio()
        if wanted in normalized or normalized in wanted:
            score = max(score, 0.96)
        scored.append((score, len(normalized), company))
    if not scored:
        return None
    score, _, company = max(scored, key=lambda item: (item[0], item[1]))
    return company if score >= 0.82 else None


def determine_stage(
    *,
    run_date: date,
    distribution_date: date | None,
    has_certificate: bool,
    trading_proof: Mapping[str, Any] | None,
    window_days: int,
) -> str:
    if trading_proof and distribution_date:
        window_end = distribution_date + timedelta(days=window_days)
        return "in_window" if run_date <= window_end else "past_window"
    if trading_proof:
        return "trading"
    if has_certificate:
        return "listing_approved"
    return "registered"


def score_relative_size(ratio: Decimal) -> int:
    if ratio <= Decimal("0.10"):
        return 2
    if ratio <= Decimal("0.20"):
        return 1
    return 0


def score_price_weakness(decline_percent: Decimal) -> int:
    if decline_percent >= Decimal("15"):
        return 2
    if decline_percent >= Decimal("5"):
        return 1
    return 0


def score_insider_buying(distinct_insiders: int) -> int:
    if distinct_insiders >= 2:
        return 2
    if distinct_insiders == 1:
        return 1
    return 0


def score_record(record: Mapping[str, Any], factors: Mapping[str, Any]) -> dict[str, Any]:
    inputs = record.get("factor_inputs") or {}
    raw_points: dict[str, int | None] = {}
    ratio = _decimal(inputs.get("relative_company_size_ratio"))
    raw_points["relative_company_size"] = score_relative_size(ratio) if ratio is not None else None
    decline = _decimal(inputs.get("price_decline_percent"))
    raw_points["post_distribution_price_weakness"] = (
        score_price_weakness(decline) if decline is not None else None
    )
    insiders = inputs.get("distinct_qualifying_insiders")
    raw_points["insider_open_market_buying"] = (
        score_insider_buying(int(insiders)) if insiders is not None else None
    )

    factor_results = []
    missing = []
    total = Decimal(0)
    for factor in factors["factors"]:
        factor_id = factor["id"]
        weight = int(factor["weight_percent"])
        points = raw_points[factor_id]
        if weight == 0:
            factor_results.append(
                {
                    "id": factor_id,
                    "name": factor["name"],
                    "weight_percent": 0,
                    "points": None,
                    "raw_points_before_weight_rule": points,
                    "weighted_score": "0",
                    "status": "disabled",
                }
            )
            continue
        if points is None:
            missing.append(factor["name"])
            contribution = None
        else:
            contribution = (Decimal(points) / Decimal(2)) * Decimal(weight)
            total += contribution
        factor_results.append(
            {
                "id": factor_id,
                "name": factor["name"],
                "weight_percent": weight,
                "points": points,
                "raw_points_before_weight_rule": points,
                "weighted_score": str(contribution) if contribution is not None else None,
                "status": "missing" if points is None else "active",
            }
        )
    rankable = record.get("stage") == "in_window" and not missing
    return {
        "cik": record.get("cik"),
        "company": record.get("company"),
        "ticker": record.get("ticker"),
        "stage": record.get("stage"),
        "rankable": rankable,
        "unranked_reasons": [f"Missing required input for {name}." for name in missing],
        "total_score": str(total) if not missing else None,
        "factors": factor_results,
    }


def evaluate_snapshot(snapshot: Mapping[str, Any], factors: Mapping[str, Any]) -> dict[str, Any]:
    records = []
    source_by_cik = {}
    for record in snapshot.get("records", []):
        if record.get("classification") != "spinoff":
            continue
        result = score_record(record, factors)
        records.append(result)
        source_by_cik[str(record.get("cik"))] = record
    ranked = sorted(
        (item for item in records if item["rankable"]),
        key=lambda item: (-Decimal(str(item["total_score"])), str(item["company"])),
    )
    for rank, item in enumerate(ranked, 1):
        item["rank"] = rank
    return {
        "factor_configuration": factors["configuration"],
        "factors_sha256": _payload_sha256(factors),
        "records": records,
        "ranked_ciks": [item["cik"] for item in ranked],
        "ranked": ranked,
        "source_by_cik": source_by_cik,
    }


def _records(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        values = payload.values()
    elif isinstance(payload, list):
        values = payload
    else:
        return []
    return [dict(item) for item in values if isinstance(item, Mapping)]


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _save_sec_resource(client: SecClient, url: str, path: Path) -> DownloadedResource:
    if path.is_file():
        suffix = path.suffix.lower()
        content_type = {
            ".json": "application/json",
            ".html": "text/html",
            ".xml": "application/xml",
        }.get(suffix, "text/plain")
        resource = DownloadedResource(
            url=url,
            content=path.read_bytes(),
            content_type=content_type,
            encoding="utf-8",
        )
        client._resource_cache[url] = resource
        return resource
    resource = client.fetch(url)
    _write_bytes(path, resource.content)
    return resource


def _filing_dict(filing: Filing, cik: int) -> dict[str, Any]:
    return {
        "form": filing.form,
        "accession": filing.accession_number,
        "filing_date": filing.filing_date,
        "report_date": filing.report_date,
        "url": filing.primary_document_url(cik) if filing.primary_document else filing.index_url(cik),
    }


def _company_from_record(record: Mapping[str, Any], fallback_name: str) -> Company:
    ticker = str(record.get("ticker") or "").strip().upper()
    return Company(
        ticker=ticker,
        cik=int(record.get("cik_str") or 0),
        name=str(record.get("title") or fallback_name),
    )


def _xbrl_parent_assets(
    payload: Mapping[str, Any], target_date: date
) -> dict[str, Any] | None:
    concepts = payload.get("facts", {}).get("us-gaap", {})
    if not isinstance(concepts, Mapping):
        return None
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for tag in (
        "Assets",
        "AssetsCurrent",
        "AssetsNet",
    ):
        concept = concepts.get(tag)
        if not isinstance(concept, Mapping):
            continue
        units = concept.get("units", {})
        points = units.get("USD", []) if isinstance(units, Mapping) else []
        for point in points if isinstance(points, list) else []:
            if not isinstance(point, Mapping):
                continue
            if str(point.get("form", "")).upper() not in {"10-K", "10-Q"}:
                continue
            point_date = _parse_date(str(point.get("end", "")))
            try:
                value = Decimal(str(point.get("val")))
            except InvalidOperation:
                continue
            if point_date is None or not value.is_finite() or value <= 0:
                continue
            candidates.append(
                (
                    abs((point_date - target_date).days),
                    str(point.get("filed", "")),
                    {
                        "value": str(value),
                        "as_of_date": point_date.isoformat(),
                        "source": {
                            "form": str(point.get("form", "")),
                            "accession": str(point.get("accn", "")),
                            "filed": str(point.get("filed", "")),
                            "tag": tag,
                            "unit": "USD",
                            "section": "XBRL company facts",
                        },
                    },
                )
            )
    if not candidates:
        return None
    return min(candidates, key=lambda item: (item[0], item[1]))[2]


def _xml_text(element: ET.Element, path: str) -> str:
    found = element.find(path)
    return (found.text or "").strip() if found is not None else ""


def _qualifying_form4_purchases(
    raw_xml: str,
    *,
    start_date: date,
    end_date: date,
    filing: Filing,
    source_url: str,
) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return []
    owner = _xml_text(root, ".//{*}reportingOwnerId/{*}rptOwnerName")
    is_director = _xml_text(root, ".//{*}reportingOwnerRelationship/{*}isDirector") == "1"
    is_officer = _xml_text(root, ".//{*}reportingOwnerRelationship/{*}isOfficer") == "1"
    if not (is_director or is_officer):
        return []
    results = []
    for transaction in root.findall(".//{*}nonDerivativeTransaction"):
        code = _xml_text(
            transaction, ".//{*}transactionCoding/{*}transactionCode"
        ).upper()
        transaction_date = _parse_date(
            _xml_text(transaction, ".//{*}transactionDate/{*}value")
        )
        if code != "P" or transaction_date is None:
            continue
        if not start_date <= transaction_date <= end_date:
            continue
        results.append(
            {
                "owner": owner,
                "transaction_date": transaction_date.isoformat(),
                "transaction_code": code,
                "role": "director" if is_director and not is_officer else "officer",
                "source": {
                    "form": filing.form,
                    "accession": filing.accession_number,
                    "filing_date": filing.filing_date,
                    "url": source_url,
                },
            }
        )
    return results


def _format_source(fact: Mapping[str, Any] | None) -> str:
    if not fact:
        return ""
    source = fact.get("source")
    if not isinstance(source, Mapping):
        return ""
    parts = [
        str(source.get("form") or "").strip(),
        str(source.get("accession") or "").strip(),
        str(source.get("section") or "").strip(),
    ]
    return ", ".join(item for item in parts if item)


def _record_for_csv(record: Mapping[str, Any]) -> dict[str, Any]:
    facts = record.get("facts") if isinstance(record.get("facts"), Mapping) else {}
    inputs = record.get("factor_inputs") if isinstance(record.get("factor_inputs"), Mapping) else {}

    def fact_value(name: str) -> str:
        fact = facts.get(name) if isinstance(facts, Mapping) else None
        return str(fact.get("value") or "") if isinstance(fact, Mapping) else ""

    return {
        "cik": record.get("cik", ""),
        "company": record.get("company", ""),
        "ticker": record.get("ticker", ""),
        "classification": record.get("classification", ""),
        "stage": record.get("stage", ""),
        "parent": fact_value("parent"),
        "parent_cik": record.get("parent_cik", ""),
        "distribution_ratio": fact_value("distribution_ratio"),
        "record_date": fact_value("record_date"),
        "distribution_date": fact_value("distribution_date"),
        "first_price": (record.get("first_price") or {}).get("close", ""),
        "first_price_date": (record.get("first_price") or {}).get("trading_date", ""),
        "day20_price": (record.get("day20_price") or {}).get("close", ""),
        "day20_price_date": (record.get("day20_price") or {}).get("trading_date", ""),
        "relative_company_size_ratio": inputs.get("relative_company_size_ratio", ""),
        "price_decline_percent": inputs.get("price_decline_percent", ""),
        "distinct_qualifying_insiders": inputs.get("distinct_qualifying_insiders", ""),
        "unavailable_facts": "; ".join(record.get("unavailable_facts") or []),
    }


def _write_registry(run_dir: Path, records: Sequence[Mapping[str, Any]]) -> tuple[Path, Path]:
    json_path = run_dir / "registry.json"
    csv_path = run_dir / "registry.csv"
    _write_json(json_path, {"records": list(records)})
    rows = [_record_for_csv(record) for record in records]
    fieldnames = list(rows[0]) if rows else list(_record_for_csv({}))
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return json_path, csv_path


def render_report(
    snapshot: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> str:
    source_by_cik = {
        str(item.get("cik")): item
        for item in snapshot.get("records", [])
        if isinstance(item, Mapping)
    }
    price_dates = []
    for record in source_by_cik.values():
        for name in ("first_price", "day20_price"):
            value = record.get(name)
            if isinstance(value, Mapping) and value.get("trading_date"):
                price_dates.append(str(value["trading_date"]))
    price_date = max(price_dates) if price_dates else "not available"
    lines = [
        f"Run date: {snapshot['run_date']} | Price date: {price_date} | Index date: {snapshot['index_date']}",
        "# Lab 06 Spinoff Seeker",
        "",
        "## Ranked in-window names",
    ]
    ranked = evaluation.get("ranked", [])
    if not ranked:
        lines.append("No in-window name had every required active-factor input.")
    for result in ranked:
        source = source_by_cik.get(str(result.get("cik")), {})
        facts = source.get("facts") if isinstance(source.get("facts"), Mapping) else {}
        parent = facts.get("parent") if isinstance(facts, Mapping) else None
        distribution = facts.get("distribution_date") if isinstance(facts, Mapping) else None
        distribution_value = distribution.get("value") if isinstance(distribution, Mapping) else ""
        window_end = (
            date.fromisoformat(str(distribution_value))
            + timedelta(days=int(snapshot["window_days"]))
            if distribution_value
            else None
        )
        first = source.get("first_price") or {}
        factor_text = []
        for factor in result.get("factors", []):
            if factor.get("status") == "disabled":
                factor_text.append(f"{factor['name']}: disabled (0% weight)")
            else:
                factor_text.append(f"{factor['name']}: {factor.get('points')} points")
        lines.append(
            f"{result['rank']}. {result.get('company')} ({result.get('ticker') or 'ticker unavailable'})"
            f" | parent {parent.get('value') if isinstance(parent, Mapping) else 'unavailable'}"
            f" | distributed {distribution_value or 'unavailable'}"
            f" | window ends {window_end.isoformat() if window_end else 'unavailable'}"
            f" | {first.get('close', 'unavailable')} on {first.get('trading_date', 'unavailable')}"
            f" | points: {', '.join(factor_text)} | weighted total {result.get('total_score')}"
        )

    lines.extend(["", "## Unranked trading names"])
    unranked = [
        item
        for item in evaluation.get("records", [])
        if not item.get("rankable") and item.get("stage") in {"trading", "in_window", "past_window"}
    ]
    if not unranked:
        lines.append("None.")
    for item in unranked:
        reasons = item.get("unranked_reasons") or ["Outside the active ranking window."]
        lines.append(
            f"- {item.get('company')} ({item.get('ticker') or 'ticker unavailable'}): "
            + "; ".join(reasons)
        )

    lines.extend(["", "## Registered / watch list"])
    watch = [
        item
        for item in snapshot.get("records", [])
        if item.get("classification") == "spinoff"
        and item.get("stage") in {"registered", "listing_approved"}
    ]
    if not watch:
        lines.append("None.")
    for item in watch:
        filing = item.get("classification_filing") or {}
        lines.append(
            f"- {item.get('company')} ({item.get('ticker') or 'ticker unavailable'}): "
            f"{item.get('stage')}; {filing.get('form', 'Form 10')} "
            f"{filing.get('accession', '')} {filing.get('url', '')}".rstrip()
        )

    lines.extend(["", "## Dropped filers"])
    dropped = snapshot.get("dropped", [])
    if not dropped:
        lines.append("None.")
    for item in dropped:
        filing = item.get("classification_filing") or {}
        lines.append(
            f"- {item.get('company')}: {item.get('reason')} Supporting filing: "
            f"{filing.get('form', 'Form 10')} {filing.get('accession', '')} "
            f"{filing.get('url', '')}".rstrip()
        )

    lines.extend(["", "## Unavailable facts and limits"])
    unavailable = []
    for item in snapshot.get("records", []):
        for fact in item.get("unavailable_facts") or []:
            unavailable.append(f"- {item.get('company')}: {fact}. Left blank; not estimated.")
    lines.extend(unavailable or ["None."])
    lines.extend(
        [
            "",
            "First-price rule: each displayed first price is the earliest returned regular daily close strictly after the filing-proven distribution date. When-issued tickers and prices are rejected.",
            "",
            "screens, not recommendations",
        ]
    )
    return "\n".join(lines) + "\n"


def validate_report_contract(report: str) -> None:
    lines = report.splitlines()
    if not lines or not all(label in lines[0] for label in ("Run date:", "Price date:", "Index date:")):
        raise SeekerError("The report first line does not contain all three required dates.")
    if not lines or lines[-1] != "screens, not recommendations":
        raise SeekerError("The report final line is not the required disclaimer.")


def _merge_missing_facts(
    facts: dict[str, Any], replacement: Mapping[str, Any]
) -> None:
    for name in ("parent", "distribution_ratio", "record_date", "distribution_date"):
        if facts.get(name) is None and replacement.get(name) is not None:
            facts[name] = replacement[name]


def _download_parent_distribution_evidence(
    client: SecClient,
    parent: Company,
    registrant_name: str,
    filings: Sequence[Filing],
    raw_dir: Path,
    facts: dict[str, Any],
    start_date: date,
) -> list[dict[str, Any]]:
    wanted = _normalize_company_name(registrant_name)
    candidates = [
        filing
        for filing in filings
        if filing.form.upper() == "8-K"
        and filing.primary_document
        and (not filing.filing_date or filing.filing_date >= (start_date - timedelta(days=120)).isoformat())
    ]
    status_filings: list[dict[str, Any]] = []
    for filing in sorted(candidates, key=lambda item: item.filing_date, reverse=True)[:30]:
        url = filing.primary_document_url(parent.cik)
        resource = _save_sec_resource(
            client,
            url,
            raw_dir / f"parent_8-K_{filing.accession_number.replace('-', '')}.html",
        )
        text = resource_to_plain_text(resource)
        normalized = _normalize_company_name(text[:200_000])
        if wanted and wanted not in normalized:
            continue
        if not re.search(r"spin[- ]off|distribution|merger|record date", text, re.I):
            continue
        status_filings.append(
            {
                "form": "8-K",
                "accession": filing.accession_number,
                "filed_date": filing.filing_date,
                "url": url,
                "text": text,
            }
        )
        _merge_missing_facts(
            facts,
            extract_registry_facts(
                text,
                form="8-K",
                accession=filing.accession_number,
                url=url,
            ),
        )
        (raw_dir / f"parent_8-K_{filing.accession_number.replace('-', '')}.txt").write_text(
            text, encoding="utf-8"
        )
    return status_filings


def _save_cited_fact_sources(
    client: SecClient, raw_sec: Path, records: Sequence[Mapping[str, Any]]
) -> list[dict[str, str]]:
    """Persist any cited SEC source not already present in the run evidence."""
    existing_names = {path.name for path in raw_sec.rglob("*") if path.is_file()}
    saved: list[dict[str, str]] = []
    for record in records:
        facts = record.get("facts")
        if not isinstance(facts, Mapping):
            continue
        for name, fact in facts.items():
            if not isinstance(fact, Mapping):
                continue
            source = fact.get("source")
            if not isinstance(source, Mapping):
                continue
            url = str(source.get("url", ""))
            accession = str(source.get("accession", ""))
            match = re.search(r"/data/(\d+)/", url)
            if not url or not accession or not match:
                continue
            compact = accession.replace("-", "")
            if any(compact in filename or accession in filename for filename in existing_names):
                continue
            cik = int(match.group(1))
            destination = raw_sec / f"CIK{cik:010d}" / "cited_sources" / f"{source.get('form','SEC')}_{compact}.txt"
            _save_sec_resource(client, url, destination)
            existing_names.add(destination.name)
            saved.append({"fact": str(name), "accession": accession, "url": url, "path": str(destination)})
    return saved


def run_live_seeker(
    *,
    start_date: date,
    run_date: date,
    output_root: Path,
    resume_run: Path | None = None,
) -> Path:
    factors = load_factors(FINAL_FACTORS_PATH)
    team_inputs = _read_json(TEAM_INPUTS_PATH)
    if str(team_inputs.get("lab06_start_date")) != start_date.isoformat():
        raise SeekerError("The requested start date does not match the confirmed team input.")

    timestamp = datetime.now(EASTERN).strftime("%Y-%m-%d_%H-%M-%S-%f")
    run_dir = resume_run.expanduser().resolve() if resume_run else output_root / f"SEEKER_{timestamp}"
    raw_sec = run_dir / "raw" / "sec"
    raw_market = run_dir / "raw" / "financialdatasets"
    raw_sec.mkdir(parents=True, exist_ok=resume_run is not None)
    raw_market.mkdir(parents=True, exist_ok=True)

    client = SecClient(read_sec_user_agent(WORKSPACE_DIR))
    built_reader = build_closes_reader(WORKSPACE_DIR)
    market_reader = built_reader.readers[0]
    if not isinstance(market_reader, FinancialDatasetsClosesReader):
        raise SeekerError("The primary closes reader is not Financial Datasets.")

    ticker_resource = _save_sec_resource(
        client, SEC_TICKERS_URL, raw_sec / "company_tickers.json"
    )
    ticker_payload = json.loads(decode_resource(ticker_resource))
    company_records = _records(ticker_payload)
    by_cik = {
        int(item.get("cik_str")): item
        for item in company_records
        if str(item.get("cik_str", "")).isdigit()
    }

    scan_start = start_date - timedelta(days=180)
    index_rows: list[IndexRow] = []
    for year, quarter in quarters_between(scan_start, run_date):
        url = FORM_INDEX_URL.format(year=year, quarter=quarter)
        resource = _save_sec_resource(
            client, url, raw_sec / f"form_{year}_QTR{quarter}.idx"
        )
        index_rows.extend(parse_form_index(decode_resource(resource), scan_start, run_date))
    form10_by_cik: dict[int, list[IndexRow]] = defaultdict(list)
    cert_ciks = set()
    for row in index_rows:
        if row.form in FORM10_FORMS:
            form10_by_cik[row.cik].append(row)
        elif row.form == "CERT":
            cert_ciks.add(row.cik)

    records: list[dict[str, Any]] = []
    dropped: list[dict[str, Any]] = []
    for candidate_number, (cik, rows) in enumerate(sorted(form10_by_cik.items()), 1):
        record_from_tickers = by_cik.get(cik, {})
        company_name = str(record_from_tickers.get("title") or rows[-1].company)
        print(f"Candidate {candidate_number}/{len(form10_by_cik)}: {company_name}")
        candidate_dir = raw_sec / f"CIK{cik:010d}"
        histories = []
        for row in sorted(rows, key=lambda item: item.filed_date):
            resource = _save_sec_resource(
                client,
                row.url,
                candidate_dir / f"Form10_{row.accession}.txt",
            )
            raw = decode_resource(resource)
            documents = parse_submission_documents(raw, row.url)
            information = select_information_document(documents)
            text = information.text if information else "\n".join(item.text for item in documents)
            parsed_path = candidate_dir / f"Form10_{row.accession}_information.txt"
            parsed_path.parent.mkdir(parents=True, exist_ok=True)
            parsed_path.write_text(text, encoding="utf-8")
            histories.append(
                {
                    "form": row.form,
                    "accession": row.accession,
                    "filed_date": row.filed_date.isoformat(),
                    "url": row.url,
                    "text": text,
                }
            )
        classification = classify_registration_history(histories)
        classification_filing = {
            key: value
            for key, value in classification.get("filing", {}).items()
            if key != "text"
        }
        if classification["classification"] != "spinoff":
            dropped.append(
                {
                    "cik": cik,
                    "company": company_name,
                    "reason": classification["reason"],
                    "classification_filing": classification_filing,
                }
            )
            continue

        accepted = classification["filing"]
        facts = extract_registry_facts(
            str(accepted["text"]),
            form=str(accepted["form"]),
            accession=str(accepted["accession"]),
            url=str(accepted["url"]),
        )
        company = Company(
            ticker=str(record_from_tickers.get("ticker") or "").upper(),
            cik=cik,
            name=company_name,
        )
        submissions_url = SEC_SUBMISSIONS_URL.format(cik=cik)
        _save_sec_resource(
            client, submissions_url, candidate_dir / "submissions.json"
        )
        submissions_payload, company_filings = fetch_submission_filings(
            client, company, include_history=False
        )
        if not company.ticker:
            tickers = submissions_payload.get("tickers", [])
            if isinstance(tickers, list) and tickers:
                company = Company(str(tickers[0]).upper(), cik, company_name)

        parent_cik: int | None = None
        parent_record = None
        parent_status = {
            "classification": "spinoff",
            "reason": None,
            "record_date_withdrawn": False,
            "record_date_withdrawal_filing": None,
            "merger_filing": None,
        }
        parent_fact = facts.get("parent")
        if isinstance(parent_fact, Mapping) and parent_fact.get("value"):
            parent_record = resolve_company_by_name(
                str(parent_fact["value"]), company_records
            )
            if parent_record is not None:
                parent_cik = int(parent_record["cik_str"])
                # Use the canonical SEC registrant name after a source-backed match.
                parent_fact["value"] = str(parent_record.get("title", "")).strip()

        parent_assets = None
        if parent_record is not None and parent_cik is not None:
            parent = _company_from_record(parent_record, str(parent_fact["value"]))
            parent_dir = candidate_dir / f"parent_CIK{parent_cik:010d}"
            parent_submissions_url = SEC_SUBMISSIONS_URL.format(cik=parent_cik)
            _save_sec_resource(
                client, parent_submissions_url, parent_dir / "submissions.json"
            )
            _, parent_filings = fetch_submission_filings(client, parent, include_history=False)
            parent_status_filings = _download_parent_distribution_evidence(
                client,
                parent,
                company_name,
                parent_filings,
                parent_dir,
                facts,
                start_date,
            )
            parent_status = classify_parent_transaction_updates(
                parent_status_filings,
                accepted_filed_date=str(accepted["filed_date"]),
            )
            if parent_status["record_date_withdrawn"]:
                facts["record_date"] = None
            if parent_status["classification"] == "status_conflict":
                dropped.append(
                    {
                        "cik": cik,
                        "company": company_name,
                        "reason": parent_status["reason"],
                        "classification_filing": classification_filing,
                        "parent_status_correction": parent_status,
                    }
                )
                continue
            distribution_value = (
                facts.get("distribution_date", {}).get("value")
                if isinstance(facts.get("distribution_date"), Mapping)
                else None
            )
            target_date = _parse_date(str(distribution_value or accepted["filed_date"])) or run_date
            facts_resource = _save_sec_resource(
                client,
                SEC_COMPANY_FACTS_URL.format(cik=parent_cik),
                parent_dir / "companyfacts.json",
            )
            parent_facts_payload = json.loads(decode_resource(facts_resource))
            parent_assets = _xbrl_parent_assets(parent_facts_payload, target_date)

        distribution_fact = facts.get("distribution_date")
        distribution_date = (
            _parse_date(str(distribution_fact.get("value")))
            if isinstance(distribution_fact, Mapping)
            else None
        )
        if distribution_date is not None and distribution_date < start_date:
            dropped.append(
                {
                    "cik": cik,
                    "company": company_name,
                    "reason": f"Distribution date {distribution_date.isoformat()} is before the requested start date {start_date.isoformat()}.",
                    "classification_filing": classification_filing,
                }
            )
            continue

        proof_filings = [
            filing
            for filing in company_filings
            if filing.form.upper() in TRADING_PROOF_FORMS
            and filing.filing_date
            and filing.filing_date >= (distribution_date or start_date).isoformat()
        ]
        trading_filing = min(proof_filings, key=lambda item: item.filing_date) if proof_filings else None
        trading_proof = _filing_dict(trading_filing, cik) if trading_filing else None
        stage = determine_stage(
            run_date=run_date,
            distribution_date=distribution_date,
            has_certificate=cik in cert_ciks,
            trading_proof=trading_proof,
            window_days=int(factors["window_days_after_distribution"]),
        )

        unavailable = []
        for fact_name, label in (
            ("parent", "Parent"),
            ("distribution_ratio", "Distribution ratio"),
            ("record_date", "Record date"),
            ("distribution_date", "Distribution date"),
            ("spinoff_total_assets", "Spinoff total assets"),
        ):
            if facts.get(fact_name) is None:
                unavailable.append(label)
        if parent_cik is None:
            unavailable.append("Parent CIK")
        if parent_assets is None:
            unavailable.append("Parent total assets")
        if not company.ticker:
            unavailable.append("Trading ticker")

        first_price = None
        day20_price = None
        price_decline = None
        if distribution_date and company.ticker and trading_proof:
            price_end = min(run_date, distribution_date + timedelta(days=75))
            price_error = None
            try:
                closes = market_reader.daily_closes(
                    company.ticker,
                    distribution_date,
                    price_end,
                )
            except Exception as exc:
                closes = []
                price_error = f"{type(exc).__name__}: {exc}"
            _write_json(
                raw_market / f"{company.ticker}_{distribution_date.isoformat()}_{price_end.isoformat()}.json",
                {
                    "endpoint": "https://api.financialdatasets.ai/prices",
                    "ticker": company.ticker,
                    "start_date": distribution_date.isoformat(),
                    "end_date": price_end.isoformat(),
                    "responses": market_reader.last_payloads,
                    "error": price_error,
                },
            )
            first = first_close_after(closes, distribution_date)
            if first is not None:
                first_price = first.to_dict()
                twentieth = trading_day_close(closes, first, 20)
                if twentieth is not None:
                    day20_price = twentieth.to_dict()
                    price_decline = str(
                        ((first.close - twentieth.close) / first.close * Decimal(100)).quantize(
                            Decimal("0.0001"), rounding=ROUND_HALF_UP
                        )
                    )
                else:
                    unavailable.append("Closing price 20 trading days after the first close")
            else:
                unavailable.append("First regular close after distribution")
                if price_error:
                    unavailable.append(f"Financial Datasets price request ({price_error})")

        insider_purchases: list[dict[str, Any]] = []
        if distribution_date:
            insider_end = distribution_date + timedelta(days=30)
            for filing in company_filings:
                if filing.form.upper() not in {"4", "4/A"} or not filing.primary_document:
                    continue
                if filing.filing_date and filing.filing_date > (insider_end + timedelta(days=10)).isoformat():
                    continue
                url = filing.primary_document_url(cik)
                resource = _save_sec_resource(
                    client,
                    url,
                    candidate_dir / f"Form4_{filing.accession_number.replace('-', '')}.xml",
                )
                insider_purchases.extend(
                    _qualifying_form4_purchases(
                        decode_resource(resource),
                        start_date=distribution_date,
                        end_date=insider_end,
                        filing=filing,
                        source_url=url,
                    )
                )
        distinct_insiders = len(
            {item["owner"].casefold() for item in insider_purchases if item.get("owner")}
        ) if distribution_date else None

        spinoff_assets = facts.get("spinoff_total_assets")
        relative_size = None
        if isinstance(spinoff_assets, Mapping) and parent_assets is not None:
            numerator = _decimal(spinoff_assets.get("value"))
            denominator = _decimal(parent_assets.get("value"))
            if numerator is not None and denominator not in (None, Decimal(0)):
                relative_size = str((numerator / denominator).quantize(Decimal("0.00000001")))

        factor_inputs = {
            "relative_company_size_ratio": relative_size,
            "price_decline_percent": price_decline,
            "distinct_qualifying_insiders": distinct_insiders,
        }
        if relative_size is None:
            unavailable.append("Relative company size factor input")
        if price_decline is None:
            unavailable.append("Post-distribution price weakness factor input")
        if distinct_insiders is None:
            unavailable.append("Insider open-market buying factor input")
        records.append(
            {
                "cik": cik,
                "company": company_name,
                "ticker": company.ticker,
                "classification": "spinoff",
                "classification_reason": classification["reason"],
                "classification_filing": classification_filing,
                "later_filing_override": classification["later_filing_override"],
                "stage": stage,
                "parent_cik": parent_cik,
                "facts": facts,
                "parent_total_assets": parent_assets,
                "trading_proof": trading_proof,
                "first_price": first_price,
                "day20_price": day20_price,
                "insider_purchases": insider_purchases,
                "factor_inputs": factor_inputs,
                "unavailable_facts": list(dict.fromkeys(unavailable)),
            }
        )

    snapshot = {
        "start_date": start_date.isoformat(),
        "run_date": run_date.isoformat(),
        "index_date": run_date.isoformat(),
        "index_scan_start": scan_start.isoformat(),
        "window_days": factors["window_days_after_distribution"],
        "factor_configuration": factors,
        "records": records,
        "dropped": dropped,
    }
    cited_source_files = _save_cited_fact_sources(client, raw_sec, records)
    _write_json(run_dir / "cited_source_files.json", cited_source_files)
    evaluation = evaluate_snapshot(snapshot, factors)
    _write_json(run_dir / "evaluation_snapshot.json", snapshot)
    _write_json(run_dir / "evaluation_final.json", evaluation)
    registry_json, registry_csv = _write_registry(run_dir, [*records, *dropped])
    report = render_report(snapshot, evaluation)
    validate_report_contract(report)
    report_path = run_dir / "seeker_report.md"
    report_path.write_text(report, encoding="utf-8")
    manifest = {
        "run_date": run_date.isoformat(),
        "start_date": start_date.isoformat(),
        "factor_weights": [item["weight_percent"] for item in factors["factors"]],
        "factor_sha256": _file_sha256(FINAL_FACTORS_PATH),
        "registry_json": registry_json.name,
        "registry_csv": registry_csv.name,
        "report": report_path.name,
        "form10_candidate_count": len(form10_by_cik),
        "spinoff_count": len(records),
        "dropped_count": len(dropped),
        "ranked_count": len(evaluation["ranked"]),
    }
    _write_json(run_dir / "manifest.json", manifest)
    print(f"Run folder: {run_dir}")
    print(f"Registry: {registry_json}")
    print(f"Report: {report_path}")
    return run_dir


def prove_zero_weight(base_run: Path) -> Path:
    base_run = base_run.expanduser().resolve()
    snapshot = _read_json(base_run / "evaluation_snapshot.json")
    final_evaluation = _read_json(base_run / "evaluation_final.json")
    final_hash_before = _file_sha256(FINAL_FACTORS_PATH)
    zero_factors = load_factors(ZERO_FACTORS_PATH, allow_proof=True)
    timestamp = datetime.now(EASTERN).strftime("%Y-%m-%d_%H-%M-%S-%f")
    proof_dir = base_run / f"weight_zero_proof_{timestamp}"
    proof_dir.mkdir(parents=True, exist_ok=False)
    temporary_config = proof_dir / "temporary_factors_weight_zero.json"
    shutil.copyfile(ZERO_FACTORS_PATH, temporary_config)
    zero_evaluation = evaluate_snapshot(snapshot, zero_factors)

    final_by_cik = {str(item["cik"]): item for item in final_evaluation["records"]}
    comparisons = []
    passed = True
    zero_id = str(zero_factors["proof_zero_factor_id"])
    for zero_record in zero_evaluation["records"]:
        final_record = final_by_cik[str(zero_record["cik"])]
        final_factors = {item["id"]: item for item in final_record["factors"]}
        factor_checks = []
        for factor in zero_record["factors"]:
            original = final_factors[factor["id"]]
            if factor["id"] == zero_id:
                ok = factor["points"] is None and factor["status"] == "disabled" and factor["weighted_score"] == "0"
            else:
                ok = factor["points"] == original["points"]
            passed = passed and ok
            factor_checks.append(
                {
                    "factor_id": factor["id"],
                    "original_points": original["points"],
                    "proof_points": factor["points"],
                    "proof_status": factor["status"],
                    "unchanged_or_removed": ok,
                }
            )
        comparisons.append(
            {
                "cik": zero_record["cik"],
                "company": zero_record["company"],
                "factor_checks": factor_checks,
            }
        )
    final_hash_after = _file_sha256(FINAL_FACTORS_PATH)
    passed = passed and final_hash_before == final_hash_after
    proof = {
        "status": "PASS" if passed else "FAIL",
        "base_run": str(base_run),
        "zero_factor_id": zero_id,
        "temporary_configuration": str(temporary_config),
        "final_factor_hash_before": final_hash_before,
        "final_factor_hash_after": final_hash_after,
        "final_configuration_preserved": final_hash_before == final_hash_after,
        "comparisons": comparisons,
    }
    _write_json(proof_dir / "proof.json", proof)
    _write_json(proof_dir / "evaluation_weight_zero.json", zero_evaluation)
    report = render_report(snapshot, zero_evaluation)
    validate_report_contract(report)
    (proof_dir / "seeker_report_weight_zero.md").write_text(report, encoding="utf-8")
    if not passed:
        raise SeekerError(f"Weight-zero proof failed. See {proof_dir / 'proof.json'}")
    print(f"Weight-zero proof: {proof_dir / 'proof.json'}")
    return proof_dir


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic Lab 06 seeker.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Run the live seeker.")
    run_parser.add_argument("--start-date", required=True, type=date.fromisoformat)
    run_parser.add_argument("--end-date", type=date.fromisoformat, default=date.today())
    run_parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    run_parser.add_argument("--resume-run", type=Path)
    proof_parser = subparsers.add_parser(
        "prove-zero-weight", help="Prove the zero-weight rule from a saved run."
    )
    proof_parser.add_argument("--base-run", required=True, type=Path)
    return parser


def _main() -> int:
    args = _parser().parse_args()
    if args.command == "run":
        run_live_seeker(
            start_date=args.start_date,
            run_date=args.end_date,
            output_root=args.output_root,
            resume_run=args.resume_run,
        )
    elif args.command == "prove-zero-weight":
        prove_zero_weight(args.base_run)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(_main())
    except (OSError, ValueError, RuntimeError, SeekerError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
