"""Site Deploy (pages.yml): every Release's docs beside main's (ADR 0014). Each release's docs asset, built once by
Release Assets from its tag under /noggin/vX.Y/, is unpacked into the site at vX.Y/ (the newest patch of each minor),
and versions.json lists them for the header's switcher in Material for MkDocs' format, latest (main's) first.
Usage: GITHUB_REPOSITORY=o/r GH_TOKEN=... python3 scripts/docs_versions.py site/dist"""

import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

LATEST = {"version": "latest", "title": "latest", "aliases": []}


def asset(tag: str) -> str:
    """The docs Release Assets attaches to the release (release.yml)"""
    return f"noggin-docs-{tag}.tar.gz"


def served(releases: list[dict]) -> list[tuple[str, str]]:
    """(vX.Y, its newest vX.Y.Z) for each minor with a docs asset, newest first; no drafts or prereleases"""
    newest: dict[tuple[int, int], tuple[int, str]] = {}
    for r in releases:
        m = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", r["tag_name"])
        docs = asset(r["tag_name"]) in {a["name"] for a in r["assets"]}
        if m and docs and not r["draft"] and not r["prerelease"]:
            major, minor, patch = map(int, m.groups())
            newest[major, minor] = max(newest.get((major, minor), (-1, "")), (patch, r["tag_name"]))
    return [(f"v{x}.{y}", newest[x, y][1]) for x, y in sorted(newest, reverse=True)]


def versions_json(versions: list[tuple[str, str]]) -> list[dict]:
    return [LATEST, *({"version": v, "title": tag, "aliases": []} for v, tag in versions)]


if __name__ == "__main__":
    dist, repo = Path(sys.argv[1]), os.environ["GITHUB_REPOSITORY"]
    out = subprocess.run(
        ["gh", "api", "--paginate", "--slurp", f"repos/{repo}/releases"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    versions = served([r for page in json.loads(out) for r in page])
    for version, tag in versions:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["gh", "release", "download", tag, "-R", repo, "-p", asset(tag), "-D", tmp], check=True)
            with tarfile.open(Path(tmp) / asset(tag)) as t:
                t.extractall(dist / version, filter="data")
        print(f"docs: {tag} at {version}/")
    (dist / "versions.json").write_text(json.dumps(versions_json(versions)) + "\n")
