"""Prune the Actions caches no workflow uses any more (#473, .github/workflows/cache-prune.yml). The prefixes are
derived from the workflows (docs/adr/0011): each actions/cache key's and restore-key's text before its first `${{`, plus
the caches setup-node (`cache:`) and setup-uv (unless `enable-cache: false`) save under their own names. Reads
`gh cache list --json id,key,sizeInBytes` on stdin, prints the stale caches' ids and logs each one to stderr."""

import json
import re
import sys
from pathlib import Path

import yaml

WORKFLOWS = Path(__file__).resolve().parent.parent / ".github" / "workflows"
REFERENCE = re.compile(r"\$\{\{ *(steps|needs)\.[\w-]+\.outputs\.[\w-]+ *\}\}")  # another step's key, derived there


def prefixes(workflows: Path) -> set[str]:
    found = set()
    for f in workflows.glob("*.yml"):
        for job in yaml.safe_load(f.read_text())["jobs"].values():
            for step in job.get("steps", []):
                uses, with_ = step.get("uses", ""), step.get("with") or {}
                if uses.startswith("actions/cache"):
                    for key in [with_["key"], *str(with_.get("restore-keys", "")).splitlines()]:
                        head = key.split("${{")[0]
                        assert head or REFERENCE.fullmatch(key), f"{f.name}: {key} has no prefix to keep its caches by"
                        found |= {head} - {""}
                elif uses.startswith("actions/setup-node") and with_.get("cache"):
                    found.add("node-cache-")
                elif uses.startswith("astral-sh/setup-uv") and with_.get("enable-cache") is not False:
                    found.add("setup-uv-")
    return found


def stale(caches: list[dict], keep: set[str]) -> list[dict]:
    return [c for c in caches if not c["key"].startswith(tuple(keep))]


if __name__ == "__main__":
    gone = stale(json.load(sys.stdin), prefixes(WORKFLOWS))
    for c in gone:
        print(f"deleting {c['key']} ({c['sizeInBytes'] / 1e6:.1f} MB)", file=sys.stderr)
        print(c["id"])
    print(f"{len(gone)} caches, {sum(c['sizeInBytes'] for c in gone) / 1e9:.2f} GB", file=sys.stderr)
