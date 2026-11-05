#!/usr/bin/env python
"""Command-line entry point for the fixed equity-research team Flow."""

from __future__ import annotations

import argparse
import json
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Sequence

from dotenv import dotenv_values

# Keep CrewAI's local storage inside this generated project. This must be set
# before importing crewai through team_flow.
_PROJECT_STORAGE = Path(__file__).resolve().parents[2] / ".crewai"
os.environ.setdefault("CREWAI_STORAGE_DIR", str(_PROJECT_STORAGE.resolve()))

from equity_research_team.team_flow import (
    WORKSPACE_DIR,
    EquityResearchTeamFlow,
    build_desk,
    new_verification_output_dir,
    role_instructions,
)
from equity_research_team.verifier import verify_run

if str(WORKSPACE_DIR) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_DIR))

from equity_research_data import (  # noqa: E402
    SecClient,
    decimal_argument,
    normalize_peer_arguments,
    read_sec_user_agent,
)
from research_roles import DEFAULT_OPENAI_MODEL, OpenAIRoleClient  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the fixed CrewAI equity-research team and mandatory Verifier."
    )
    parser.add_argument("ticker", nargs="?", help="Primary ticker symbol")
    parser.add_argument(
        "--peers",
        nargs="*",
        default=[],
        metavar="TICKER",
        help="Optional peer tickers separated by commas or spaces",
    )
    parser.add_argument("--price", type=decimal_argument, help="Optional share price")
    parser.add_argument(
        "--verify-only",
        type=Path,
        metavar="SAVED_RUN",
        help="Run only the mandatory Verifier on a saved run directory or report file",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_OPENAI_MODEL,
        help=f"OpenAI model for all role calls (default: {DEFAULT_OPENAI_MODEL})",
    )
    return parser


def _api_key() -> str:
    values = dotenv_values(WORKSPACE_DIR / ".env")
    value = values.get("API_KEY")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"API_KEY is missing from {WORKSPACE_DIR / '.env'}.")
    return value.strip()


def _saved_run_paths(path: Path) -> tuple[Path, Path]:
    resolved = path.expanduser().resolve()
    if resolved.is_file():
        return resolved.parent, resolved
    report = resolved / "equity_research_report.md"
    if not report.is_file():
        raise FileNotFoundError(f"No equity_research_report.md exists in {resolved}.")
    return resolved, report


def run(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    role_client = OpenAIRoleClient(api_key=_api_key(), model=args.model)

    if args.verify_only is not None:
        run_dir, report_path = _saved_run_paths(args.verify_only)
        output_dir = new_verification_output_dir(run_dir)
        print("Node: Verifier")
        verified_path = verify_run(
            run_dir=run_dir,
            report_path=report_path,
            output_dir=output_dir,
            semantic_client=role_client,
            verifier_instructions=role_instructions("Verifier"),
        )
        print(f"Verified report: {verified_path}")
        return 0

    if not args.ticker:
        raise ValueError("ticker is required unless --verify-only is used.")
    peers = normalize_peer_arguments(args.peers)
    sec_client = SecClient(read_sec_user_agent(WORKSPACE_DIR))
    desk = build_desk(
        ticker=args.ticker,
        peers=peers,
        price=args.price,
        client=sec_client,
    )
    flow = EquityResearchTeamFlow(desk=desk, role_client=role_client)
    flow.kickoff(
        inputs={
            "ticker": args.ticker.upper(),
            "peers": peers,
            "price": str(args.price) if args.price is not None else "",
            "model": args.model,
        }
    )
    return 0


def kickoff() -> None:
    try:
        exit_code = run()
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    if exit_code:
        raise SystemExit(exit_code)


def plot() -> None:
    path = EquityResearchTeamFlow().plot("equity_research_team_flow.html", show=False)
    print(path)


def run_with_trigger() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Provide one JSON object with ticker, peers, price, and model.")
    payload = json.loads(sys.argv[1])
    argv = [str(payload["ticker"])]
    peers = payload.get("peers", [])
    if peers:
        argv.extend(("--peers", ",".join(str(item) for item in peers)))
    if payload.get("price") is not None:
        try:
            Decimal(str(payload["price"]))
        except InvalidOperation as exc:
            raise SystemExit("Trigger price must be a decimal number.") from exc
        argv.extend(("--price", str(payload["price"])))
    if payload.get("model"):
        argv.extend(("--model", str(payload["model"])))
    raise SystemExit(run(argv))


if __name__ == "__main__":
    kickoff()
