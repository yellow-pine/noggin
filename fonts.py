"""MkDocs hook (mkdocs.yml hooks): Roboto and Roboto Mono, the fonts Material asks Google Fonts for, which theme.font:
false turns off, served by the site itself (#308): Fontsource's variable woff2, upright and italic, fetched and checked
by vendored.py and copied to assets/fonts/; overrides/main.html declares each face (extra.fonts) on every page."""

from pathlib import Path

from mkdocs.exceptions import PluginError

import vendored

VERSION = "5.3.0"  # of @fontsource-variable/roboto and @fontsource-variable/roboto-mono
FAMILIES = {"Roboto": ("roboto", "100 900"), "Roboto Mono": ("roboto-mono", "100 700")}  # package, weight axis
# shortcut: the Latin subset only, so the docs' few arrows, Greek letters and math signs (the research notes') are
# drawn in the system's font; add Fontsource's math subset with its unicode-range if they should be Roboto too
SHA384 = {  # of each package's Latin file per style
    ("roboto", "normal"): "sha384-cRWqYoK1JFpgIWsQLV3fZnrYFvqD8CddruARJEScLgYvbD84hbbiYCHl6sB78gxH",
    ("roboto", "italic"): "sha384-pQoTb43DE8y6uPy1EbOfhPbWDf3Bs0yZSW8FwO3ebZOhfxt/702KJN3Rvi7hdN2W",
    ("roboto-mono", "normal"): "sha384-3Ogr/uVItuEjNsNRfkOcwej8FEB5Q6ZWWkerKqBYHzdO7r11dvUGTVD/lg/pDsve",
    ("roboto-mono", "italic"): "sha384-bfXlezDjZ6kfQ7xUINYpuqwKf49/Irv2tx/eZp6nBtZnY3CfODBBg/a1uDUPWhgO",
}


def file(package, style):
    return f"{package}-latin-wght-{style}.woff2"  # Fontsource's name for it


def on_config(config):
    config.extra["fonts"] = [
        {"family": family, "style": style, "weight": weight, "file": file(package, style)}
        for family, (package, weight) in FAMILIES.items()
        for style in ("normal", "italic")
    ]


def on_post_build(config):
    (out := Path(config.site_dir) / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    for (package, style), integrity in SHA384.items():
        try:
            data = vendored.fetch(f"@fontsource-variable/{package}@{VERSION}/files/{file(package, style)}", integrity)
        except ValueError as e:
            raise PluginError(str(e)) from e
        (out / file(package, style)).write_bytes(data)
