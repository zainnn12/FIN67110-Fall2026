"""Build the SEC data layer for an equity-research workflow.

The script deliberately stops before model-driven research roles.  It resolves a
ticker, selects and downloads filings, extracts comparable XBRL facts, performs
deterministic calculations, extracts two earnings-release disclosures, and
repeats the quantitative work for optional peers.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, NavigableString
from dotenv import dotenv_values
from pypdf import PdfReader
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_SUBMISSIONS_FILE_URL = "https://data.sec.gov/submissions/{name}"
SEC_COMPANY_FACTS_URL = (
    "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
)
SEC_ARCHIVES_ROOT = "https://www.sec.gov/Archives/edgar/data"

ANNUAL_FORMS = {"10-K", "10-K/A"}
MIN_SEC_REQUEST_INTERVAL_SECONDS = 0.12
HTTP_TIMEOUT_SECONDS = 45


class DeskError(RuntimeError):
    """A concise, user-facing workflow error."""


@dataclass(frozen=True)
class Company:
    ticker: str
    cik: int
    name: str

    @property
    def padded_cik(self) -> str:
        return f"{self.cik:010d}"


@dataclass
class Filing:
    accession_number: str
    form: str
    filing_date: str
    report_date: str
    primary_document: str
    items: str
    acceptance_datetime: str
    accepted_from_index: str | None = None

    def archive_directory_url(self, cik: int) -> str:
        accession_compact = self.accession_number.replace("-", "")
        return f"{SEC_ARCHIVES_ROOT}/{cik}/{accession_compact}/"

    def primary_document_url(self, cik: int) -> str:
        return urljoin(self.archive_directory_url(cik), self.primary_document)

    def index_url(self, cik: int) -> str:
        return urljoin(
            self.archive_directory_url(cik),
            f"{self.accession_number}-index.html",
        )


@dataclass(frozen=True)
class DownloadedResource:
    url: str
    content: bytes
    content_type: str
    encoding: str | None


@dataclass(frozen=True)
class FactDefinition:
    key: str
    label: str
    tags: tuple[str, ...]
    preferred_units: tuple[str, ...]
    instant: bool


@dataclass(frozen=True)
class ReleaseMetricPair:
    """Current and prior-year-quarter values from one release table row."""

    current: Decimal
    prior: Decimal
    source_line: str
    unit: str | None = None


@dataclass(frozen=True)
class QuarterlyReleaseMetrics:
    revenue: ReleaseMetricPair
    gaap_diluted_eps: ReleaseMetricPair


FACT_DEFINITIONS: tuple[FactDefinition, ...] = (
    FactDefinition(
        "revenue",
        "Total revenue",
        (
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
            "OperatingRevenues",
            "RegulatedAndUnregulatedOperatingRevenue",
            "SalesRevenueGoodsNet",
            "SalesRevenueServicesNet",
            "InterestAndDividendIncomeOperating",
            "InsuranceRevenue",
        ),
        ("USD",),
        False,
    ),
    FactDefinition(
        "operating_income",
        "Operating income",
        ("OperatingIncomeLoss",),
        ("USD",),
        False,
    ),
    FactDefinition(
        "net_income",
        "Net income",
        (
            "NetIncomeLoss",
            "ProfitLoss",
            "NetIncomeLossAvailableToCommonStockholdersBasic",
        ),
        ("USD",),
        False,
    ),
    FactDefinition(
        "diluted_eps",
        "Diluted EPS",
        (
            "EarningsPerShareDiluted",
            "EarningsPerShareDilutedIncludingExtraordinaryItems",
        ),
        ("USD/shares",),
        False,
    ),
    FactDefinition(
        "stockholders_equity",
        "Stockholders' equity",
        (
            "StockholdersEquity",
            "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
            "PartnersCapital",
        ),
        ("USD",),
        True,
    ),
    FactDefinition(
        "long_term_debt",
        "Long-term debt",
        (
            "LongTermDebtNoncurrent",
            "LongTermDebtAndFinanceLeaseObligationsNoncurrent",
            "LongTermDebtAndCapitalLeaseObligationsNoncurrent",
        ),
        ("USD",),
        True,
    ),
    FactDefinition(
        "current_long_term_debt",
        "Current portion of long-term debt",
        (
            "LongTermDebtCurrent",
            "CurrentPortionOfLongTermDebt",
            "LongTermDebtAndFinanceLeaseObligationsCurrent",
            "LongTermDebtAndCapitalLeaseObligationsCurrent",
            "CurrentMaturitiesOfLongTermDebt",
        ),
        ("USD",),
        True,
    ),
    FactDefinition(
        "cash_from_operations",
        "Cash from operations",
        (
            "NetCashProvidedByUsedInOperatingActivities",
            "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        ),
        ("USD",),
        False,
    ),
    FactDefinition(
        "property_additions",
        "Additions to property and equipment",
        (
            "PaymentsToAcquirePropertyPlantAndEquipment",
            "PaymentsToAcquireProductiveAssets",
            "PaymentsForAdditionsToPropertyPlantAndEquipment",
            "PaymentsToAcquirePropertyPlantAndEquipmentAndIntangibleAssets",
        ),
        ("USD",),
        False,
    ),
)


STEP_TITLES = {
    1: "Resolve ticker to CIK",
    2: "Select filings and read EDGAR acceptance times",
    3: "Download filings and convert them to plain text",
    4: "Fetch and align annual XBRL company facts",
    5: "Calculate financial metrics",
    6: "Find quarterly revenue and diluted EPS in the release",
    7: "Collect peer facts and operating margins",
}


class SecClient:
    """A rate-limited SEC client that declares the configured user agent."""

    def __init__(
        self,
        user_agent: str,
        min_interval: float = MIN_SEC_REQUEST_INTERVAL_SECONDS,
    ) -> None:
        if not user_agent.strip():
            raise DeskError("SEC_USER_AGENT is empty in .env.")
        self.user_agent = user_agent.strip()
        self.min_interval = min_interval
        self._last_request_started = 0.0
        self._resource_cache: dict[str, DownloadedResource] = {}
        self._json_cache: dict[str, Any] = {}

        retry = Retry(
            total=4,
            connect=4,
            read=4,
            status=4,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"GET"}),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session = requests.Session()
        self.session.mount("https://", adapter)

    @staticmethod
    def _validate_sec_url(url: str) -> None:
        host = (urlparse(url).hostname or "").lower()
        if host != "sec.gov" and not host.endswith(".sec.gov"):
            raise DeskError(f"Refusing a non-SEC request: {url}")

    def fetch(self, url: str) -> DownloadedResource:
        self._validate_sec_url(url)
        if url in self._resource_cache:
            return self._resource_cache[url]

        elapsed = time.monotonic() - self._last_request_started
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        headers = {
            "User-Agent": self.user_agent,
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
        }
        self._last_request_started = time.monotonic()
        response = self.session.get(
            url,
            headers=headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise DeskError(
                f"SEC request failed with HTTP {response.status_code}: {url}"
            ) from exc

        resource = DownloadedResource(
            url=url,
            content=response.content,
            content_type=response.headers.get("Content-Type", ""),
            encoding=response.encoding,
        )
        self._resource_cache[url] = resource
        return resource

    def get_json(self, url: str) -> Any:
        if url in self._json_cache:
            return self._json_cache[url]
        resource = self.fetch(url)
        try:
            payload = json.loads(resource.content.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DeskError(f"SEC returned invalid JSON: {url}") from exc
        self._json_cache[url] = payload
        return payload


def read_sec_user_agent(base_dir: Path) -> str:
    env_path = base_dir / ".env"
    if not env_path.is_file():
        raise DeskError(f"Missing .env file: {env_path}")
    value = dotenv_values(env_path).get("SEC_USER_AGENT")
    if value is None or not str(value).strip():
        raise DeskError("SEC_USER_AGENT is missing or empty in .env.")
    return str(value).strip()


def normalize_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not ticker or not re.fullmatch(r"[A-Z0-9.-]+", ticker):
        raise DeskError(f"Invalid ticker: {value!r}")
    return ticker


def normalize_peer_arguments(values: Sequence[str]) -> list[str]:
    peers: list[str] = []
    for value in values:
        for item in value.split(","):
            ticker = normalize_ticker(item)
            if ticker not in peers:
                peers.append(ticker)
    return peers


def safe_path_component(value: str, limit: int = 90) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_value).strip("._-")
    return (cleaned or "company")[:limit]


def resolve_ticker(client: SecClient, ticker: str) -> Company:
    wanted = normalize_ticker(ticker)
    payload = client.get_json(SEC_TICKERS_URL)
    records: Iterable[dict[str, Any]]
    if isinstance(payload, dict):
        records = payload.values()
    elif isinstance(payload, list):
        records = payload
    else:
        raise DeskError("Unexpected structure in company_tickers.json.")

    for record in records:
        if str(record.get("ticker", "")).upper() == wanted:
            try:
                cik = int(record["cik_str"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DeskError(f"SEC returned an invalid CIK for {wanted}.") from exc
            return Company(
                ticker=wanted,
                cik=cik,
                name=str(record.get("title") or wanted),
            )
    raise DeskError(f"Ticker {wanted} was not found in SEC company_tickers.json.")


def _filings_from_columns(columns: dict[str, Any]) -> list[Filing]:
    accessions = columns.get("accessionNumber", [])
    if not isinstance(accessions, list):
        return []

    def cell(key: str, index: int) -> str:
        values = columns.get(key, [])
        if isinstance(values, list) and index < len(values):
            value = values[index]
            return "" if value is None else str(value)
        return ""

    results: list[Filing] = []
    for index, accession in enumerate(accessions):
        results.append(
            Filing(
                accession_number=str(accession),
                form=cell("form", index),
                filing_date=cell("filingDate", index),
                report_date=cell("reportDate", index),
                primary_document=cell("primaryDocument", index),
                items=cell("items", index),
                acceptance_datetime=cell("acceptanceDateTime", index),
            )
        )
    return results


def fetch_submission_filings(
    client: SecClient,
    company: Company,
    include_history: bool = False,
) -> tuple[dict[str, Any], list[Filing]]:
    url = SEC_SUBMISSIONS_URL.format(cik=company.padded_cik)
    payload = client.get_json(url)
    if not isinstance(payload, dict):
        raise DeskError("Unexpected structure in the SEC submissions response.")
    recent = payload.get("filings", {}).get("recent", {})
    filings = _filings_from_columns(recent if isinstance(recent, dict) else {})

    if include_history:
        extra_files = payload.get("filings", {}).get("files", [])
        for descriptor in extra_files if isinstance(extra_files, list) else []:
            name = descriptor.get("name") if isinstance(descriptor, dict) else None
            if not name:
                continue
            older_payload = client.get_json(
                SEC_SUBMISSIONS_FILE_URL.format(name=name)
            )
            if isinstance(older_payload, dict):
                filings.extend(_filings_from_columns(older_payload))
    return payload, filings


def filing_sort_key(filing: Filing) -> tuple[str, str, str]:
    return (
        filing.filing_date,
        filing.acceptance_datetime,
        filing.accession_number,
    )


def decode_resource(resource: DownloadedResource) -> str:
    encodings = [resource.encoding, "utf-8-sig", "utf-8", "latin-1"]
    for encoding in encodings:
        if not encoding:
            continue
        try:
            return resource.content.decode(encoding)
        except (LookupError, UnicodeDecodeError):
            continue
    return resource.content.decode("utf-8", errors="replace")


def resource_to_plain_text(resource: DownloadedResource) -> str:
    content_type = resource.content_type.lower()
    if "pdf" in content_type or resource.content.startswith(b"%PDF"):
        try:
            reader = PdfReader(io.BytesIO(resource.content))
            pages = [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # pypdf exposes several parser exceptions.
            raise DeskError(f"Could not extract text from PDF: {resource.url}") from exc
        return clean_plain_text("\n\n".join(pages))

    decoded = decode_resource(resource)
    looks_like_html = (
        "html" in content_type
        or bool(
            re.search(
                r"<\s*(?:html|body|div|table|p)\b",
                decoded[:5000],
                re.IGNORECASE,
            )
        )
    )
    if not looks_like_html:
        return clean_plain_text(decoded)

    soup = BeautifulSoup(decoded, "html.parser")
    for tag in soup.find_all(["script", "style", "noscript", "template"]):
        tag.decompose()

    for row in list(soup.find_all("tr")):
        cells = [
            clean_inline_text(cell.get_text(" ", strip=True))
            for cell in row.find_all(["th", "td"], recursive=False)
        ]
        cells = [cell for cell in cells if cell]
        if cells:
            row.replace_with(NavigableString("\n" + " | ".join(cells) + "\n"))

    return clean_plain_text(soup.get_text("\n"))


def clean_inline_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\u00a0", " ")).strip()


def clean_plain_text(value: str) -> str:
    lines: list[str] = []
    previous = None
    for raw_line in value.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = clean_inline_text(raw_line)
        if not line or line == previous:
            continue
        lines.append(line)
        previous = line
    return "\n".join(lines).strip() + "\n"


ITEM_202_RE = re.compile(r"\bItem\s*2\.02\b", re.IGNORECASE)


def select_required_filings(
    client: SecClient,
    company: Company,
    filings: Sequence[Filing],
) -> dict[str, Filing]:
    ordered = sorted(filings, key=filing_sort_key, reverse=True)

    def latest_form(form: str) -> Filing | None:
        return next(
            (
                filing
                for filing in ordered
                if filing.form.upper() == form and filing.primary_document
            ),
            None,
        )

    ten_k = latest_form("10-K")
    ten_q = latest_form("10-Q")
    if ten_k is None or ten_q is None:
        missing = "10-K" if ten_k is None else "10-Q"
        raise DeskError(f"No {missing} with a primary document was found.")

    eight_k_candidates = [
        filing
        for filing in ordered
        if filing.form.upper() == "8-K" and filing.primary_document
    ]
    metadata_matches = [
        filing
        for filing in eight_k_candidates
        if re.search(r"(?:^|[,\s])2\.02(?:$|[,\s])", filing.items)
    ]
    candidates = metadata_matches + [
        filing for filing in eight_k_candidates if filing not in metadata_matches
    ]

    item_202_filing = None
    for filing in candidates:
        resource = client.fetch(filing.primary_document_url(company.cik))
        if ITEM_202_RE.search(resource_to_plain_text(resource)):
            item_202_filing = filing
            break
    if item_202_filing is None:
        raise DeskError("No 8-K primary document reporting Item 2.02 was found.")

    return {"10-K": ten_k, "10-Q": ten_q, "8-K": item_202_filing}


def parse_filing_index(
    client: SecClient,
    company: Company,
    filing: Filing,
) -> tuple[str, str]:
    index_url = filing.index_url(company.cik)
    resource = client.fetch(index_url)
    html = decode_resource(resource)
    soup = BeautifulSoup(html, "html.parser")

    accepted = None
    for head in soup.find_all("div", class_="infoHead"):
        if clean_inline_text(head.get_text(" ", strip=True)).lower() != "accepted":
            continue
        sibling = head.find_next_sibling("div", class_="info")
        if sibling is not None:
            accepted = clean_inline_text(sibling.get_text(" ", strip=True))
            break
    if accepted is None:
        match = re.search(
            r"Accepted\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})",
            soup.get_text(" ", strip=True),
            re.IGNORECASE,
        )
        accepted = match.group(1) if match else None
    if accepted is None:
        raise DeskError(f"Accepted time was not found on EDGAR index: {index_url}")

    return accepted, html


def find_exhibit_991_url(index_url: str, index_html: str) -> str:
    soup = BeautifulSoup(index_html, "html.parser")
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if not cells:
            continue
        type_text = clean_inline_text(cells[3].get_text(" ", strip=True)).upper() if len(cells) > 3 else ""
        description = clean_inline_text(cells[1].get_text(" ", strip=True)).upper() if len(cells) > 1 else ""
        normalized_type = type_text.replace(" ", "")
        is_exhibit = bool(re.fullmatch(r"EX-99\.0?1", normalized_type))
        if not is_exhibit and not re.search(r"EXHIBIT\s+99\.0?1\b", description):
            continue
        link = row.find("a", href=True)
        if link is not None:
            return urljoin(index_url, str(link["href"]))
    raise DeskError("Exhibit 99.1 was not found on the selected 8-K index page.")


def parse_iso_date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def annual_points(
    concept: dict[str, Any],
    definition: FactDefinition,
) -> tuple[str | None, list[dict[str, Any]]]:
    units = concept.get("units", {})
    if not isinstance(units, dict):
        return None, []
    unit_order = list(definition.preferred_units) + [
        unit for unit in units if unit not in definition.preferred_units
    ]

    for unit in unit_order:
        raw_points = units.get(unit, [])
        if not isinstance(raw_points, list):
            continue
        selected: list[dict[str, Any]] = []
        for point in raw_points:
            if not isinstance(point, dict):
                continue
            if str(point.get("form", "")).upper() not in ANNUAL_FORMS:
                continue
            fiscal_period = str(point.get("fp", "")).upper()
            if fiscal_period not in {"", "FY"}:
                continue
            end = parse_iso_date(point.get("end"))
            if end is None or point.get("val") is None:
                continue
            if not definition.instant:
                start = parse_iso_date(point.get("start"))
                if start is None:
                    continue
                duration_days = (end - start).days
                if duration_days < 250 or duration_days > 450:
                    continue
            selected.append(point)
        if selected:
            return unit, selected
    return None, []


def select_fact_tag(
    company_facts: dict[str, Any],
    definition: FactDefinition,
) -> dict[str, Any]:
    taxonomy = company_facts.get("facts", {}).get("us-gaap", {})
    if not isinstance(taxonomy, dict):
        taxonomy = {}

    candidates: list[dict[str, Any]] = []
    for priority, tag in enumerate(definition.tags):
        concept = taxonomy.get(tag)
        if not isinstance(concept, dict):
            continue
        unit, points = annual_points(concept, definition)
        ends = [parse_iso_date(point.get("end")) for point in points]
        valid_ends = [end for end in ends if end is not None]
        if not valid_ends:
            continue
        candidates.append(
            {
                "tag": tag,
                "label": str(concept.get("label") or tag),
                "description": str(concept.get("description") or ""),
                "unit": unit,
                "points": points,
                "latest_end": max(valid_ends),
                "priority": priority,
            }
        )

    if not candidates:
        return {
            "tag": None,
            "label": definition.label,
            "description": "",
            "unit": None,
            "points": [],
            "latest_end": None,
        }
    return max(
        candidates,
        key=lambda item: (item["latest_end"], -item["priority"]),
    )


def point_for_end(
    points: Sequence[dict[str, Any]],
    period_end: date | None,
) -> dict[str, Any] | None:
    if period_end is None:
        return None
    matches = [
        point
        for point in points
        if parse_iso_date(point.get("end")) == period_end
    ]
    if not matches:
        return None
    return max(
        matches,
        key=lambda point: (
            str(point.get("filed", "")),
            str(point.get("accn", "")),
        ),
    )


def serializable_point(point: dict[str, Any] | None) -> dict[str, Any] | None:
    if point is None:
        return None
    keys = ("val", "start", "end", "accn", "fy", "fp", "form", "filed", "frame")
    return {key: point.get(key) for key in keys if point.get(key) is not None}


def extract_aligned_facts(
    company: Company,
    company_facts: dict[str, Any],
) -> dict[str, Any]:
    selected = {
        definition.key: select_fact_tag(company_facts, definition)
        for definition in FACT_DEFINITIONS
    }
    revenue_selection = selected["revenue"]
    revenue_ends = sorted(
        {
            end
            for end in (
                parse_iso_date(point.get("end"))
                for point in revenue_selection["points"]
            )
            if end is not None
        },
        reverse=True,
    )
    if not revenue_ends:
        raise DeskError(
            f"No annual total-revenue fact was found for {company.ticker}."
        )
    current_end = revenue_ends[0]
    prior_end = revenue_ends[1] if len(revenue_ends) > 1 else None

    facts: dict[str, Any] = {}
    for definition in FACT_DEFINITIONS:
        choice = selected[definition.key]
        facts[definition.key] = {
            "label": definition.label,
            "taxonomy": "us-gaap",
            "tag": choice["tag"],
            "xbrl_label": choice["label"],
            "unit": choice["unit"],
            "tag_latest_period_end": (
                choice["latest_end"].isoformat()
                if choice["latest_end"] is not None
                else None
            ),
            "current": serializable_point(
                point_for_end(choice["points"], current_end)
            ),
            "prior": serializable_point(
                point_for_end(choice["points"], prior_end)
            ),
        }

    return {
        "company": asdict(company),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "fiscal_year_period_end": current_end.isoformat(),
        "prior_year_period_end": prior_end.isoformat() if prior_end else None,
        "selection_rule": (
            "For each metric, select the candidate US-GAAP tag whose latest "
            "annual period end is newest; break ties by candidate order. Read "
            "current and prior facts at the same period ends selected from revenue."
        ),
        "facts": facts,
    }


def format_fact_value(value: Any, unit: str | None) -> str:
    if value is None:
        return "N/A"
    try:
        number = Decimal(str(value))
    except InvalidOperation:
        return str(value)
    if unit == "USD/shares":
        return f"{number:,.4f} {unit}"
    if unit == "USD":
        return f"{number:,.0f} {unit}"
    return f"{number:,} {unit or ''}".strip()


def point_filing(point: dict[str, Any] | None) -> str:
    if not point:
        return "N/A"
    form = point.get("form", "")
    accession = point.get("accn", "")
    filed = point.get("filed", "")
    return clean_inline_text(f"{form} {accession} filed {filed}")


def print_fact_set(fact_set: dict[str, Any]) -> None:
    print(
        "Fiscal-year alignment: "
        f"{fact_set['fiscal_year_period_end']} versus "
        f"{fact_set.get('prior_year_period_end') or 'N/A'}"
    )
    for definition in FACT_DEFINITIONS:
        fact = fact_set["facts"][definition.key]
        tag = fact.get("tag") or "N/A"
        unit = fact.get("unit")
        current = fact.get("current")
        prior = fact.get("prior")
        print(f"- {definition.label} [{tag}]")
        print(
            "  Current: "
            f"{format_fact_value(current.get('val') if current else None, unit)}; "
            f"period end {current.get('end') if current else 'N/A'}; "
            f"filing {point_filing(current)}"
        )
        print(
            "  Prior:   "
            f"{format_fact_value(prior.get('val') if prior else None, unit)}; "
            f"period end {prior.get('end') if prior else 'N/A'}; "
            f"filing {point_filing(prior)}"
        )


def decimal_fact(
    fact_set: dict[str, Any],
    key: str,
    period: str = "current",
) -> Decimal | None:
    point = fact_set.get("facts", {}).get(key, {}).get(period)
    if not point or point.get("val") is None:
        return None
    try:
        value = Decimal(str(point["val"]))
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


def number(value: Decimal) -> str:
    return f"{value:,.4f}".rstrip("0").rstrip(".")


def percent(value: Decimal) -> str:
    return f"{value * Decimal(100):,.2f}%"


def ratio_or_none(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def calculate_metrics(
    fact_set: dict[str, Any],
    price: Decimal | None,
) -> list[tuple[str, str]]:
    revenue = decimal_fact(fact_set, "revenue")
    prior_revenue = decimal_fact(fact_set, "revenue", "prior")
    operating_income = decimal_fact(fact_set, "operating_income")
    net_income = decimal_fact(fact_set, "net_income")
    equity = decimal_fact(fact_set, "stockholders_equity")
    prior_equity = decimal_fact(fact_set, "stockholders_equity", "prior")
    long_term_debt = decimal_fact(fact_set, "long_term_debt")
    current_long_term_debt = decimal_fact(fact_set, "current_long_term_debt")
    cash_from_operations = decimal_fact(fact_set, "cash_from_operations")
    property_additions = decimal_fact(fact_set, "property_additions")
    diluted_eps = decimal_fact(fact_set, "diluted_eps")

    results: list[tuple[str, str]] = []

    growth = None
    if revenue is not None and prior_revenue not in {None, Decimal(0)}:
        growth = (revenue - prior_revenue) / prior_revenue
    results.append(
        (
            "Revenue growth",
            (
                f"({number(revenue)} - {number(prior_revenue)}) / "
                f"{number(prior_revenue)} = {percent(growth)}"
                if growth is not None and revenue is not None and prior_revenue is not None
                else "N/A (current and prior revenue are required)"
            ),
        )
    )

    operating_margin = ratio_or_none(operating_income, revenue)
    results.append(
        (
            "Operating margin",
            (
                f"{number(operating_income)} / {number(revenue)} = "
                f"{percent(operating_margin)}"
                if operating_margin is not None and operating_income is not None and revenue is not None
                else "N/A (operating income and revenue are required)"
            ),
        )
    )

    average_equity = None
    if equity is not None and prior_equity is not None:
        average_equity = (equity + prior_equity) / Decimal(2)
    roe = ratio_or_none(net_income, average_equity)
    results.append(
        (
            "Return on average equity",
            (
                f"{number(net_income)} / (({number(equity)} + "
                f"{number(prior_equity)}) / 2) = {percent(roe)}"
                if roe is not None
                and net_income is not None
                and equity is not None
                and prior_equity is not None
                else "N/A (net income and current/prior equity are required)"
            ),
        )
    )

    debt_to_equity = None
    if long_term_debt is not None and current_long_term_debt is not None:
        debt_to_equity = ratio_or_none(long_term_debt + current_long_term_debt, equity)
    results.append(
        (
            "Debt to equity",
            (
                f"({number(long_term_debt)} + {number(current_long_term_debt)}) / "
                f"{number(equity)} = {number(debt_to_equity)}x"
                if debt_to_equity is not None
                and long_term_debt is not None
                and current_long_term_debt is not None
                and equity is not None
                else "N/A (noncurrent debt, current debt, and equity are required)"
            ),
        )
    )

    free_cash_flow = None
    if cash_from_operations is not None and property_additions is not None:
        free_cash_flow = cash_from_operations - property_additions
    results.append(
        (
            "Free cash flow",
            (
                f"{number(cash_from_operations)} - {number(property_additions)} = "
                f"{number(free_cash_flow)}"
                if free_cash_flow is not None
                and cash_from_operations is not None
                and property_additions is not None
                else "N/A (cash from operations and property additions are required)"
            ),
        )
    )

    pe = ratio_or_none(price, diluted_eps) if price is not None else None
    if price is None:
        pe_text = "N/A (--price was not supplied)"
    elif pe is None or diluted_eps is None:
        pe_text = "N/A (nonzero diluted EPS is required)"
    else:
        pe_text = f"{number(price)} / {number(diluted_eps)} = {number(pe)}x"
    results.append(("P/E", pe_text))

    return results


REVENUE_LINE_RE = re.compile(
    r"\b(?:"
    r"total\s+(?:net\s+)?(?:revenue|revenues|sales)|"
    r"quarterly\s+(?:net\s+)?(?:revenue|revenues|sales)|"
    r"(?:net\s+)?(?:revenue|revenues)\s+"
    r"(?:was|were|of|totaled|reached)"
    r")\b",
    re.IGNORECASE,
)
DILUTED_EPS_LINE_RE = re.compile(
    r"(?:\bdiluted\b.{0,160}\b(?:EPS|earnings?|income|loss)\b|"
    r"\b(?:EPS|earnings?|income|loss)\b.{0,160}\bdiluted\b)",
    re.IGNORECASE,
)
NUMERIC_LINE_RE = re.compile(
    r"(?<![A-Za-z])(?:[$€£]\s*)?\(?-?\d[\d,]*(?:\.\d+)?\)?"
    r"(?:\s*(?:%|million|billion|thousand))?",
    re.IGNORECASE,
)


def matching_release_lines(text: str, pattern: re.Pattern[str]) -> list[str]:
    matches: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = clean_inline_text(raw_line)
        if len(line) < 4 or len(line) > 800:
            continue
        if not pattern.search(line) or not NUMERIC_LINE_RE.search(line):
            continue
        key = line.casefold()
        if key not in seen:
            matches.append(line)
            seen.add(key)
    return matches[:12]


NON_GAAP_LABEL_RE = re.compile(
    r"\b(?:adjusted|non[\s-]?GAAP|normalized|core|comparable)\b|"
    r"\(\s*cc\s*\)|\bconstant\s+currency\b",
    re.IGNORECASE,
)
REVENUE_ROW_LABEL_RE = re.compile(
    r"^(?:total\s+)?(?:(?:net|operating)\s+)?"
    r"(?:revenues?|sales)(?:\s*,\s*net)?$",
    re.IGNORECASE,
)
RELEASE_NUMBER_CELL_RE = re.compile(
    r"^\s*(?P<outer_open>\()?\s*(?:[$€£]\s*)?"
    r"(?P<inner_open>\()?\s*(?P<sign>[-−])?\s*"
    r"(?P<number>\d[\d,]*(?:\.\d+)?)\s*\)?\s*"
    r"(?P<scale>thousands?|millions?|billions?)?\s*\)?\s*$",
    re.IGNORECASE,
)
RELEASE_UNIT_RE = re.compile(
    r"\bin\s+(?P<scale>thousands?|millions?|billions?)\b",
    re.IGNORECASE,
)
RELEASE_EPS_SECTION_HEADING_RE = re.compile(
    r"\b(?:net\s+income|(?:net\s+)?loss|earnings?)\s+per\s+"
    r"(?:common\s+)?shares?\b",
    re.IGNORECASE,
)
RELEASE_SHARE_COUNT_SECTION_RE = re.compile(
    r"\b(?:"
    r"shares?\s+used\s+(?:in|for|to)\b|"
    r"(?:weighted[\s-]*average|average)\b.{0,80}\bshares?\b|"
    r"shares?\b.{0,80}\b(?:outstanding|used\s+(?:in|for|to))\b"
    r")",
    re.IGNORECASE,
)
RELEASE_EPS_ABBREVIATION_RE = re.compile(r"\bEPS\b", re.IGNORECASE)


def _release_table_values(line: str) -> tuple[list[Decimal], list[str]]:
    """Return non-percentage numeric cells after a release row label."""

    cells = line.split("|")
    if len(cells) < 3:
        return [], []

    values: list[Decimal] = []
    units: list[str] = []
    for index, raw_cell in enumerate(cells[1:], start=1):
        cell = clean_inline_text(raw_cell)
        next_cell = (
            clean_inline_text(cells[index + 1])
            if index + 1 < len(cells)
            else ""
        )
        if "%" in cell or re.fullmatch(r"%\)?", next_cell):
            continue
        match = RELEASE_NUMBER_CELL_RE.fullmatch(cell)
        if match is None:
            continue
        try:
            value = Decimal(match.group("number").replace(",", ""))
        except InvalidOperation:
            continue
        if match.group("sign") or match.group("outer_open") or match.group("inner_open"):
            value = -value
        values.append(value)
        scale = match.group("scale")
        if scale:
            units.append(scale.lower().rstrip("s"))
    return values, units


def _release_row_label(line: str) -> str:
    label = clean_inline_text(line.split("|", 1)[0]).rstrip(":")
    return re.sub(r"\s+\d+$", "", label).strip()


def _nearest_release_eps_section(
    lines: Sequence[str],
    index: int,
) -> str | None:
    """Classify the nearest preceding EPS or share-count section marker."""

    for context_line in reversed(lines[max(0, index - 20) : index]):
        if RELEASE_SHARE_COUNT_SECTION_RE.search(context_line):
            return "share_count"
        is_eps_section = bool(
            RELEASE_EPS_SECTION_HEADING_RE.search(context_line)
            or RELEASE_EPS_ABBREVIATION_RE.search(context_line)
        )
        if not is_eps_section:
            continue
        if NON_GAAP_LABEL_RE.search(context_line):
            return "non_gaap"
        if RELEASE_EPS_SECTION_HEADING_RE.search(context_line):
            return "gaap"
    return None


def _release_context_score(lines: Sequence[str], index: int) -> int:
    context = " ".join(lines[max(0, index - 40) : index]).casefold()
    score = 0
    if re.search(
        r"consolidated\s+statements?\s+of\s+"
        r"(?:income|operations|earnings|comprehensive\s+income)",
        context,
    ):
        score += 100
    if re.search(r"\b(?:three\s+months|quarter)\s+ended\b", context):
        score += 20
    if re.search(r"\b(?:reconciliation|non[\s-]?gaap|adjusted\s+eps)\b", context):
        score -= 40
    if re.search(r"\bsegment\s+information\b", context):
        score -= 20
    return score


def _release_value_unit(
    lines: Sequence[str],
    index: int,
    inline_units: Sequence[str],
) -> str | None:
    if inline_units and len(set(inline_units[:2])) == 1:
        return inline_units[0]
    for context_line in reversed(lines[max(0, index - 20) : index]):
        match = RELEASE_UNIT_RE.search(context_line)
        if match:
            return match.group("scale").lower().rstrip("s")
    return None


def _select_release_revenue(lines: Sequence[str]) -> ReleaseMetricPair | None:
    candidates: list[tuple[int, int, ReleaseMetricPair]] = []
    for index, line in enumerate(lines):
        label = _release_row_label(line)
        if NON_GAAP_LABEL_RE.search(label) or not REVENUE_ROW_LABEL_RE.fullmatch(label):
            continue
        values, inline_units = _release_table_values(line)
        if len(values) < 2:
            continue
        label_folded = label.casefold()
        label_score = 40 if "revenue" in label_folded else 20
        if label_folded.startswith("total "):
            label_score += 20
        score = _release_context_score(lines, index) + label_score
        candidates.append(
            (
                score,
                -index,
                ReleaseMetricPair(
                    current=values[0],
                    prior=values[1],
                    source_line=line,
                    unit=_release_value_unit(lines, index, inline_units),
                ),
            )
        )
    return max(candidates, default=(0, 0, None), key=lambda item: item[:2])[2]


def _select_release_gaap_diluted_eps(
    lines: Sequence[str],
) -> ReleaseMetricPair | None:
    candidates: list[tuple[int, int, ReleaseMetricPair]] = []
    for index, line in enumerate(lines):
        label = _release_row_label(line)
        is_bare_diluted = bool(re.fullmatch(r"diluted", label, re.IGNORECASE))
        if NON_GAAP_LABEL_RE.search(label) or (
            not is_bare_diluted and not DILUTED_EPS_LINE_RE.search(label)
        ):
            continue
        label_folded = label.casefold()
        if is_bare_diluted:
            is_per_share = _nearest_release_eps_section(lines, index) == "gaap"
        else:
            is_per_share = "eps" in label_folded or (
                "per" in label_folded
                and "share" in label_folded
                and re.search(r"\b(?:earnings?|income|loss)\b", label, re.IGNORECASE)
            )
        if not is_per_share:
            continue
        values, _ = _release_table_values(line)
        if len(values) < 2:
            continue
        score = _release_context_score(lines, index)
        if re.search(r"\bGAAP\b", label, re.IGNORECASE):
            score += 20
        if label_folded.startswith("diluted"):
            score += 10
        candidates.append(
            (
                score,
                -index,
                ReleaseMetricPair(
                    current=values[0],
                    prior=values[1],
                    source_line=line,
                ),
            )
        )
    return max(candidates, default=(0, 0, None), key=lambda item: item[:2])[2]


def parse_quarterly_release_metrics(text: str) -> QuarterlyReleaseMetrics:
    lines = [
        clean_inline_text(raw_line)
        for raw_line in text.splitlines()
        if clean_inline_text(raw_line)
    ]
    revenue = _select_release_revenue(lines)
    if revenue is None:
        raise DeskError(
            "No release table row with current and prior quarterly revenue was found."
        )
    diluted_eps = _select_release_gaap_diluted_eps(lines)
    if diluted_eps is None:
        raise DeskError(
            "No release table row with current and prior GAAP diluted EPS was found; "
            "adjusted and non-GAAP rows are excluded."
        )
    return QuarterlyReleaseMetrics(
        revenue=revenue,
        gaap_diluted_eps=diluted_eps,
    )


def _release_number(value: Decimal) -> str:
    decimal_places = max(0, -value.as_tuple().exponent)
    return f"{value:,.{decimal_places}f}"


def _release_currency(value: Decimal, unit: str | None = None) -> str:
    sign = "-" if value < 0 else ""
    result = f"{sign}${_release_number(abs(value))}"
    return f"{result} {unit}" if unit else result


def format_quarterly_release_metrics(
    metrics: QuarterlyReleaseMetrics,
    accession_number: str,
) -> list[str]:
    revenue = metrics.revenue
    diluted_eps = metrics.gaap_diluted_eps
    if revenue.prior == 0:
        growth_arithmetic = "N/A (prior-year-quarter revenue is zero)"
    else:
        growth = (revenue.current - revenue.prior) / revenue.prior
        growth_arithmetic = (
            f"({_release_currency(revenue.current)} - "
            f"{_release_currency(revenue.prior)}) / "
            f"{_release_currency(revenue.prior)} = {percent(growth)}"
        )
    return [
        f"Current-quarter revenue: {_release_currency(revenue.current, revenue.unit)}",
        f"Prior-year-quarter revenue: {_release_currency(revenue.prior, revenue.unit)}",
        f"Revenue growth arithmetic: {growth_arithmetic}",
        "Current-quarter GAAP diluted EPS: "
        f"{_release_currency(diluted_eps.current)}",
        "Prior-year-quarter GAAP diluted EPS: "
        f"{_release_currency(diluted_eps.prior)}",
        f"Revenue source release line: {revenue.source_line}",
        f"GAAP diluted-EPS source release line: {diluted_eps.source_line}",
        f"Source release accession number: {accession_number}",
    ]


def save_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def save_facts_csv(path: Path, fact_set: dict[str, Any]) -> None:
    columns = [
        "metric",
        "label",
        "taxonomy",
        "tag",
        "unit",
        "tag_latest_period_end",
        "current_value",
        "current_start",
        "current_end",
        "current_form",
        "current_accession",
        "current_filed",
        "prior_value",
        "prior_start",
        "prior_end",
        "prior_form",
        "prior_accession",
        "prior_filed",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for definition in FACT_DEFINITIONS:
            fact = fact_set["facts"][definition.key]
            current = fact.get("current") or {}
            prior = fact.get("prior") or {}
            writer.writerow(
                {
                    "metric": definition.key,
                    "label": fact.get("label"),
                    "taxonomy": fact.get("taxonomy"),
                    "tag": fact.get("tag"),
                    "unit": fact.get("unit"),
                    "tag_latest_period_end": fact.get("tag_latest_period_end"),
                    "current_value": current.get("val"),
                    "current_start": current.get("start"),
                    "current_end": current.get("end"),
                    "current_form": current.get("form"),
                    "current_accession": current.get("accn"),
                    "current_filed": current.get("filed"),
                    "prior_value": prior.get("val"),
                    "prior_start": prior.get("start"),
                    "prior_end": prior.get("end"),
                    "prior_form": prior.get("form"),
                    "prior_accession": prior.get("accn"),
                    "prior_filed": prior.get("filed"),
                }
            )


class EquityResearchDataDesk:
    def __init__(
        self,
        client: SecClient,
        ticker: str,
        peers: Sequence[str],
        price: Decimal | None,
        base_dir: Path,
    ) -> None:
        self.client = client
        self.ticker = normalize_ticker(ticker)
        self.peers = [peer for peer in peers if peer != self.ticker]
        self.price = price
        self.base_dir = base_dir
        self.run_started = datetime.now().astimezone()
        self.company: Company | None = None
        self.submissions_payload: dict[str, Any] | None = None
        self.filings: list[Filing] | None = None
        self.selected_filings: dict[str, Filing] | None = None
        self.index_html: dict[str, str] = {}
        self.output_dir: Path | None = None
        self.document_texts: dict[str, str] = {}
        self.release_text: str | None = None
        self.fact_set: dict[str, Any] | None = None

    def print_step(self, step: int) -> None:
        print(f"\n[Step {step}/7] {STEP_TITLES[step]}")

    def ensure_company(self) -> Company:
        if self.company is None:
            self.company = resolve_ticker(self.client, self.ticker)
        return self.company

    def ensure_output_dir(self) -> Path:
        if self.output_dir is None:
            company = self.ensure_company()
            stamp = self.run_started.strftime("%Y-%m-%d_%H-%M-%S")
            folder = f"{safe_path_component(company.name)}_{stamp}"
            self.output_dir = self.base_dir / "runs" / folder
            self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir

    def ensure_filings(self) -> dict[str, Filing]:
        if self.selected_filings is not None:
            return self.selected_filings
        company = self.ensure_company()
        payload, filings = fetch_submission_filings(self.client, company)
        try:
            selected = select_required_filings(self.client, company, filings)
        except DeskError:
            payload, filings = fetch_submission_filings(
                self.client, company, include_history=True
            )
            selected = select_required_filings(self.client, company, filings)
        self.submissions_payload = payload
        self.filings = filings
        self.selected_filings = selected
        return selected

    def ensure_index_details(self) -> None:
        company = self.ensure_company()
        for label, filing in self.ensure_filings().items():
            if filing.accepted_from_index is not None and label in self.index_html:
                continue
            accepted, html = parse_filing_index(self.client, company, filing)
            filing.accepted_from_index = accepted
            self.index_html[label] = html

    def ensure_fact_set(self) -> dict[str, Any]:
        if self.fact_set is None:
            company = self.ensure_company()
            url = SEC_COMPANY_FACTS_URL.format(cik=company.padded_cik)
            payload = self.client.get_json(url)
            if not isinstance(payload, dict):
                raise DeskError("Unexpected structure in SEC company facts.")
            self.fact_set = extract_aligned_facts(company, payload)
        return self.fact_set

    def ensure_release_text(self) -> str:
        if self.release_text is not None:
            return self.release_text
        company = self.ensure_company()
        selected = self.ensure_filings()
        self.ensure_index_details()
        filing = selected["8-K"]
        exhibit_url = find_exhibit_991_url(
            filing.index_url(company.cik), self.index_html["8-K"]
        )
        self.release_text = resource_to_plain_text(self.client.fetch(exhibit_url))
        return self.release_text

    def step_1(self) -> None:
        self.print_step(1)
        company = self.ensure_company()
        print(f"Ticker: {company.ticker}")
        print(f"Company: {company.name}")
        print(f"CIK: {company.padded_cik}")

    def step_2(self) -> None:
        self.print_step(2)
        self.ensure_index_details()
        selected = self.ensure_filings()
        print(f"Submissions API filings examined: {len(self.filings or [])}")
        labels = (
            ("Latest 10-K", "10-K"),
            ("Latest 10-Q", "10-Q"),
            ("Latest 8-K reporting Item 2.02", "8-K"),
        )
        for display, key in labels:
            filing = selected[key]
            print(
                f"{display}: accession {filing.accession_number}; "
                f"Accepted {filing.accepted_from_index}"
            )

    def step_3(self) -> None:
        self.print_step(3)
        company = self.ensure_company()
        selected = self.ensure_filings()
        self.ensure_index_details()
        output_dir = self.ensure_output_dir()

        downloads: list[tuple[str, str, Filing | None]] = []
        for key in ("10-K", "10-Q", "8-K"):
            filing = selected[key]
            downloads.append(
                (key, filing.primary_document_url(company.cik), filing)
            )
        exhibit_url = find_exhibit_991_url(
            selected["8-K"].index_url(company.cik), self.index_html["8-K"]
        )
        downloads.append(("8-K_EX-99.1", exhibit_url, selected["8-K"]))

        manifest_documents: list[dict[str, Any]] = []
        for label, url, filing in downloads:
            text = resource_to_plain_text(self.client.fetch(url))
            filename = (
                f"{safe_path_component(label)}_"
                f"{filing.accession_number.replace('-', '')}.txt"
            )
            path = output_dir / filename
            path.write_text(text, encoding="utf-8")
            self.document_texts[label] = text
            if label == "8-K_EX-99.1":
                self.release_text = text
            print(f"Saved {label}: {path}")
            manifest_documents.append(
                {
                    "label": label,
                    "source_url": url,
                    "text_file": filename,
                    "accession_number": filing.accession_number,
                    "accepted": filing.accepted_from_index,
                }
            )

        manifest = {
            "company": asdict(company),
            "run_started": self.run_started.isoformat(timespec="seconds"),
            "documents": manifest_documents,
        }
        save_json(output_dir / "manifest.json", manifest)
        print(f"Run folder: {output_dir}")

    def step_4(self) -> None:
        self.print_step(4)
        fact_set = self.ensure_fact_set()
        print_fact_set(fact_set)
        output_dir = self.ensure_output_dir()
        json_path = output_dir / "facts.json"
        csv_path = output_dir / "facts.csv"
        save_json(json_path, fact_set)
        save_facts_csv(csv_path, fact_set)
        print(f"Saved facts: {json_path}")
        print(f"Saved facts: {csv_path}")

    def step_5(self) -> None:
        self.print_step(5)
        for label, calculation in calculate_metrics(
            self.ensure_fact_set(), self.price
        ):
            print(f"{label}: {calculation}")

    def step_6(self) -> None:
        self.print_step(6)
        release_text = self.ensure_release_text()
        metrics = parse_quarterly_release_metrics(release_text)
        accession_number = self.ensure_filings()["8-K"].accession_number
        for output_line in format_quarterly_release_metrics(
            metrics,
            accession_number,
        ):
            print(output_line)

    def step_7(self) -> None:
        self.print_step(7)
        if not self.peers:
            print("No peers supplied.")
            return
        output_dir = self.ensure_output_dir()
        for ticker in self.peers:
            company = resolve_ticker(self.client, ticker)
            url = SEC_COMPANY_FACTS_URL.format(cik=company.padded_cik)
            payload = self.client.get_json(url)
            if not isinstance(payload, dict):
                raise DeskError(f"Unexpected company-facts response for {ticker}.")
            fact_set = extract_aligned_facts(company, payload)
            print(f"\nPeer: {company.ticker} | {company.name} | CIK {company.padded_cik}")
            print_fact_set(fact_set)
            margin_row = dict(calculate_metrics(fact_set, None))["Operating margin"]
            print(f"Operating margin: {margin_row}")
            stem = f"facts_{safe_path_component(company.ticker)}"
            json_path = output_dir / f"{stem}.json"
            csv_path = output_dir / f"{stem}.csv"
            save_json(json_path, fact_set)
            save_facts_csv(csv_path, fact_set)
            print(f"Saved peer facts: {json_path}")
            print(f"Saved peer facts: {csv_path}")

    def run(self, step: int | None) -> None:
        if step is not None:
            getattr(self, f"step_{step}")()
            return
        for step_number in range(1, 8):
            getattr(self, f"step_{step_number}")()


def decimal_argument(value: str) -> Decimal:
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not result.is_finite() or result < 0:
        raise argparse.ArgumentTypeError("must be a finite, nonnegative number")
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect SEC filings and comparable annual facts for equity research."
    )
    parser.add_argument("ticker", help="Primary ticker symbol")
    parser.add_argument(
        "--peers",
        nargs="*",
        default=[],
        metavar="TICKER",
        help="Optional peer tickers, separated by spaces or commas",
    )
    parser.add_argument(
        "--price",
        type=decimal_argument,
        help="Optional share price used for P/E",
    )
    parser.add_argument(
        "--step",
        type=int,
        choices=range(1, 8),
        help="Run only one numbered step (1-7)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    base_dir = Path(__file__).resolve().parent
    try:
        peers = normalize_peer_arguments(args.peers)
        user_agent = read_sec_user_agent(base_dir)
        client = SecClient(user_agent)
        desk = EquityResearchDataDesk(
            client=client,
            ticker=args.ticker,
            peers=peers,
            price=args.price,
            base_dir=base_dir,
        )
        desk.run(args.step)
    except (DeskError, requests.RequestException, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
