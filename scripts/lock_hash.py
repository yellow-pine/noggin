"""Print uv.lock's sha256 without the project's own version: what every CI cache and `make ours` key on in its place
(#403), since a release's version bump is the one change to the lock that changes nothing they build. Run from the
repo's root; the project's name is pyproject.toml's."""

import hashlib
import json
import tomllib
from pathlib import Path

name = tomllib.loads(Path("pyproject.toml").read_text())["project"]["name"]
lock = tomllib.loads(Path("uv.lock").read_text())
del next(p for p in lock["package"] if p["name"] == name)["version"]  # missing: fail, never hash a bump in silently
print(hashlib.sha256(json.dumps(lock, sort_keys=True).encode()).hexdigest())
