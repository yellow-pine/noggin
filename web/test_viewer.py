"""The viewer in a browser on the built site (make site, with make web's GLBs in site/viewer), Playwright driving the
installed Chrome: it offers every gesture and the hero, plays a gesture to its end and back to the hero, switches Stage,
and asks no other host for anything. CI runs it after make site (pages.yml); locally, after make site:
uv run --with playwright==<the version pages.yml pins> pytest web/test_viewer.py"""

import functools
import http.server
import threading
from pathlib import Path

import pytest

from model import traces

sync_api = pytest.importorskip("playwright.sync_api")  # not a dev dependency: CI's site job adds it (pages.yml)
SITE = Path(__file__).resolve().parent.parent / "site"
# Material's header asks GitHub for the repo's stars, forks and latest release (repo_url): data, not code
GITHUB_FACTS = "https://api.github.com/repos/yellow-pine/noggin"


@pytest.fixture(scope="module")
def server():
    if not (SITE / "viewer" / "stage3.glb").is_file():
        pytest.skip(f"{SITE / 'viewer'} has no GLBs (make web, then make site)")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}/"
    httpd.shutdown()


def test_the_viewer_plays_a_gesture_from_the_site_alone(server):
    expect, requests, errors = sync_api.expect, [], []
    with sync_api.sync_playwright() as p:
        # the installed Chrome; SwiftShader draws the WebGL where there is no GPU (CI's runners)
        browser = p.chromium.launch(channel="chrome", args=["--enable-unsafe-swiftshader"])
        page = browser.new_page()
        page.on("request", lambda r: requests.append(r.url))
        page.on("pageerror", lambda e: errors.append(e))
        # three.js logs a shader that fails to compile as an error; GitHub's 404 for a latest release (none yet) aside
        page.on("console", lambda m: m.type == "error" and GITHUB_FACTS not in m.location["url"] and errors.append(m))
        page.goto(server + "viewer/")
        button = functools.partial(page.get_by_role, "button", exact=True)
        expect(button(name="Stage 3")).to_have_attribute("aria-pressed", "true")
        expect(button(name="hero")).to_have_attribute("aria-pressed", "true", timeout=30_000)  # Stage 3 loaded
        gestures = page.get_by_role("navigation", name="Gesture").get_by_role("button")
        assert sorted(gestures.all_text_contents()) == sorted([*traces.GESTURES, "hero"])
        # every button pressed from here on, in order: a slow software-drawn frame can play the whole wink at once
        page.evaluate("""() => {
          window.pressed = [];
          const log = (m) => m.target.ariaPressed === "true" && pressed.push(m.target.textContent);
          new MutationObserver((ms) => ms.forEach(log))
            .observe(document.querySelector(".noggin-viewer"), { subtree: true, attributeFilter: ["aria-pressed"] });
        }""")
        button(name="wink").click()
        page.wait_for_function("() => pressed.join() === 'wink,hero'", timeout=30_000)  # the wink, then the hero
        button(name="Stage 1").click()
        expect(button(name="Stage 1")).to_have_attribute("aria-pressed", "true")
        expect(button(name="wink")).to_be_enabled(timeout=30_000)
        expect(button(name="hero")).to_have_count(0)  # Stage 1 has no neck
        browser.close()
    assert [str(e) for e in errors] == []
    # the site's files, and the Blob worker DRACOLoader makes from them
    assert [u for u in requests if not u.startswith((server, f"blob:{server}", GITHUB_FACTS))] == []
