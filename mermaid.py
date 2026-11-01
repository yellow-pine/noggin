"""MkDocs hook (mkdocs.yml hooks): the site serves its own Mermaid, the one mkdocs.yml extra.mermaid pins. Fetched once
from the npm package on jsDelivr into .cache/ (CI caches it), checked against the pinned sha384 on every build, cached
or not, and copied to assets/javascripts/, the one file overrides/main.html loads."""

import base64
import hashlib
import os
import urllib.request
from pathlib import Path

from mkdocs.exceptions import PluginError

CACHE = Path(__file__).resolve().parent / ".cache"


def on_post_build(config):
    version, integrity = config.extra["mermaid"]["version"], config.extra["mermaid"]["integrity"]
    name, url = f"mermaid-{version}.min.js", f"https://cdn.jsdelivr.net/npm/mermaid@{version}/dist/mermaid.min.js"
    cached = CACHE / name
    data = cached.read_bytes() if cached.is_file() else urllib.request.urlopen(url, timeout=60).read()
    if f"sha384-{base64.b64encode(hashlib.sha384(data).digest()).decode()}" != integrity:
        raise PluginError(f"{cached if cached.is_file() else url}: sha384 differs from mkdocs.yml extra.mermaid")
    if not cached.is_file():  # the site build runs in parallel test workers: write aside, then rename
        CACHE.mkdir(exist_ok=True)
        (tmp := CACHE / f"{name}.{os.getpid()}").write_bytes(data)
        tmp.replace(cached)
    (Path(config.site_dir) / "assets" / "javascripts" / name).write_bytes(data)
