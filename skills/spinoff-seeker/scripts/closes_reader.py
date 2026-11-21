#!/usr/bin/env python3
"""Read unadjusted daily closes without exposing raw vendor data to a model."""

from __future__ import annotations

import csv
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping, Protocol, Sequence
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from dotenv import dotenv_values


EASTERN = ZoneInfo("America/New_York")
FINANCIAL_DATASETS_PRICES_URL = "https://api.financialdatasets.ai/prices"
NASDAQ_HISTORY_URL = "https://api.nasdaq.com/api/quote/{ticker}/historical"
HTTP_TIMEOUT_SECONDS = 45


class CloseReaderError(RuntimeError):
    """A close source could not return contract-compliant data."""


@dataclass(frozen=True, order=True)
class DailyClose:
    trading_date: date
    close: Decimal
    ticker: str
    source: str

    def to_dict(self) -> dict[str, str]:
        payload = asdict(self)
        payload["trading_date"] = self.trading_date.isoformat()
        payload["close"] = str(self.close)
        return payload


class ClosesReader(Protocol):
    def daily_closes(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[DailyClose]: ...


def _decimal(value: object) -> Decimal:
    cleaned = re.sub(r"[^0-9.()\-]", "", str(value)).strip()
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        result = Decimal(cleaned)
    except InvalidOperation as exc:
        raise CloseReaderError(f"Invalid close value: {value!r}") from exc
    if not result.is_finite() or result <= 0:
        raise CloseReaderError(f"Close must be a positive finite number: {value!r}")
    return result


def _normalize_ticker(value: str) -> str:
    ticker = value.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,14}", ticker):
        raise CloseReaderError(f"Invalid ticker: {value!r}")
    if ticker.endswith(("-WI", ".WI", " WI")):
        raise CloseReaderError("A when-issued ticker is not permitted.")
    return ticker


def first_close_after(
    closes: Iterable[DailyClose], distribution_date: date
) -> DailyClose | None:
    """Return the first regular close strictly after the distribution date."""
    eligible = sorted(item for item in closes if item.trading_date > distribution_date)
    return eligible[0] if eligible else None


def trading_day_close(
    closes: Iterable[DailyClose], first: DailyClose, offset: int
) -> DailyClose | None:
    """Return the close `offset` trading rows after `first` (offset 20 is day 20)."""
    if offset < 0:
        raise ValueError("Trading-day offset must be non-negative.")
    ordered = sorted(item for item in closes if item.trading_date >= first.trading_date)
    if not ordered or ordered[0].trading_date != first.trading_date:
        return None
    return ordered[offset] if len(ordered) > offset else None


def last_close_before(
    closes: Iterable[DailyClose], cutoff: datetime
) -> DailyClose | None:
    """Return the last close known before a timestamp; a close occurs at 4 PM ET."""
    if cutoff.tzinfo is None:
        cutoff = cutoff.replace(tzinfo=EASTERN)
    eastern_cutoff = cutoff.astimezone(EASTERN)
    eligible = []
    for item in closes:
        close_time = datetime.combine(item.trading_date, time(16, 0), tzinfo=EASTERN)
        if close_time < eastern_cutoff:
            eligible.append(item)
    return max(eligible, default=None)


