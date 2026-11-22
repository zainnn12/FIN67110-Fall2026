import csv
import json
import statistics
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from wrds_crsp_reaction import (
    load_wrds_username,
    open_wrds_connection,
    run,
    select_close_pair,
    smoke_test,
)


ROOT = Path(__file__).resolve().parents[1]


class Frame:
    def __init__(self, rows):
        self.rows = rows

    def iterrows(self):
        return iter(enumerate(self.rows))


class Row(dict):
    pass


class Connection:
    def __init__(self, *, libraries=None, frame=None):
        self.libraries = libraries or []
        self.frame = frame
        self.queries = []

    def list_libraries(self):
        return self.libraries

    def raw_sql(self, sql, params):
        self.queries.append((sql, params))
        if "MIN(dlycaldt)" in sql:
            dates = [row["date"] for row in self.frame.rows]
            return Frame(
                [
                    Row(
                        first_date=min(dates),
                        last_date=max(dates),
                        row_count=len(dates),
                    )
                ]
            )
        return self.frame


def test_close_pair_uses_accepted_timestamp_and_regular_session_close():
    frame = Frame(
        [
            Row(date=date.fromisoformat(day), prc=price)
            for day, price in [
                ("2026-11-19", 10),
                ("2026-11-20", 11),
                ("2026-11-23", 12),
            ]
        ]
    )
    accepted = datetime.fromisoformat("2026-11-20T08:22:14-05:00")
    assert select_close_pair(frame, accepted) == (10.0, 11.0)
    after_close = datetime.fromisoformat("2026-11-20T16:22:14-05:00")
    assert select_close_pair(frame, after_close) == (11.0, 12.0)
    flagged = Frame(
        [
            Row(date=date.fromisoformat(day), prc=price)
            for day, price in [
                ("2026-11-19", 10),
                ("2026-11-20", -11),
                ("2026-11-23", 12),
            ]
        ]
    )
    assert select_close_pair(flagged, accepted) == (10.0, 12.0)


def test_username_loads_from_selected_dotenv_without_password(tmp_path, monkeypatch):
    monkeypatch.delenv("WRDS_USERNAME", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text("WRDS_USERNAME=test-user\n", encoding="utf-8")
    assert load_wrds_username(env_path) == "test-user"


def test_missing_username_fails_before_connection(tmp_path, monkeypatch):
    monkeypatch.delenv("WRDS_USERNAME", raising=False)
    with pytest.raises(RuntimeError, match="WRDS_USERNAME is missing or blank"):
        open_wrds_connection(env_path=tmp_path / "missing.env")


def test_smoke_test_reports_crsp_without_full_library_list():
    result = smoke_test(connection=Connection(libraries=["comp", "crsp"]))
    assert result == {
        "status": "connected",
        "provider": "WRDS / CRSP",
        "crsp_available": True,
    }


def test_smoke_test_labels_subscription_limitation():
    result = smoke_test(connection=Connection(libraries=["comp"]))
    assert result["crsp_available"] is False
    assert "subscription" in result["limitation"]
    assert "not a coding failure" in result["limitation"]


def test_run_saves_source_calculations_and_methodology(tmp_path):
    events = tmp_path / "events.csv"
    with events.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "ticker",
                "accession",
                "accepted_at",
                "permno",
                "start_date",
                "end_date",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "ticker": "COST",
                "accession": "test-accession",
                "accepted_at": "2026-11-20T16:22:14-05:00",
                "permno": "12345",
                "start_date": "2026-11-19",
                "end_date": "2026-11-23",
            }
        )
    frame = Frame(
        [
            Row(date=date(2026, 11, 19), prc=10, shrout=100, permno=12345),
            Row(date=date(2026, 11, 20), prc=11, shrout=100, permno=12345),
            Row(date=date(2026, 11, 23), prc=12, shrout=100, permno=12345),
        ]
    )
    output = tmp_path / "result.json"
    source = tmp_path / "source.csv"
    methodology = tmp_path / "methodology.md"

    result = run(
        events,
        output,
        source_path=source,
        methodology_path=methodology,
        connection=Connection(libraries=["crsp"], frame=frame),
    )

    assert result["status"] == "complete"
    assert result["rows"][0]["last_close_before"] == 11.0
    assert result["rows"][0]["first_close_after"] == 12.0
    assert (
        result["rows"][0]["reaction_percent"]
        == "9.090909090909090909090909100"
    )
    assert json.loads(output.read_text(encoding="utf-8")) == result
    assert len(list(csv.DictReader(source.open(encoding="utf-8")))) == 3
    method_text = methodology.read_text(encoding="utf-8")
    assert "Independent arithmetic check" in method_text
    assert "Reproducible command" in method_text


