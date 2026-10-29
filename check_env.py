"""Check that the private course configuration can be read safely.

This script prints only the first four characters of the API key. It never
prints the complete key.
"""

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
    api_key = values.get("API_KEY") or values.get("OPENAI_API_KEY")
    user_agent = values.get("SEC_USER_AGENT")

    if not api_key or len(api_key) < 4:
        raise SystemExit("ERROR: API_KEY or OPENAI_API_KEY is missing from .env.")
    if not user_agent:
        raise SystemExit("ERROR: SEC_USER_AGENT is missing from .env.")

    print(f"API_KEY={api_key[:4]}...")
    print(f"SEC_USER_AGENT={user_agent}")


if __name__ == "__main__":
    main()
