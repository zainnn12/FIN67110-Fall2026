"""Check that the private course configuration is present without printing it."""

from pathlib import Path


def load_env(path: Path) -> dict[str, str]:
    """Load simple KEY=VALUE entries without an external package."""
    values: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[name.strip()] = value

    return values


def main() -> None:
    env_path = Path(__file__).with_name(".env")
    if not env_path.is_file():
        raise SystemExit("ERROR: .env was not found in the course folder.")

    values = load_env(env_path)
    api_key = values.get("API_KEY")
    financial_datasets_api_key = values.get("FINANCIAL_DATASETS_API_KEY")
    user_agent = values.get("SEC_USER_AGENT")

    if not api_key:
        raise SystemExit("ERROR: API_KEY is missing from .env.")
    if not financial_datasets_api_key:
        raise SystemExit("ERROR: FINANCIAL_DATASETS_API_KEY is missing from .env.")
    if not user_agent:
        raise SystemExit("ERROR: SEC_USER_AGENT is missing from .env.")

    print("Required environment variables are present.")


if __name__ == "__main__":
    main()
