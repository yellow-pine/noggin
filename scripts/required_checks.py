"""Does every required check main's ruleset names still name a gate job (one without a matrix) in .github/workflows? A
renamed job strands the old name in the ruleset, and every PR waits on a check that never reports (#450); a matrix job's
checks come and go with its matrix, so a required check names only a gate job (#570). Exits 1 with an Actions error per
stale check. Code job (.github/workflows/checks.yml), which feeds it the ruleset's contexts from the GitHub API.
Usage: gh api repos/OWNER/REPO/rules/branches/main --jq ... | .venv/bin/python scripts/required_checks.py [workflows]"""

import sys
from pathlib import Path

import yaml


def stale(required: list[str], workflows: Path) -> list[str]:
    """The required checks no gate job in the workflows names (a job without a name reports its id)."""
    jobs = {
        job.get("name", id_)
        for f in workflows.glob("*.yml")
        for id_, job in yaml.safe_load(f.read_text())["jobs"].items()
        if "matrix" not in job.get("strategy", {})
    }
    return [check for check in required if check not in jobs]


if __name__ == "__main__":
    workflows = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / ".github/workflows"
    gone = stale(sys.stdin.read().splitlines(), workflows)
    for check in gone:
        print(
            f"::error::Main's ruleset requires {check!r}, which no gate job (one without a matrix) in "
            ".github/workflows names: rename it there too, or require the gate that needs the matrix job."
        )
    sys.exit(1 if gone else 0)
