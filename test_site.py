"""The site (docs/adr/0009) as the pages workflow builds it: MkDocs Material builds the repo's Markdown strictly, so a
broken page or link fails here before it fails the deploy; every doc in the nav is a page, the local-only references
never ship, and the nav reaches the web viewer's page at /viewer. The README's pictures are built in CI too
(#226): none in git, every one a site URL the render job builds."""

import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from mkdocs.exceptions import PluginError
from mkdocs.utils.yaml import get_yaml_loader

ROOT = Path(__file__).resolve().parent


def test_every_doc_is_a_page(site):
    adrs = [f"docs/adr/{p.stem}/index.html" for p in (ROOT / "docs" / "adr").glob("*.md")]
    guides = [f"docs/{d}/{p.stem}/index.html" for d in ("build", "use") for p in (ROOT / "docs" / d).glob("*.md")]
    docs = ["GLOSSARY", "CONTRIBUTING", "docs/model-notes", "docs/face-design", "docs/how-it-works", "docs/pictures"]
    pages = ["index.html", *(f"{d}/index.html" for d in [*docs, "docs/credits"]), *adrs, *guides]
    assert adrs and guides and [p for p in pages if not (site / p).is_file()] == []


def test_a_page_that_moved_keeps_its_url(site):
    """docs/build-notes.md split into the Build and Use pages (#280): its old URL sends a reader to Stage 1."""
    assert 'content="0; url=../build/stage-1/"' in (site / "docs" / "build-notes" / "index.html").read_text()


def test_the_home_page_is_the_landing_page(site):
    """docs/index.md is the site's root (#280): its buttons lead into Build, Use and the viewer; the README, which is
    for contributors, stays off the site."""
    home = (site / "index.html").read_text()
    buttons = [a for a in re.findall(r"<a [^>]*>", home) if "md-button" in a]
    for target in [
        'href="docs/build/parts/"',
        'href="docs/use/noggin-service/"',
        'href="https://yellowpine.com/noggin/viewer/"',
    ]:
        assert any(target in a for a in buttons), target
    assert "make check" not in home and not (site / "README" / "index.html").exists()


def test_no_real_photo_is_public(site):
    """No real photo of the Mech on the site or in the README until there are staged ones (Cansin, 2026-11-01): every
    picture shown or linked is a site URL CI renders in Blender, and no photo file ships."""
    photo = re.compile(r"\.(?:jpe?g|heic)\b", re.I)
    blender = "https://yellowpine.com/noggin/images/"
    pages = {p: p.read_text() for p in site.rglob("*.html")}
    links = [(p, u) for p, html in pages.items() for u in re.findall(r'(?:href|src)="([^"]+)"', html)]
    links += [("README.md", u) for u in re.findall(r'(?:\]\(|src=")([^)"\s]+)', (ROOT / "README.md").read_text())]
    assert [(p, u) for p, u in links if photo.search(u) and not u.startswith(blender)] == []
    assert [f for f in site.rglob("*") if photo.search(f.name)] == []


def test_the_home_page_finds_its_theme(site):
    """exclude_docs applies to the theme's own files too: Material's CSS and JS must ship."""
    refs = re.findall(r'(?:href|src)="(assets/[^"]+)"', (site / "index.html").read_text())
    assert any(r.endswith(".css") for r in refs) and [r for r in refs if not (site / r).is_file()] == []


def test_the_references_do_not_ship(site):
    assert not (site / "docs" / "references").exists() and not (site / "model").exists()


def test_no_generated_picture_is_tracked():
    """The pictures are built in CI and served from the site (#226): git holds none of them (photos stay)."""
    from model.render import pictures  # here, not at the top: it imports the model, as macros does

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert [f for f in tracked if os.path.basename(f) in sum(pictures.SITE.values(), [])] == []


def test_the_nav_reaches_every_decision_and_the_viewer(site):
    home = (site / "index.html").read_text()
    links = [f'href="docs/adr/{p.stem}/"' for p in (ROOT / "docs" / "adr").glob("*.md")] + ['href="viewer/"']
    assert [link for link in links if link not in home] == []


