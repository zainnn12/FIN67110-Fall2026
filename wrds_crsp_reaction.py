#!/usr/bin/env python3
"""Run a reproducible CRSP close-to-close event-reaction analysis."""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import statistics
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv


EASTERN = ZoneInfo("America/New_York")
ROOT = Path(__file__).resolve().parent
ROOT_ENV = ROOT / ".env"
REACTION_FORMULA = "(first_close_after / last_close_before - 1) * 100"
CRSP_SQL = """
SELECT permno, ticker, dlycaldt AS date, dlyclose AS prc, dlyprcflg, shrout
FROM crsp.dsf_v2
WHERE ticker = %(ticker)s
  AND dlycaldt BETWEEN %(start)s AND %(end)s
ORDER BY dlycaldt
""".strip()
AVAILABILITY_SQL = """
SELECT MIN(dlycaldt) AS first_date,
       MAX(dlycaldt) AS last_date,
       COUNT(*) AS row_count
FROM crsp.dsf_v2
WHERE ticker = %(ticker)s
""".strip()


def reaction(last_close: object, first_close: object) -> str | None:
    """Return the unrounded percentage reaction as a decimal string."""
    if last_close in (None, 0) or first_close is None:
        return None
    result = (
        Decimal(str(first_close)) / Decimal(str(last_close)) - Decimal(1)
    ) * Decimal(100)
    return str(result)


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def select_close_observations(
    frame: Any, accepted: datetime
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """Select the last valid close before acceptance and first one after it."""
    candidates: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        trading_date = _as_date(row["date"])
        price = float(row["prc"])
        # A regular close must be a positive, populated CIZ dlyclose observation.
        if price <= 0:
            continue
        candidates.append(
            {
                "timestamp": datetime.combine(
                    trading_date, time(16, 0), tzinfo=EASTERN
                ),
                "date": trading_date.isoformat(),
                "price": price,
            }
        )
    before = [item for item in candidates if item["timestamp"] < accepted]
    after = [item for item in candidates if item["timestamp"] > accepted]
    return (before[-1] if before else None, after[0] if after else None)


def select_close_pair(
    frame: Any, accepted: datetime
) -> tuple[float | None, float | None]:
    """Compatibility wrapper that returns only the two selected prices."""
    before, after = select_close_observations(frame, accepted)
    return (
        before["price"] if before else None,
        after["price"] if after else None,
    )


def load_wrds_username(env_path: Path = ROOT_ENV) -> str:
    """Load WRDS_USERNAME from the worktree-root .env without other values."""
    load_dotenv(dotenv_path=env_path, override=False)
    return os.getenv("WRDS_USERNAME", "").strip()


def open_wrds_connection(
    *, username: str | None = None, env_path: Path = ROOT_ENV
):
    """Connect through the supported WRDS password/Duo or ~/.pgpass process."""
    resolved_username = (
        username if username is not None else load_wrds_username(env_path)
    )
    if not resolved_username:
        raise RuntimeError(
            "WRDS_USERNAME is missing or blank in the worktree-root .env."
        )
    import wrds

    try:
        if sys.stdin.isatty():
            return wrds.Connection(wrds_username=resolved_username)
        # WRDS includes the username in its interactive fallback prompt. Suppress
        # all upstream connection text for non-interactive runs so no credential
        # identifier can enter CI or agent logs.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return wrds.Connection(wrds_username=resolved_username)
    except Exception:
        raise RuntimeError(
            "The WRDS connection did not complete. Run the command in a local "
            "interactive Terminal for the password and Duo prompts, or configure "
            "the standard ~/.pgpass authentication."
        ) from None


def crsp_is_available(connection: Any) -> bool:
    """Check CRSP entitlement without printing the account's full library list."""
    return "crsp" in set(connection.list_libraries())


def smoke_test(
    *,
    connection: Any | None = None,
    username: str | None = None,
    env_path: Path = ROOT_ENV,
) -> dict[str, Any]:
    """Connect and report only whether the CRSP library is available."""
    owns_connection = connection is None
    if connection is None:
        connection = open_wrds_connection(username=username, env_path=env_path)
    try:
        available = crsp_is_available(connection)
        result: dict[str, Any] = {
            "status": "connected",
            "provider": "WRDS / CRSP",
            "crsp_available": available,
        }
        if not available:
            result["limitation"] = (
                "CRSP is unavailable because the institution's WRDS subscription "
                "does not grant this account access; this is not a coding failure."
            )
        return result
    finally:
        if owns_connection:
            connection.close()


def _read_events(events_path: Path) -> list[dict[str, str]]:
    with events_path.open(newline="", encoding="utf-8") as handle:
        events = list(csv.DictReader(handle))
    required = {
        "ticker",
        "accession",
        "accepted_at",
        "permno",
        "start_date",
        "end_date",
    }
    if not events:
        raise ValueError(f"No events are present in {events_path}.")
    missing = required.difference(events[0])
    if missing:
        raise ValueError(
            f"Event input is missing columns: {', '.join(sorted(missing))}."
        )
    return events


def _source_rows(event: dict[str, str], frame: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, item in frame.iterrows():
        rows.append(
            {
                "ticker": event["ticker"],
                "accession": event["accession"],
                "accepted_at": event["accepted_at"],
                "permno": int(event["permno"]),
                "date": _as_date(item["date"]).isoformat(),
                "prc": float(item["prc"]),
                "dlyprcflg": item.get("dlyprcflg"),
                "shrout": (
                    None
                    if item.get("shrout") is None
                    else float(item["shrout"])
                ),
            }
        )
    return rows


def _resolve_permno(event: dict[str, str], frame: Any) -> int:
    configured = event["permno"].strip()
    matches = sorted({int(row["permno"]) for _, row in frame.iterrows()})
    if configured and matches != [int(configured)]:
        raise ValueError(
            f"Configured PERMNO does not match CRSP rows for {event['ticker']}."
        )
    if len(matches) != 1:
        raise ValueError(
            f"Expected one PERMNO for {event['ticker']} in its event window; "
            f"found {len(matches)}."
        )
    return matches[0]


def _write_source_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "ticker",
        "accession",
        "accepted_at",
        "permno",
        "date",
        "prc",
        "dlyprcflg",
        "shrout",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        Decimal(row["reaction_percent"])
        for row in rows
        if row["reaction_percent"] is not None
    ]
    if not values:
        return {
            "complete_reactions": 0,
            "positive_reactions": 0,
            "mean_reaction_percent": None,
            "median_reaction_percent": None,
        }
    return {
        "complete_reactions": len(values),
        "positive_reactions": sum(value > 0 for value in values),
        "mean_reaction_percent": str(sum(values) / Decimal(len(values))),
        "median_reaction_percent": str(statistics.median(values)),
    }


def _validation(
    events: list[dict[str, str]],
    rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    availability: dict[str, Any],
) -> dict[str, Any]:
    accessions = [event["accession"] for event in events]
    permnos = {row["permno"] for row in rows}
    checks = {
        "event_count_is_eight": len(events) == 8,
        "accessions_are_unique": len(accessions) == len(set(accessions)),
        "all_reactions_are_complete": all(
            row["reaction_percent"] is not None for row in rows
        ),
        "single_permno": len(permnos) == 1,
        "source_rows_are_present": bool(source_rows),
        "event_windows_are_within_crsp_data": all(
            availability["first_date"] <= event["start_date"]
            and event["end_date"] <= availability["last_date"]
            for event in events
        ),
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "saved_source_row_count": len(source_rows),
    }


def _write_methodology(
    path: Path,
    *,
    events_path: Path,
    source_path: Path,
    output_path: Path,
    rows: list[dict[str, Any]],
    availability: dict[str, Any],
) -> None:
    first = rows[0]
    text = f"""# Costco eight-event CRSP reaction methodology

## Sources

- Event timestamps and SEC accessions: `{events_path.as_posix()}`.
- Daily source observations: WRDS CRSP CIZ `crsp.dsf_v2`. The selected columns and aliases are saved at `{source_path.as_posix()}`.
- Calculations and results: `{output_path.as_posix()}`.

## Method

The event input contains the latest eight Costco Item 2.02 8-K filings whose reaction windows are inside the account's CRSP CIZ data, which ended on `{availability['last_date']}` at the time of this run. The SEC acceptance timestamps are stored in UTC with their accessions and source links. The eight events run from March 7, 2024 through December 11, 2025.

For each SEC acceptance timestamp, query the current CRSP CIZ daily stock file and retain `dlyclose` as `prc`, `dlyprcflg`, shares outstanding, ticker, and PERMNO. Select the last positive `dlyclose` observation whose 4:00 p.m. America/New_York close is before the timestamp. Then select the first positive `dlyclose` observation whose close is after the timestamp. Calculate the close-to-close reaction as `{REACTION_FORMULA}`. Do not round the stored calculation.

## Independent arithmetic check

For accession `{first['accession']}`, the saved calculation is `({first['first_close_after']} / {first['last_close_before']} - 1) * 100 = {first['reaction_percent']}` percent. This recomputation uses the two saved source prices and agrees with the program result.

## Reproducible command

```bash
UV_CACHE_DIR=/tmp/checkpoint3-uv-cache uv run --project equity_research_team --locked python wrds_crsp_reaction.py --events {events_path.as_posix()} --source-output {source_path.as_posix()} --output {output_path.as_posix()} --methodology-output {path.as_posix()}
```
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(
    events_path: Path,
    output_path: Path,
    *,
    source_path: Path | None = None,
    methodology_path: Path | None = None,
    connection: Any | None = None,
    username: str | None = None,
    env_path: Path = ROOT_ENV,
) -> dict[str, Any]:
    """Query CRSP, save source observations, and calculate event reactions."""
    owns_connection = connection is None
    if connection is None:
        connection = open_wrds_connection(
            username=username, env_path=env_path
        )
    try:
        if not crsp_is_available(connection):
            result = {
                "status": (
                    "CRSP unavailable — institutional subscription limitation."
                ),
                "provider": "WRDS / CRSP",
                "substitution": "none",
                "coding_failure": False,
            }
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(result, indent=2) + "\n", encoding="utf-8"
            )
            return result

        events = _read_events(events_path)
        tickers = {event["ticker"] for event in events}
        if len(tickers) != 1:
            raise ValueError("The event input must contain exactly one ticker.")
        ticker = next(iter(tickers))
        availability_frame = connection.raw_sql(
            AVAILABILITY_SQL, params={"ticker": ticker}
        )
        availability_rows = list(availability_frame.iterrows())
        if len(availability_rows) != 1:
            raise ValueError(f"Could not establish CRSP availability for {ticker}.")
        availability_item = availability_rows[0][1]
        availability = {
            "ticker": ticker,
            "first_date": _as_date(availability_item["first_date"]).isoformat(),
            "last_date": _as_date(availability_item["last_date"]).isoformat(),
            "row_count": int(availability_item["row_count"]),
        }
        rows: list[dict[str, Any]] = []
        saved_source_rows: list[dict[str, Any]] = []
        for event in events:
            accepted = datetime.fromisoformat(event["accepted_at"])
            if accepted.tzinfo is None:
                raise ValueError(
                    "Acceptance timestamp lacks a UTC offset: "
                    f"{event['accession']}."
                )
            frame = connection.raw_sql(
                CRSP_SQL,
                params={
                    "ticker": event["ticker"],
                    "start": event["start_date"],
                    "end": event["end_date"],
                },
            )
            permno = _resolve_permno(event, frame)
            resolved_event = {**event, "permno": str(permno)}
            saved_source_rows.extend(_source_rows(resolved_event, frame))
            prior, first = select_close_observations(frame, accepted)
            prior_price = prior["price"] if prior else None
            first_price = first["price"] if first else None
            rows.append(
                {
                    "ticker": event["ticker"],
                    "permno": permno,
                    "accession": event["accession"],
                    "accepted_at": accepted.isoformat(),
                    "last_close_before_date": (
                        prior["date"] if prior else None
                    ),
                    "last_close_before": prior_price,
                    "first_close_after_date": (
                        first["date"] if first else None
                    ),
                    "first_close_after": first_price,
                    "reaction_formula": REACTION_FORMULA,
                    "reaction_percent": reaction(prior_price, first_price),
                }
            )

        result = {
            "status": "complete",
            "provider": "WRDS / CRSP",
            "event_count": len(events),
            "source_table": "crsp.dsf_v2",
            "crsp_data_availability": availability,
            "summary": _summary(rows),
            "validation": _validation(
                events, rows, saved_source_rows, availability
            ),
            "rows": rows,
        }
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        if source_path is not None:
            _write_source_csv(source_path, saved_source_rows)
        if methodology_path is not None:
            if source_path is None:
                raise ValueError(
                    "A source output is required with a methodology output."
                )
            _write_methodology(
                methodology_path,
                events_path=events_path,
                source_path=source_path,
                output_path=output_path,
                rows=rows,
                availability=availability,
            )
        return result
    finally:
        if owns_connection:
            connection.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Connect and report only whether the CRSP library is available.",
    )
    parser.add_argument("--events", type=Path)
    parser.add_argument("--source-output", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--methodology-output", type=Path)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.smoke_test:
        if any(
            (
                args.events,
                args.source_output,
                args.output,
                args.methodology_output,
            )
        ):
            raise SystemExit(
                "--smoke-test cannot be combined with analysis outputs."
            )
        result = smoke_test()
    else:
        if not all(
            (
                args.events,
                args.source_output,
                args.output,
                args.methodology_output,
            )
        ):
            raise SystemExit(
                "Analysis requires --events, --source-output, --output, and "
                "--methodology-output."
            )
        result = run(
            args.events,
            args.output,
            source_path=args.source_output,
            methodology_path=args.methodology_output,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
