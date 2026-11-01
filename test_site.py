"""The site (docs/adr/0009) as the pages workflow builds it: MkDocs Material builds the repo's Markdown strictly, so a
broken page or link fails here before it fails the deploy; every doc in the nav is a page, the local-only references
never ship, and the nav reaches the web viewer the workflow puts at /viewer."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import macros

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


def test_the_home_page_builds_the_behaviour_table_from_the_code(site):
    """reactions/director.py and install_hooks.py say which event plays what, eyes/eyes.py how often it blinks."""
    home = re.sub(r"<[^>]+>", "", (site / "index.html").read_text())
    for row in [
        "SessionStart\nwink (hello)",
        "UserPromptSubmit\nthinking: lids low, gaze averted, micro-saccades, a blink every 5-8 s",
        "Stop\neureka, sized by how long the turn took: under 20 s small, under 3 min normal, longer big",
        "Notification permission_prompt\nattention: half lids, a real left-right scan",
        "Notification idle_prompt\nbored: drooping lids, heavy blinks, one long closure",
        "StopFailure\nwince",
        "SessionEnd\nback to rest (a turn with no events for 15 min also returns to rest)",
    ]:
        assert row in home


def github(path):
    """The page as GitHub shows it: HTML comments hidden (the site's macros sit in them)."""
    return re.sub(r"<!--.*?-->", "", (ROOT / path).read_text(), flags=re.S)


def test_github_shows_a_link_to_the_site_for_the_behaviour_table():
    readme = github("README.md")
    assert "| SessionStart |" not in readme and "(https://yellowpine.com/noggin/#what-it-does)" in readme


def test_the_model_notes_build_the_picture_sizes_and_colours_from_the_code(site):
    """model/render/pictures.py and blender.py, model/geometry.py SPOOLS, model/mjcf.py VIEW: as Cansin set them."""
    notes = re.sub(r"<[^>]+>", "", (site / "docs" / "model-notes" / "index.html").read_text())
    for row in [
        "gestures\n600x450\n480 wide, 10 fps, 64 colours, at most 1 MB",
        "hero\n800x600\n640 wide, 10 fps, 48 colours, at most 3 MB",
        "Milky Pink\n#F7CED7\n#F7CED7\n#F7CED7",
        "Absolute Black\n#000000\n#2B2B2E\n#5A5A60",
        "Pure White\n#FFFFFF\n#FFFFFF\n#E8E8E8",
        "background\n\n#F7F4EE\n#F7F4EE",
    ]:
        assert row in notes
    assert "(https://yellowpine.com/noggin/docs/model-notes/#numbers-from-the-code)" in github("docs/model-notes.md")


def test_every_duration_left_in_the_readme_agrees_with_the_code():
    """The table is the site's; a duration GitHub still shows (say a blink every 5-8 s) must be one the code has."""
    durations = r"\b\d+(?:-\d+)? (?:s|min)\b"
    assert set(re.findall(durations, github("README.md"))) <= set(re.findall(durations, macros.behaviour()))
