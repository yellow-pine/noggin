"""MkDocs hook (mkdocs.yml hooks): the site serves its own Mermaid, the one mkdocs.yml extra.mermaid pins, fetched and
checked by vendored.py and copied to assets/javascripts/, the one file overrides/main.html loads."""

from pathlib import Path

from mkdocs.exceptions import PluginError

import vendored


def on_post_build(config):
    version, integrity = config.extra["mermaid"]["version"], config.extra["mermaid"]["integrity"]
    try:
        data = vendored.fetch(f"mermaid@{version}/dist/mermaid.min.js", integrity)
    except ValueError as e:
        raise PluginError(str(e)) from e
    (Path(config.site_dir) / "assets" / "javascripts" / f"mermaid-{version}.min.js").write_bytes(data)