@pytest.mark.parametrize("page", ["index.html", "docs/use/gestures/index.html"])
def test_the_behaviour_table_is_built_from_the_code(site, page):
    """reactions/director.py and install_hooks.py say which event plays what, eyes/eyes.py how often it blinks."""
    home = re.sub(r"<[^>]+>", "", (site / page).read_text())
    for row in [
        "SessionStart\nwink (hello)",
        "UserPromptSubmit\nthinking: lids low, gaze averted, micro-saccades, a blink every 5-8 s",
        "Stop\neureka, sized by how long the turn took: under 20 s small, under 3 min normal, longer big",
        "Notification permission_prompt\nattention: half lids, a real left-right scan",
        "Notification idle_prompt\nbored: drooping lids, heavy blinks, one long closure",
        "StopFailure\nwince",
        "SessionEnd\nback to rest (also when the last turn ends 15 min after its prompt, whatever Triggers arrive)",
    ]:
        assert row in home


# the Mermaid the site serves (mkdocs.yml extra.mermaid, overrides/main.html): the one every diagram renders with here
MERMAID = yaml.load((ROOT / "mkdocs.yml").read_text(), Loader=get_yaml_loader())["extra"]["mermaid"]
MERMAID_CLI = [f"@mermaid-js/mermaid-cli@{MERMAID['cli']}", f"mermaid@{MERMAID['version']}"]


def sri(file):
    """The file's sha384 as SRI (and vendored.py's pins) write it."""
    return f"sha384-{base64.b64encode(hashlib.sha384(file.read_bytes()).digest()).decode()}"


def test_the_site_serves_the_mermaid_the_diagrams_render_with(site):
    """The site's own copy, with its hash, and only on pages with a diagram; every page allows scripts from the site
    alone, so Material's floating unpkg mermaid@11 can never load, not even when the site's copy fails (a page with the
    web viewer also lets the Draco decoder compile its WASM in a Blob worker); no page names a script elsewhere."""
    file = site / "assets" / "javascripts" / f"mermaid-{MERMAID['version']}.min.js"
    assert MERMAID["integrity"] == sri(file)
    csp = """<meta http-equiv="Content-Security-Policy" content="script-src 'self' 'unsafe-inline'{}">"""
    for page in site.rglob("*.html"):
        html, local = page.read_text(), os.path.relpath(file, page.parent)
        if 'http-equiv="refresh"' in html:  # a moved page's stub (mkdocs-redirects): no theme, one inline script
            assert re.findall(r"<script[^>]* src=", html) == [], page
            continue
        srcs = [s for s in re.findall(r'<script[^>]* src="([^"]+)"', html) if "mermaid" in s]
        assert srcs == ([local] if 'class="mermaid"' in html else []), page
        assert f'integrity="{MERMAID["integrity"]}"' in html or not srcs
        viewer = " 'wasm-unsafe-eval'; worker-src 'self' blob:" if 'class="noggin-viewer"' in html else ""
        assert csp.format(viewer) in html.split("</head>")[0], page
        assert [s for s in re.findall(r'<script[^>]* src="([^"]+)"', html) if re.match(r"https?:|//", s)] == [], page
        sheets = re.findall(r'<link[^>]* rel="stylesheet"[^>]* href="([^"]+)"', html)  # no Google Fonts (font: false)
        fonts = re.findall(r'url\("([^"]+)"\)', html.split("</head>")[0])  # the site's Roboto (fonts.py)
        assert sheets and fonts and [s for s in sheets + fonts if re.match(r"https?:|//|data:", s)] == [], page
    assert 'class="mermaid"' in (site / "docs" / "how-it-works" / "index.html").read_text()
    assert 'class="noggin-viewer"' in (site / "viewer" / "index.html").read_text()


