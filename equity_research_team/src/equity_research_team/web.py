"""Loopback-only web page for the fixed equity-research team."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

from equity_research_team.team_flow import PROJECT_DIR, WORKSPACE_DIR


STATIC_DIR = Path(__file__).resolve().parent / "static"
TICKER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.-]{0,9}$")
PACKAGE_SOURCE_DIR = PROJECT_DIR / "src"
AMD_FALLBACK_DIR = (
    WORKSPACE_DIR
    / "runs"
    / "ADVANCED_MICRO_DEVICES_INC_2026-11-08_16-02-23-519971"
)


@dataclass(frozen=True)
class RunInput:
    ticker: str
    peers: str = ""
    price: str = ""

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RunInput":
        ticker = str(payload.get("ticker", "")).strip().upper()
        if not TICKER_RE.fullmatch(ticker):
            raise ValueError("Use a valid U.S. ticker with at most 10 characters.")

        peer_tokens = [
            item
            for item in re.split(r"[\s,]+", str(payload.get("peers", "")).strip())
            if item
        ]
        if len(peer_tokens) > 12:
            raise ValueError("Use at most 12 peers.")
        for token in peer_tokens:
            if not TICKER_RE.fullmatch(token):
                raise ValueError(f"Invalid peer ticker: {token}")
        peers = ",".join(token.upper() for token in peer_tokens)

        price_text = str(payload.get("price", "")).strip()
        if price_text:
            try:
                price = Decimal(price_text)
            except InvalidOperation as exc:
                raise ValueError("Price must be a number.") from exc
            if not price.is_finite() or price <= 0:
                raise ValueError("Price must be greater than 0.")
            price_text = str(price)
        return cls(ticker=ticker, peers=peers, price=price_text)


@dataclass
class RunRecord:
    run_id: str
    status: str = "queued"
    events: list[dict[str, Any]] = field(default_factory=list)
    report_path: str = ""
    report: str = ""
    run_dir: str = ""


_runs: dict[str, RunRecord] = {}
_lock = threading.Lock()


def build_command(run_input: RunInput) -> list[str]:
    command = [
        sys.executable,
        "-u",
        "-m",
        "equity_research_team.main",
        run_input.ticker,
    ]
    if run_input.peers:
        command.extend(("--peers", run_input.peers))
    if run_input.price:
        command.extend(("--price", run_input.price))
    return command


def build_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Make the src-layout package importable in the child process."""
    environment = dict(os.environ if base_env is None else base_env)
    import_paths = [str(PACKAGE_SOURCE_DIR), str(WORKSPACE_DIR)]
    existing = environment.get("PYTHONPATH", "")
    if existing:
        import_paths.extend(existing.split(os.pathsep))
    environment["PYTHONPATH"] = os.pathsep.join(
        dict.fromkeys(path for path in import_paths if path)
    )
    return environment


def fallback_report_for(run_input: RunInput) -> Path | None:
    """Return the saved AMD fallback only for the requested AMD inputs."""
    if run_input.ticker != "AMD" or run_input.peers != "NVDA,INTC,AVGO":
        return None
    if not run_input.price or Decimal(run_input.price) != Decimal("466.84"):
        return None
    report = AMD_FALLBACK_DIR / "fallback_report.md"
    return report if report.is_file() else None


def is_credit_balance_exhausted(output: str) -> bool:
    lowered = output.lower()
    return "429" in lowered and "credit_balance_exhausted" in lowered


