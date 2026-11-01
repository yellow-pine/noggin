"""The site as the Pages workflow builds it (web/build.py): the page loads only what the build writes, and offers
every gesture the model replays (model/traces.py) plus the hero loop."""

import re
from html.parser import HTMLParser

import pytest

from model import traces
from web import build


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.gestures = set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("src", "href", "data-src"):
            v = a.get(key)
            if v and not re.match(r"https?:|#", v):
                self.refs.add(v)
        if "data-gesture" in a:
            self.gestures.append(a["data-gesture"])


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    build.build(out)
    page = Page()
    page.feed((out / "index.html").read_text())
    return out, page


def test_the_page_loads_only_files_the_build_writes(site):
    out, page = site
    assert page.refs >= {"stage1.glb", "stage2.glb", "stage3.glb"}
    assert {r for r in page.refs if not (out / r).is_file()} == set()


def test_one_button_per_gesture_and_the_hero(site):
    _, page = site
    assert sorted(page.gestures) == sorted([*traces.GESTURES, "hero"])