def test_every_page_reads_in_the_sites_own_roboto(site):
    """Roboto for text and Roboto Mono for code, the fonts Material would ask Google Fonts for (theme.font: false), from
    the site itself (#308): every page declares both, upright and italic, from files the site serves with the hashes
    fonts.py pins, and makes them Material's fonts."""
    import fonts

    pinned = set(fonts.SHA384.values())
    for page in site.rglob("*.html"):
        html = page.read_text()
        if 'http-equiv="refresh"' in html:  # a moved page's stub: no theme
            continue
        head = html.split("</head>")[0]
        faces = {}
        for family, style, url in re.findall(r'font-family: "([^"]+)"; font-style: (\w+);[^}]*url\("([^"]+)"\)', head):
            # 404.html's url is from the site's root (site_url's path)
            file = site / url.removeprefix("/noggin/") if url.startswith("/") else page.parent / url
            faces[family, style] = sri(file)
        assert sorted(faces) == [
            ("Roboto", "italic"),
            ("Roboto", "normal"),
            ("Roboto Mono", "italic"),
            ("Roboto Mono", "normal"),
        ], page
        assert set(faces.values()) == pinned, page
        assert '--md-text-font: "Roboto"; --md-code-font: "Roboto Mono"' in head, page


def test_a_mermaid_that_is_not_the_pinned_one_fails_the_build(tmp_path, monkeypatch):
    """vendored.py checks the hash cached or fetched, so a tampered cache never reaches the site."""
    import mermaid
    import vendored

    monkeypatch.setattr(vendored, "CACHE", tmp_path)
    (tmp_path / f"mermaid@{MERMAID['version']}" / "dist").mkdir(parents=True)
    (tmp_path / f"mermaid@{MERMAID['version']}" / "dist" / "mermaid.min.js").write_text("alert(1)")
    (tmp_path / "site" / "assets" / "javascripts").mkdir(parents=True)
    config = SimpleNamespace(extra={"mermaid": MERMAID}, site_dir=str(tmp_path / "site"))
    with pytest.raises(PluginError, match="sha384 differs"):
        mermaid.on_post_build(config)
    assert list((tmp_path / "site").rglob("*.js")) == []


