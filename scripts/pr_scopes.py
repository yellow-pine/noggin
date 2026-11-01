"""The scopes a PR title may name (docs/adr/0010): the repo's areas, one per top-level directory git tracks, so a new
area is a scope the moment it lands. The tooling folders (dot-folders) are not areas, except .github, which is `ci`;
overrides/ (the site's theme) is `site`. Prints one per line, sorted, for the PR Title check.
Usage: python3 scripts/pr_scopes.py (in the repo)"""

import subprocess

SCOPE_OF_DIR = {".github": "ci", "overrides": "site"}

if __name__ == "__main__":
    files = subprocess.run(["git", "ls-files"], check=True, capture_output=True, text=True).stdout.splitlines()
    dirs = {f.split("/")[0] for f in files if "/" in f}
    print("\n".join(sorted({SCOPE_OF_DIR.get(d, d) for d in dirs if d in SCOPE_OF_DIR or not d.startswith(".")})))