def test_run_resolves_blank_permno_with_current_ciz_schema(tmp_path):
    events = tmp_path / "events.csv"
    events.write_text(
        "ticker,accession,accepted_at,permno,start_date,end_date\n"
        "COST,test-accession,2026-11-20T16:22:14-05:00,,"
        "2026-11-19,2026-11-23\n",
        encoding="utf-8",
    )
    prices = Frame(
        [
            Row(date=date(2026, 11, 20), prc=11, shrout=100, permno=12345),
            Row(date=date(2026, 11, 23), prc=12, shrout=100, permno=12345),
        ]
    )
    connection = Connection(
        libraries=["crsp"],
        frame=prices,
    )

    result = run(events, tmp_path / "result.json", connection=connection)

    assert result["rows"][0]["permno"] == 12345
    price_sql, price_params = connection.queries[1]
    assert "crsp.dsf_v2" in price_sql
    assert "dlyclose AS prc" in price_sql
    assert price_params == {
        "ticker": "COST",
        "start": "2026-11-19",
        "end": "2026-11-23",
    }


def test_saved_eight_event_evidence_recalculates_from_source_csv():
    source_path = ROOT / "runs/wrds/costco_crsp_daily.csv"
    result_path = ROOT / "runs/wrds/crsp_reaction.json"
    methodology_path = ROOT / "runs/wrds/crsp_reaction_methodology.md"
    with source_path.open(newline="", encoding="utf-8") as handle:
        source_rows = list(csv.DictReader(handle))
    result = json.loads(result_path.read_text(encoding="utf-8"))

    assert result["status"] == "complete"
    assert result["event_count"] == 8
    assert result["source_table"] == "crsp.dsf_v2"
    assert result["validation"]["status"] == "PASS"
    assert result["validation"]["saved_source_row_count"] == len(source_rows)
    assert len(source_rows) == 54
    assert {row["dlyprcflg"] for row in source_rows} == {"TR"}

    eastern = ZoneInfo("America/New_York")
    recalculated = []
    for saved in result["rows"]:
        accepted = datetime.fromisoformat(saved["accepted_at"])
        matching = [
            row for row in source_rows if row["accession"] == saved["accession"]
        ]
        candidates = [
            (
                datetime.combine(
                    date.fromisoformat(row["date"]),
                    time(16, 0),
                    tzinfo=eastern,
                ),
                Decimal(row["prc"]),
            )
            for row in matching
            if Decimal(row["prc"]) > 0
        ]
        prior = [item for item in candidates if item[0] < accepted][-1]
        first = [item for item in candidates if item[0] > accepted][0]
        expected = (first[1] / prior[1] - Decimal(1)) * Decimal(100)
        assert saved["last_close_before_date"] == prior[0].date().isoformat()
        assert Decimal(str(saved["last_close_before"])) == prior[1]
        assert saved["first_close_after_date"] == first[0].date().isoformat()
        assert Decimal(str(saved["first_close_after"])) == first[1]
        assert Decimal(saved["reaction_percent"]) == expected
        recalculated.append(expected)

    assert Decimal(result["summary"]["mean_reaction_percent"]) == sum(
        recalculated
    ) / Decimal(8)
    assert Decimal(
        result["summary"]["median_reaction_percent"]
    ) == statistics.median(recalculated)
    methodology = methodology_path.read_text(encoding="utf-8")
    assert "crsp.dsf_v2" in methodology
    assert "Reproducible command" in methodology