def test_every_diagram_renders(tmp_path):
    """Every Mermaid block in docs/ drawn by Mermaid's own CLI in headless Chrome (a parse or layout
    error fails it); the site's Mermaid, GitHub its own 12 (docs/research/2026-11-01-diagrams.md)."""
    docs = [ROOT / "README.md", *(p for p in (ROOT / "docs").rglob("*.md") if "references" not in p.parts)]
    files = [p for p in docs if "```mermaid" in p.read_text()]
    assert ROOT / "docs" / "how-it-works.md" in files
    pkgs = [arg for pkg in MERMAID_CLI for arg in ("-p", pkg)]
    for f in files:
        r = subprocess.run(
            ["npx", "-y", *pkgs, "mmdc", "-q", "-i", str(f), "-o", str(tmp_path / f.name)],
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, f"{f.relative_to(ROOT)}: {r.stderr[-2000:]}"


def github(path):
    """The page as GitHub shows it: HTML comments hidden (the site's macros sit in them)."""
    return re.sub(r"<!--.*?-->", "", (ROOT / path).read_text(), flags=re.S)


# each doc whose numbers the site builds from the code, and where on the site GitHub's link sends a reader for them
SITE_TABLES = {
    "docs/index.md": "#what-it-does",
    "docs/use/gestures.md": "docs/use/gestures/#which-event-plays-what",
    "docs/build/stage-1.md": "docs/build/stage-1/#parts-from-the-model",
    "docs/build/stage-2.md": "docs/build/stage-2/#servos-it-adds",
    "docs/build/stage-3.md": "docs/build/stage-3/#servos-it-adds",
    "docs/model-notes.md": "docs/model-notes/#numbers-from-the-code",
}


@pytest.mark.parametrize("doc", SITE_TABLES)
def test_github_links_to_the_site_for_the_tables_built_from_the_code(site, doc):
    """GitHub hides the macros: its link lands on the site's page at the heading of the table built there."""
    page, anchor = SITE_TABLES[doc].split("#")
    assert f"(https://yellowpine.com/noggin/{page}#{anchor})" in github(doc)
    assert f'id="{anchor}"' in (site / page / "index.html").read_text()


def test_the_readme_is_for_contributors():
    """#279: the pitch, the hero, the call-out to the site, setup, checks, CI/CD, contributing, credits, licence;
    building and using the Mech are the site's."""
    readme = github("README.md")
    assert (
        "[Docs, build guide and live 3D viewer → https://yellowpine.com/noggin](https://yellowpine.com/noggin/)"
        in readme
    )
    assert "(https://yellowpine.com/noggin/docs/credits/)" in readme and "(CONTRIBUTING.md)" in readme
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert [
        p.name for p in workflows if f"| {yaml.safe_load(p.read_text())['name']} | `{p.name}` |" not in readme
    ] == []
    assert "scripts/setup.sh" not in readme and "## Gestures" not in readme


def test_the_model_notes_build_the_picture_sizes_and_colours_from_the_code(site):
    """model/render/pictures.py and blender.py, model/geometry.py SPOOLS, model/mjcf.py VIEW: as Cansin set them."""
    notes = re.sub(r"<[^>]+>", "", (site / "docs" / "model-notes" / "index.html").read_text())
    for row in [
        "gestures\n400x300\n400 wide, 8 fps, 64 colours, at most 1 MB",
        "hero\n800x400\n800 wide, 8 fps, 48 colours, at most 3 MB",
        "Milky Pink\n#F7CED7\n#F7CED7\n#F7CED7",
        "Absolute Black\n#000000\n#2B2B2E\n#5A5A60",
        "Pure White\n#FFFFFF\n#FFFFFF\n#E8E8E8",
        "background\n\n#F7F4EE\n#F7F4EE",
    ]:
        assert row in notes


def test_the_diagrams_numbers_agree_with_the_code():
    """docs/how-it-works.md draws the Link (eyes/wifi.py, noggin/wifi.py) and the director's timings
    (reactions/director.py) as GitHub shows them: each number must be the code's."""
    from wifi import BEACON_MS  # eyes/wifi.py, the Core's (conftest puts eyes/ on the path)

    from macros import duration
    from noggin.wifi import ACK_SECONDS
    from reactions.director import BUSY_SECONDS, STALE_TURN_SECONDS, TIERS

    page = (ROOT / "docs" / "how-it-works.md").read_text()
    busy = sorted(BUSY_SECONDS.values())
    for phrase in [
        f"every {BEACON_MS / 1000:g} s",
        f"waiting {', '.join(f'{s:g}' for s in ACK_SECONDS)} s",
        f"under {duration(TIERS[0][0])} small, under {duration(TIERS[1][0])} normal, longer big",
        f"{busy[0]:g}-{busy[-1]:g} s",
        f"is {duration(STALE_TURN_SECONDS)} old",
    ]:
        assert phrase in page, phrase


def test_the_stale_turn_sentence_follows_the_director():
    """The table says the last turn ends a fixed time after its prompt, not after a quiet spell: the Director holds
    a turn with a Trigger every minute exactly that long, then rests."""
    import macros  # here, not at the top: it imports the model
    from reactions.director import STALE_TURN_SECONDS, Director

    d, trigger = Director(), {"hook_event_name": "Notification", "session_id": "s", "notification_type": "idle_prompt"}
    d.handle({"hook_event_name": "UserPromptSubmit", "session_id": "s"}, 0)
    for minute in range(STALE_TURN_SECONDS // 60):
        d.handle(trigger, minute * 60)
        assert d.tick(minute * 60) == []
    assert d.tick(STALE_TURN_SECONDS + 1) == ["rest"]
    sentence = f"the last turn ends {macros.duration(STALE_TURN_SECONDS)} after its prompt, whatever Triggers arrive"
    assert sentence in macros.behaviour()


def test_every_number_github_shows_agrees_with_the_code():
    """The tables are the site's; a duration GitHub still shows on the landing page (say a blink every 5-8 s) must be
    one the code has, and each Core's servo count in the overview must be its channels' in model/geometry.py."""
    import macros  # here, not at the top: it imports the model, which only this test needs
    from model.geometry import CHANNELS

    home, durations = github("docs/index.md"), r"\b\d+(?:-\d+)? (?:s|min)\b"
    assert set(re.findall(durations, home)) <= set(re.findall(durations, macros.behaviour()))
    servos = re.findall(r"Core (\d): [^\"]*?(\d+) servos", github("docs/how-it-works.md"))
    assert servos == [(core, str(len(CHANNELS[f"core{core}"]))) for core, _ in servos] and len(servos) == 2


def test_every_picture_ci_builds_is_shown_from_the_site():
    """The README's and the docs' pictures (the badges aside; Markdown images or the figures' <img>s) are the site's
    absolute /images URLs of files in the pictures manifest, and each of those is shown somewhere."""
    from model.render import pictures

    docs = [
        ROOT / "README.md",
        *(p for p in (ROOT / "docs").rglob("*.md") if not {"references", "research"} & set(p.parts)),
    ]
    urls = {
        u
        for d in docs
        for u in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", d.read_text()) + re.findall(r'<img src="([^"]+)"', d.read_text())
        if u.startswith("http") and not u.startswith("https://img.shields.io/")
    }
    site = "https://yellowpine.com/noggin/images/"
    assert [u for u in urls if not u.startswith(site)] == []
    assert sorted(u.removeprefix(site) for u in urls) == sorted(sum(pictures.SITE.values(), []))


def test_the_hero_is_800x400_and_centred_wherever_it_shows(site):
    """Cansin (#278, #293): the one 800x400 hero, at its size and centred, leads the README (GitHub drops CSS, so a
    centred HTML paragraph, its width alone: GitHub's CSS would squash a fixed height on a phone) and shows on the site
    in a figure, which Material centres."""
    from model.render import pictures

    hero = "https://yellowpine.com/noggin/images/hero.gif"
    assert pictures.HERO_SIZE == (800, 400)
    readme = (ROOT / "README.md").read_text()
    assert re.search(rf'^<p align="center"><img src="{hero}" width="800" alt="[^"]+"></p>$', readme, re.M)
    assert readme.index(hero) < readme.index("## ")
    imgs = {
        p.relative_to(site).as_posix(): re.findall(rf"(<figure>\s*)?(<img [^>]*{hero}[^>]*>)", p.read_text())
        for p in site.rglob("*.html")
    }
    imgs = {p: found for p, found in imgs.items() if found}
    assert {"index.html", "docs/pictures/index.html"} <= set(imgs)
    for page, found in imgs.items():
        for figure, img in found:
            assert figure and 'width="800"' in img and 'height="400"' in img, (page, img)


def test_the_motions_list_is_every_motion_of_the_pictures_from_the_code():
    """`make pictures-list` (the pages workflow's motions job, #297): the Stage views on every Stage, the hero on
    stage 3 and each gesture of model/traces.py on stage 1, each with the Stages its trajectories bake on."""
    from model import traces

    out = subprocess.run(["make", "-s", "pictures-list"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [
        {"motion": "views", "stages": "noggin-stage1 noggin-stage2 noggin-stage3"},
        {"motion": "hero", "stages": "noggin-stage3"},
        *({"motion": g, "stages": "noggin-stage1"} for g in traces.GESTURES),
    ]


def test_the_pages_workflow_renders_one_job_per_motion_and_names_none():
    """`render` fans out over the motions job's list (#297): a new gesture needs no workflow edit."""
    from model.render import pictures

    text = (ROOT / ".github" / "workflows" / "pages.yml").read_text()
    jobs = yaml.safe_load(text)["jobs"]
    assert "make -s pictures-list" in jobs["motions"]["steps"][-1]["run"]
    assert jobs["render"]["strategy"]["matrix"] == {"include": "${{ fromJSON(needs.motions.outputs.list) }}"}
    assert jobs["render"]["name"] == "render (${{ matrix.motion }})"
    assert [m for m in pictures.SITE if re.search(rf"\b{m}\b", text)] == []


@pytest.mark.parametrize(
    "motions, render, passes",
    [
        ("success", "success", True),
        ("skipped", "skipped", True),
        ("success", "failure", False),
        ("success", "cancelled", False),
        ("failure", "skipped", False),
    ],
)
def test_the_required_pictures_check_is_every_runner_or_none(motions, render, passes):
    """`pictures`, the required check (#245), reports the motions job and the render runners as one: green when every
    motion passed or none ran (nothing the pictures are made from changed), red when any failed or was cancelled,
    the motions list too (render then skips)."""
    job = yaml.safe_load((ROOT / ".github" / "workflows" / "pages.yml").read_text())["jobs"]["pictures"]
    assert (job["needs"], job["if"]) == (["motions", "render"], "${{ !cancelled() }}")
    (step,) = job["steps"]
    assert step["env"] == {"RESULTS": "${{ needs.motions.result }} ${{ needs.render.result }}"}
    r = subprocess.run(["bash", "-c", step["run"]], env={**os.environ, "RESULTS": f"{motions} {render}"})
    assert (r.returncode == 0) is passes


def test_no_real_photos_are_tracked():
    """Cansin, 2026-11-01: real photos of the build stay local (docs/references/build-photos) until staged
    photos exist."""
    globs = ["*.jpg", "*.jpeg", "*.heic", "*.JPG", "*.HEIC"]
    tracked = subprocess.run(["git", "ls-files", *globs], capture_output=True, text=True, check=True).stdout.split()
    assert tracked == [], tracked


def schemes(html):
    """Each Material colour scheme's CSS variables as the page sets them (palette.py)."""
    blocks = re.findall(r"\[data-md-color-scheme=(\w+)\]\s*\{([^}]*)\}", html.split("</head>")[0])
    return {s: dict(re.findall(r"(--[\w-]+):\s*([^;]+);", body)) for s, body in blocks}


def test_the_palette_is_the_mechs_own_colours_light_and_dark(site):
    """#282: paper background, spool pink header, near-black text (the pictures' background and the Absolute Black
    Blender draws, docs/model-notes.md), and a dark scheme the reader can switch to on every page."""
    for page in ["index.html", "docs/build/stage-1/index.html", "viewer/index.html"]:
        html = (site / page).read_text()
        light, dark = schemes(html)["default"], schemes(html)["slate"]
        assert (light["--md-default-bg-color"], light["--md-default-fg-color"]) == ("#F7F4EE", "#2B2B2E"), page
        assert (dark["--md-default-bg-color"], dark["--md-default-fg-color"]) == ("#2B2B2E", "#F7F4EE"), page
        assert light["--md-primary-fg-color"] == dark["--md-primary-fg-color"] == "#F7CED7", page
        assert len(re.findall(r'<input class="md-option" data-md-color-media=', html)) == 2, page


def test_wcag_contrast():
    """WCAG 2's own figures: black on white 21:1, #777 on white just under AA."""
    from palette import contrast

    assert contrast("#000000", "#FFFFFF") == pytest.approx(21) and contrast("#FFFFFF", "#000000") == pytest.approx(21)
    assert contrast("#777777", "#FFFFFF") == pytest.approx(4.48, abs=0.01)


def test_every_text_colour_reads_at_aa_in_both_schemes(site):
    """Text (and its lighter shade), links and buttons on the page, the header's text on the pink, a hovered button's
    text on its fill: each at least 4.5:1 (WCAG 2 AA)."""
    from palette import contrast

    for scheme, v in schemes((site / "index.html").read_text()).items():
        bg = v["--md-default-bg-color"]
        for fg, on in [
            (v["--md-default-fg-color"], bg),
            (v["--md-default-fg-color--light"], bg),  # headings, the nav's and contents' titles
            (v["--md-typeset-a-color"], bg),
            (v["--md-primary-bg-color"], v["--md-primary-fg-color"]),
            (v["--md-accent-bg-color"], v["--md-accent-fg-color"]),
        ]:
            assert contrast(fg, on) >= 4.5, (scheme, fg, on)
