"""MkDocs hook (mkdocs.yml hooks): Roboto and Roboto Mono, the fonts Material asks Google Fonts for, which theme.font:
false turns off, served by the site itself (#308): Fontsource's variable woff2, upright and italic, fetched and checked
by vendored.py and copied to assets/fonts/, which overrides/main.html declares on every page."""

from pathlib import Path

from mkdocs.exceptions import PluginError

import vendored

# shortcut: the Latin subset only (all the docs' text but its few arrows, which fall back to the system's font); add
# Fontsource's latin-ext or symbols files beside them if the docs ever need more
VERSION = "5.3.0"  # of @fontsource-variable/roboto and @fontsource-variable/roboto-mono
FONTS = {  # by Fontsource's name for each file: its package's, then the subset's
    "roboto-latin-wght-normal.woff2": "sha384-cRWqYoK1JFpgIWsQLV3fZnrYFvqD8CddruARJEScLgYvbD84hbbiYCHl6sB78gxH",
    "roboto-latin-wght-italic.woff2": "sha384-pQoTb43DE8y6uPy1EbOfhPbWDf3Bs0yZSW8FwO3ebZOhfxt/702KJN3Rvi7hdN2W",
    "roboto-mono-latin-wght-normal.woff2": "sha384-3Ogr/uVItuEjNsNRfkOcwej8FEB5Q6ZWWkerKqBYHzdO7r11dvUGTVD/lg/pDsve",
    "roboto-mono-latin-wght-italic.woff2": "sha384-bfXlezDjZ6kfQ7xUINYpuqwKf49/Irv2tx/eZp6nBtZnY3CfODBBg/a1uDUPWhgO",
}


def on_post_build(config):
    (out := Path(config.site_dir) / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for name, integrity in FONTS.items():
        package = name.split("-latin-")[0]
        try:
            data = vendored.fetch(f"@fontsource-variable/{package}@{VERSION}/files/{name}", integrity)
        except ValueError as e:
            raise PluginError(str(e)) from e
        (out / name).write_bytes(data)
