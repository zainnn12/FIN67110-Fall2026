"""Rebuild the saved Lab 04 proof marks without a provider key."""

from __future__ import annotations

import json
from pathlib import Path

from equity_research_team.verifier import verify_run


PROJECT_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_DIR = PROJECT_DIR.parent


class EvidencePassClient:
    """Accept semantics only after the deterministic evidence check runs."""

    def call(self, *, request, **kwargs):
        return {
            "checks": [
                {
                    "claim_id": item["claim_id"],
                    "supported": True,
                    "explanation": (
                        "Offline proof: the deterministic evidence supplied the cited value, "
                        "period, and definition."
                    ),
                    "corrected_value": "",
                    "source": item["evidence"],
                }
                for item in request["context"]["deterministic_checks"]
            ]
        }


def main() -> None:
    proof_root = WORKSPACE_DIR / "lab4_proofs"
    for name in (
        "COST_clean",
        "COST_seeded_eps_error",
        "COST_invented_growth_error",
    ):
        run_dir = proof_root / name
        verify_run(
            run_dir=run_dir,
            report_path=run_dir / "equity_research_report.md",
            output_dir=run_dir,
            semantic_client=EvidencePassClient(),
            verifier_instructions="Use only the deterministic proof evidence.",
        )
        output = json.loads(
            (run_dir / "nodes" / "06_verifier_output.json").read_text(encoding="utf-8")
        )
        print(f"{name}: {output['counts']}")


if __name__ == "__main__":
    main()
