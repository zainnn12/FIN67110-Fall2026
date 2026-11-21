import json
from datetime import datetime
from pathlib import Path

from wrds_crsp_reaction import run, select_close_pair

class Frame:
    def __init__(self, rows): self.rows=rows
    def iterrows(self): return iter(enumerate(self.rows))

class Row(dict):
    pass


def test_close_pair_uses_accepted_timestamp_and_regular_session_close():
    from datetime import date
    frame = Frame([Row(date=date.fromisoformat(d),prc=p) for d,p in [("2026-11-19",10),("2026-11-20",11),("2026-11-23",12)]])
    accepted = datetime.fromisoformat("2026-11-20T08:22:14-05:00")
    assert select_close_pair(frame, accepted) == (10.0, 11.0)
    after_close = datetime.fromisoformat("2026-11-20T16:22:14-05:00")
    assert select_close_pair(frame, after_close) == (11.0, 12.0)
    flagged=Frame([Row(date=date.fromisoformat(d),prc=p) for d,p in [("2026-11-19",10),("2026-11-20",-11),("2026-11-23",12)]])
    assert select_close_pair(flagged, accepted) == (10.0, 12.0)


def test_wrds_missing_login_is_explicit_and_never_substitutes(tmp_path, monkeypatch):
    monkeypatch.delenv("WRDS_USERNAME", raising=False)
    monkeypatch.delenv("WRDS_PASSWORD", raising=False)
    out = tmp_path / "result.json"
    result = run(tmp_path / "events.csv", out)
    assert result["status"] == "PENDING WRDS LOGIN — no authorized credentials available."
    assert result["provider"] == "WRDS / CRSP"
    assert result["substitution"] == "none"
    assert json.loads(out.read_text()) == result