class CsvClosesReader:
    """Read a team-controlled LSEG export kept outside the repository."""

    _TICKER_HEADERS = ("ticker", "ric", "instrument", "universe")
    _DATE_HEADERS = ("date", "tr.priceclose.date", "trading date")
    _CLOSE_HEADERS = (
        "close",
        "price close",
        "tr.priceclose",
        "close price",
        "trdprc_1",
    )

    def __init__(self, path: Path):
        self.path = path.expanduser().resolve()

    @staticmethod
    def _column(fieldnames: Sequence[str], choices: Sequence[str]) -> str:
        lookup = {name.strip().lower(): name for name in fieldnames}
        for choice in choices:
            if choice in lookup:
                return lookup[choice]
        raise CloseReaderError(
            f"Close export is missing one required column. Expected one of: {', '.join(choices)}"
        )

    def daily_closes(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[DailyClose]:
        wanted = _normalize_ticker(ticker)
        if not self.path.is_file():
            raise CloseReaderError("The configured close export does not exist.")
        with self.path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise CloseReaderError("The configured close export has no header row.")
            ticker_column = self._column(reader.fieldnames, self._TICKER_HEADERS)
            date_column = self._column(reader.fieldnames, self._DATE_HEADERS)
            close_column = self._column(reader.fieldnames, self._CLOSE_HEADERS)
            results = []
            for row in reader:
                row_ticker = str(row.get(ticker_column, "")).strip().upper()
                if row_ticker != wanted:
                    continue
                try:
                    row_date = date.fromisoformat(str(row.get(date_column, ""))[:10])
                except ValueError:
                    continue
                if start_date <= row_date <= end_date:
                    results.append(
                        DailyClose(
                            trading_date=row_date,
                            close=_decimal(row.get(close_column, "")),
                            ticker=wanted,
                            source="LSEG close export",
                        )
                    )
        return sorted({item.trading_date: item for item in results}.values())


class LsegClosesReader:
    """Read LSEG Workspace daily closes with a temporary, unlogged config."""

    def __init__(self, app_key: str):
        if not app_key.strip():
            raise CloseReaderError("LSEG_APP_KEY is empty.")
        self._app_key = app_key.strip()

    def daily_closes(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[DailyClose]:
        wanted = _normalize_ticker(ticker)
        try:
            import lseg.data as ld  # type: ignore[import-not-found]
        except ImportError as exc:
            raise CloseReaderError(
                "LSEG_APP_KEY is set, but lseg-data is not installed. Run `uv add lseg-data`."
            ) from exc

        config = {
            "sessions": {
                "default": "desktop.workspace",
                "desktop": {"workspace": {"app-key": self._app_key}},
            }
        }
        with tempfile.TemporaryDirectory(prefix="spinoff-lseg-") as temp_dir:
            config_path = Path(temp_dir) / "lseg-data.config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            session = ld.open_session(
                name="desktop.workspace", config_name=str(config_path)
            )
            try:
                frame = ld.get_data(
                    wanted,
                    ["TR.PriceClose.date", "TR.PriceClose"],
                    {
                        "SDate": start_date.isoformat(),
                        "EDate": end_date.isoformat(),
                        "Frq": "D",
                    },
                )
            finally:
                close_method = getattr(session, "close", None)
                if callable(close_method):
                    close_method()

        if frame is None or getattr(frame, "empty", True):
            return []
        columns = {str(item).strip().lower(): item for item in frame.columns}
        date_column = next(
            (value for key, value in columns.items() if "date" in key), None
        )
        close_column = next(
            (value for key, value in columns.items() if "close" in key), None
        )
        if date_column is None or close_column is None:
            raise CloseReaderError("LSEG did not return date and close columns.")
        results = []
        for _, row in frame.iterrows():
            try:
                row_date = date.fromisoformat(str(row[date_column])[:10])
                close = _decimal(row[close_column])
            except (ValueError, CloseReaderError):
                continue
            results.append(
                DailyClose(row_date, close, wanted, "LSEG Workspace TR.PriceClose")
            )
        return sorted({item.trading_date: item for item in results}.values())


class FinancialDatasetsClosesReader:
    """Read historical end-of-day closes from financialdatasets.ai."""

    def __init__(
        self,
        api_key: str | None,
        session: requests.Session | None = None,
    ):
        if not isinstance(api_key, str) or not api_key.strip():
            raise CloseReaderError(
                "FINANCIAL_DATASETS_API_KEY is missing or empty in .env."
            )
        self._api_key = api_key.strip()
        self.session = session or requests.Session()
        self.last_payloads: list[dict[str, object]] = []

    @staticmethod
    def _next_page_url(value: object) -> str | None:
        if value in (None, ""):
            return None
        url = str(value).strip()
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != "api.financialdatasets.ai":
            raise CloseReaderError(
                "Financial Datasets returned an invalid pagination URL."
            )
        return url

    def daily_closes(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[DailyClose]:
        wanted = _normalize_ticker(ticker)
        self.last_payloads = []
        url: str | None = FINANCIAL_DATASETS_PRICES_URL
        params: dict[str, str] | None = {
            "ticker": wanted,
            "interval": "day",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }
        results: list[DailyClose] = []

        while url is not None:
            response = self.session.get(
                url,
                params=params,
                headers={"X-API-KEY": self._api_key},
                timeout=HTTP_TIMEOUT_SECONDS,
            )
            if response.status_code == 404:
                return []
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise CloseReaderError(
                    "Financial Datasets returned an invalid price response."
                )
            self.last_payloads.append(dict(payload))
            rows = payload.get("prices", [])
            if not isinstance(rows, list):
                raise CloseReaderError(
                    "Financial Datasets returned an invalid prices list."
                )
            for row in rows:
                if not isinstance(row, Mapping):
                    continue
                row_ticker = str(row.get("ticker", wanted)).strip().upper()
                if row_ticker and row_ticker != wanted:
                    continue
                try:
                    row_date = date.fromisoformat(str(row.get("time", ""))[:10])
                    close = _decimal(row.get("close", ""))
                except (ValueError, CloseReaderError):
                    continue
                if start_date <= row_date <= end_date:
                    results.append(
                        DailyClose(
                            trading_date=row_date,
                            close=close,
                            ticker=wanted,
                            source="Financial Datasets historical close",
                        )
                    )
            url = self._next_page_url(payload.get("next_page_url"))
            params = None

        return sorted({item.trading_date: item for item in results}.values())


class NasdaqClosesReader:
    """Read unadjusted historical closes from Nasdaq's public market-data page."""

    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()

    def daily_closes(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[DailyClose]:
        wanted = _normalize_ticker(ticker)
        response = self.session.get(
            NASDAQ_HISTORY_URL.format(ticker=wanted.lower()),
            params={
                "assetclass": "stocks",
                "fromdate": start_date.strftime("%m/%d/%Y"),
                "todate": end_date.strftime("%m/%d/%Y"),
                "limit": "5000",
            },
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; Three-Musketeers-Lab06/1.0)",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://www.nasdaq.com",
                "Referer": f"https://www.nasdaq.com/market-activity/stocks/{wanted.lower()}/historical",
            },
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        rows = (((payload or {}).get("data") or {}).get("tradesTable") or {}).get(
            "rows"
        ) or []
        results = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            raw_date = str(row.get("date", "")).strip()
            parsed_date = None
            for format_string in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
                try:
                    parsed_date = datetime.strptime(raw_date, format_string).date()
                    break
                except ValueError:
                    continue
            if parsed_date is None or not start_date <= parsed_date <= end_date:
                continue
            try:
                close = _decimal(row.get("close", row.get("close/last", "")))
            except CloseReaderError:
                continue
            results.append(
                DailyClose(parsed_date, close, wanted, "Nasdaq historical close")
            )
        return sorted({item.trading_date: item for item in results}.values())


class FallbackClosesReader:
    """Try configured sources in order and return no data only after all fail."""

    def __init__(self, readers: Sequence[ClosesReader]):
        self.readers = list(readers)
        self.errors: dict[str, str] = {}

    def daily_closes(
        self, ticker: str, start_date: date, end_date: date
    ) -> list[DailyClose]:
        self.errors = {}
        for reader in self.readers:
            name = type(reader).__name__
            try:
                values = reader.daily_closes(ticker, start_date, end_date)
            except Exception as exc:
                self.errors[name] = str(exc)
                continue
            if values:
                return values
            self.errors[name] = "not available"
        return []


def build_closes_reader(workspace_dir: Path) -> FallbackClosesReader:
    """Build source precedence without printing any environment value."""
    values = dotenv_values(workspace_dir / ".env")
    readers: list[ClosesReader] = [
        FinancialDatasetsClosesReader(values.get("FINANCIAL_DATASETS_API_KEY"))
    ]
    export_path = values.get("LSEG_CLOSES_FILE") or values.get("CLOSES_FILE")
    if isinstance(export_path, str) and export_path.strip():
        readers.append(CsvClosesReader(Path(export_path.strip())))
    app_key = values.get("LSEG_APP_KEY")
    if isinstance(app_key, str) and app_key.strip():
        readers.append(LsegClosesReader(app_key))
    readers.append(NasdaqClosesReader())
    return FallbackClosesReader(readers)


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Print contract-compliant daily closes.")
    parser.add_argument("ticker")
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--end", required=True, type=date.fromisoformat)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    reader = build_closes_reader(args.workspace)
    closes = reader.daily_closes(args.ticker, args.start, args.end)
    print(json.dumps([item.to_dict() for item in closes], indent=2))
    return 0 if closes else 1


if __name__ == "__main__":
    raise SystemExit(_main())