def _save_ui_evidence(record: RunRecord, run_input: RunInput) -> None:
    if not record.run_dir:
        return
    run_dir = Path(record.run_dir)
    events = list(record.events)
    payload = {
        "source": "local UI subprocess event stream",
        "inputs": {
            "ticker": run_input.ticker,
            "peers": run_input.peers.split(",") if run_input.peers else [],
            "price": run_input.price or None,
        },
        "status": record.status,
        "node_order": [
            item["name"] for item in events if item.get("kind") == "node"
        ],
        "report_path": record.report_path or None,
        "fallback_label": next(
            (item.get("label") for item in events if item.get("kind") == "fallback"),
            None,
        ),
        "events": events,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "ui_evidence.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _emit(record: RunRecord, kind: str, **payload: Any) -> None:
    with _lock:
        record.events.append({"kind": kind, **payload})


def _run_team(run_id: str, run_input: RunInput) -> None:
    record = _runs[run_id]
    record.status = "running"
    _emit(record, "status", status="running")
    verified_path: Path | None = None
    process_output: list[str] = []
    try:
        process = subprocess.Popen(
            build_command(run_input),
            cwd=PROJECT_DIR,
            env=build_environment(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.rstrip("\n")
            process_output.append(line)
            if line.startswith("Run folder: "):
                record.run_dir = str(Path(line.removeprefix("Run folder: ").strip()).resolve())
            if line.startswith("Node: "):
                _emit(record, "node", name=line.removeprefix("Node: "))
            elif line.startswith("Verified report: "):
                candidate = Path(line.removeprefix("Verified report: ").strip())
                if not candidate.is_absolute():
                    candidate = PROJECT_DIR / candidate
                verified_path = candidate.resolve()
                record.report_path = str(verified_path)
            _emit(record, "log", line=line)
        return_code = process.wait()
        if return_code != 0:
            combined_output = "\n".join(process_output)
            fallback_path = fallback_report_for(run_input)
            if is_credit_balance_exhausted(combined_output) and fallback_path:
                record.report_path = str(fallback_path.resolve())
                record.report = fallback_path.read_text(encoding="utf-8")
                record.status = "fallback"
                _emit(
                    record,
                    "fallback",
                    status="fallback",
                    label="Fallback — not a live agent-team run",
                    report_path=record.report_path,
                    report=record.report,
                )
                _save_ui_evidence(record, run_input)
                return
            raise RuntimeError(f"The agent team stopped with exit code {return_code}.")
        if verified_path is None or not verified_path.is_file():
            raise RuntimeError("The run ended without a saved verified report.")
        record.report = verified_path.read_text(encoding="utf-8")
        record.status = "complete"
        _emit(
            record,
            "complete",
            status="complete",
            report_path=record.report_path,
            report=record.report,
        )
        _save_ui_evidence(record, run_input)
    except Exception as exc:  # The exact process output is already in the event log.
        record.status = "failed"
        _emit(record, "error", status="failed", message=str(exc))
        _save_ui_evidence(record, run_input)


class PageHandler(BaseHTTPRequestHandler):
    server_version = "EquityResearchPage/1.0"

    def _send_bytes(
        self,
        body: bytes,
        *,
        status: HTTPStatus = HTTPStatus.OK,
        content_type: str = "application/json; charset=utf-8",
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(
        self, payload: Mapping[str, Any], status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        self._send_bytes(
            json.dumps(payload, ensure_ascii=False).encode("utf-8"), status=status
        )

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        path = urlparse(self.path).path
        if path == "/":
            self._send_bytes(
                (STATIC_DIR / "index.html").read_bytes(),
                content_type="text/html; charset=utf-8",
            )
            return
        if path == "/health":
            self._send_json({"status": "ok"})
            return
        match = re.fullmatch(r"/api/runs/([a-f0-9]{32})/events", path)
        if match:
            self._stream_events(match.group(1))
            return
        self._send_json({"detail": "Not found."}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        if urlparse(self.path).path != "/api/runs":
            self._send_json({"detail": "Not found."}, HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 16_384:
                raise ValueError("The request body has an invalid size.")
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, Mapping):
                raise ValueError("The request body must be a JSON object.")
            run_input = RunInput.from_payload(payload)
        except (ValueError, json.JSONDecodeError) as exc:
            self._send_json({"detail": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        run_id = uuid.uuid4().hex
        record = RunRecord(run_id=run_id)
        with _lock:
            _runs[run_id] = record
        threading.Thread(
            target=_run_team,
            args=(run_id, run_input),
            name=f"equity-run-{run_id[:8]}",
            daemon=True,
        ).start()
        self._send_json(
            {"run_id": run_id, "status": "queued"}, HTTPStatus.ACCEPTED
        )

    def _stream_events(self, run_id: str) -> None:
        with _lock:
            exists = run_id in _runs
        if not exists:
            self._send_json({"detail": "Run not found."}, HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        cursor = 0
        try:
            while True:
                with _lock:
                    record = _runs[run_id]
                    pending = list(record.events[cursor:])
                    status = record.status
                for event in pending:
                    cursor += 1
                    data = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"data: {data}\n\n".encode("utf-8"))
                if not pending:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                if status in {"complete", "failed"} and cursor >= len(record.events):
                    return
                time.sleep(0.35)
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args: Any) -> None:
        print(f"Page: {self.address_string()} - {format % args}")


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), PageHandler)


def main() -> None:
    port = int(os.environ.get("EQUITY_RESEARCH_PAGE_PORT", "8000"))
    server = make_server(port=port)
    actual_port = server.server_address[1]
    print(f"Agent team page: http://127.0.0.1:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
