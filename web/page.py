"""MkDocs hook (mkdocs.yml hooks): the viewer's page, web/viewer.md, at viewer/ beside the GLBs and three.js the Pages
workflow copies there (make site), in the theme's viewer template (overrides/viewer.html)."""

from pathlib import Path

from mkdocs.structure.files import File


def on_files(files, config):
    files.append(File.generated(config, "viewer.md", abs_src_path=str(Path(__file__).with_name("viewer.md"))))
