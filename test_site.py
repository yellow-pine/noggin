"""The site (docs/adr/0009) as the pages workflow builds it: MkDocs Material builds the repo's Markdown strictly, so a
broken page or link fails here before it fails the deploy; every doc in the nav is a page, the local-only references
never ship, and the nav reaches the web viewer the workflow puts at /viewer."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    r = subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "-d", str(out)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "NO_MKDOCS_2_WARNING": "1"},  # hush Material's banner about MkDocs 2 (it requires mkdocs<2)
    )
    assert r.returncode == 0, r.stderr[-3000:]
    return out


def test_every_doc_is_a_page(site):
    adrs = [f"docs/adr/{p.stem}/index.html" for p in (ROOT / "docs" / "adr").glob("*.md")]
    docs = ["GLOSSARY", "CONTRIBUTING", "docs/build-notes", "docs/model-notes", "docs/face-design"]
    pages = ["index.html", *(f"{d}/index.html" for d in docs), *adrs]
    assert adrs and [p for p in pages if not (site / p).is_file()] == []


def test_the_home_page_finds_its_theme(site):
    """exclude_docs applies to the theme's own files too: Material's CSS and JS must ship."""
    refs = re.findall(r'(?:href|src)="(assets/[^"]+)"', (site / "index.html").read_text())
    assert any(r.endswith(".css") for r in refs) and [r for r in refs if not (site / r).is_file()] == []


def test_the_readme_pictures_ship_and_the_references_do_not(site):
    assert (site / "docs" / "images" / "hero.gif").is_file()
    assert not (site / "docs" / "references").exists() and not (site / "model").exists()


def test_the_nav_reaches_every_decision_and_the_viewer(site):
    home = (site / "index.html").read_text()
    links = [f'href="docs/adr/{p.stem}/"' for p in (ROOT / "docs" / "adr").glob("*.md")] + ['href="viewer/"']
    assert [link for link in links if link not in home] == []
