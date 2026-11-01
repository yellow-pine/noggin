"""The third-party files the site serves itself (Mermaid: mermaid.py; Roboto: fonts.py; three.js: web/build.py), so no
page loads a script or a font from elsewhere: each is fetched once from its npm package on jsDelivr into .cache/ (CI
caches it by version) and checked against its pinned sha384 on every build, cached or not."""

import base64
import hashlib
import os
import urllib.request
from pathlib import Path

CACHE = Path(__file__).resolve().parent / ".cache"
NPM = "https://cdn.jsdelivr.net/npm/"


def fetch(path, integrity):
    """The file at path ("<package>@<version>/<file>") in npm, if its sha384 is integrity (as SRI writes it)."""
    cached = CACHE / path
    data = cached.read_bytes() if cached.is_file() else urllib.request.urlopen(NPM + path, timeout=60).read()
    if f"sha384-{base64.b64encode(hashlib.sha384(data).digest()).decode()}" != integrity:
        raise ValueError(f"{cached if cached.is_file() else NPM + path}: sha384 differs from the pinned one")
    if not cached.is_file():  # the site build runs in parallel test workers: write aside, then rename
        cached.parent.mkdir(parents=True, exist_ok=True)
        (tmp := cached.with_name(f"{cached.name}.{os.getpid()}")).write_bytes(data)
        tmp.replace(cached)
    return data
