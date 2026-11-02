"""The site's sources (docs/adr/0009, 0013) as GitHub shows them, and the numbers the code gives the site
(macros.py): the built site itself is checked in site/ (site.test.mjs, smoke.pw.mjs). The pictures are none in git
(#226); the site shows the next Mech's alone, today's are rendered locally alone (#640, #649, docs/adr/0019)."""

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent


def test_no_generated_picture_is_tracked():
    """The pictures are built in CI and served from the site (#226): git holds none of them (photos stay)."""
    from model.render import pictures  # here, not at the top: it imports the model, as macros does

    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split()
    assert [f for f in tracked if os.path.basename(f) in sum(pictures.SITE.values(), [])] == []


def test_the_behaviour_table_is_built_from_the_code():
    """reactions/director.py and install_hooks.py say which event plays what, eyes/eyes.py how often it blinks (#621:
    at Rest too)."""
    import macros  # here, not at the top: it imports the model

    table = macros.behaviour()
    for row in [
        "| SessionStart | wink (hello) |",
        "| UserPromptSubmit | thinking: lids low, gaze averted, micro-saccades, a blink every 5-8 s |",
        "| Stop | eureka, sized by how long the turn took: under 20 s small, under 3 min normal, longer big |",
        "| Notification permission_prompt | attention: half lids, a real left-right scan |",
        "| Notification idle_prompt | bored: drooping lids, heavy blinks, one long closure |",
        "| StopFailure | wince |",
        "| SessionEnd | back to rest: still but for a blink every 3-6 s (also when the last turn ends 15 min after its"
        " prompt, whatever Triggers arrive) |",
    ]:
        assert row in table


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
    "docs/build/wiring.md": "docs/build/wiring/#servo-ports",
    "docs/build/tests.md": "docs/build/tests/#the-clearance-coupon",
    "docs/ci-cd.md": "docs/ci-cd/#workflows",
}


@pytest.mark.parametrize("doc", SITE_TABLES)
def test_github_links_to_the_site_for_the_tables_built_from_the_code(doc):
    """GitHub hides the macros: its link lands on the site's page at the heading of the table built there (that the
    heading is there, site.test.mjs checks on the built site)."""
    page, anchor = SITE_TABLES[doc].split("#")
    assert f"(https://yellowpine.com/noggin/{page}#{anchor})" in github(doc)


def test_the_readme_is_for_contributors():
    """#279: the pitch, the links to the site, setup, checks, CI/CD, contributing, credits, licence; building and
    using the Mech are the site's. #595: the site's links by name; no hero or viewer till the clean-room Mech (#640)."""
    readme = github("README.md")
    site = "https://yellowpine.com/noggin/"
    links = re.findall(r'<a href="([^"]+)"><b>([^<]+)</b></a>', readme)
    assert links == [(site, "Docs"), (f"{site}docs/build/parts/", "Build guide")]
    assert readme.index("<b>Docs</b>") < readme.index("## ")
    assert "(https://yellowpine.com/noggin/docs/credits/)" in readme and "(CONTRIBUTING.md)" in readme
    assert "(https://yellowpine.com/noggin/docs/ci-cd/)" in readme  # #425
    assert "scripts/setup.sh" not in readme and "## Gestures" not in readme


def test_the_wiring_table_is_built_from_the_code():
    """Both Cores' ports (model/geometry.py CHANNELS), the Shield's GPIOs (eyes/eyes.py PORT_GPIO), the eyes'
    calibrated ranges and rests (eyes/calibration.json, #255: lids closed 39, rest 61.4 and 64, open 102; eyes 58..118,
    centred) and the neck's model limits and its 90 neutral (geometry.LIMITS; the neck Core has no program yet)."""
    import macros  # here, not at the top: it imports the model

    table = macros.wiring()
    for row in [
        "| 1 (eyes) | 1 | 3 | L lid | 39..102 | 61.4 |",
        "| 1 (eyes) | 2 | 2 | L eye | 58..118 | 88 |",
        "| 1 (eyes) | 3 | 1 | R lid | 39..102 | 64 |",
        "| 1 (eyes) | 4 | 0 | R eye | 58..118 | 88 |",
        "| 2 (neck) | 1 | 3 | tilt | 30..150 | 90 |",
        "| 2 (neck) | 2 | 2 | jaw | 15..90 | 90 |",
        "| 2 (neck) | 3 | 1 | pan | 50..160 | 90 |",
    ]:
        assert row in table, row


def test_the_coupon_table_is_built_from_the_code():
    """#624: the clearance coupon's pins and magnet pockets (model/printed/coupon.py), each fit by its place from the
    notch: 3 mm pins at 0.10 to 0.40 mm per side, pockets for the 4 mm disc at 0.05 to 0.20 mm."""
    import macros  # here, not at the top: it imports the model

    table = macros.coupon()
    for row in [
        "| 1 | 0.10 mm | 3.20 mm | 0.05 mm | 4.10 mm |",
        "| 4 | 0.25 mm | 3.50 mm | 0.20 mm | 4.40 mm |",
        "| 5 | 0.30 mm | 3.60 mm | | |",
        "| 7 | 0.40 mm | 3.80 mm | | |",
    ]:
        assert row in table, row


def test_the_model_notes_build_the_picture_sizes_and_colours_from_the_code():
    """model/render/pictures.py and blender.py, model/geometry.py SPOOLS, model/mjcf.py VIEW: as Cansin set them."""
    import macros  # here, not at the top: it imports the model

    notes = macros.picture_numbers()
    assert "| gestures |" not in notes  # the viewer plays them (#468)
    for row in [
        "| hero | 800x400 | 8 fps, at most 3 MB |",
        "| favicon | 64x64 | PNG |",
        "| Milky Pink | #F7CED7 | #F7CED7 | #F7CED7 |",
        "| Absolute Black | #000000 | #2B2B2E | #5A5A60 |",
        "| Pure White | #FFFFFF | #FFFFFF | #E8E8E8 |",
        "| lines | | #5F5F5F | |",
        "| background | | transparent | #F7F4EE |",
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


def test_the_behaviour_table_words_every_gesture_and_nothing_else():
    import macros  # here, not at the top: it imports the model
    from noggin.core import GESTURES

    assert set(macros.MECH) == {*GESTURES, "thinking", "rest"}


def test_the_viewer_says_which_claude_code_event_plays_each_gesture():
    """Cansin (#482): under the viewer's bar, one line per gesture clip names the Claude Code event that plays it, from
    the behaviour table's code (the director), never typed in a page."""
    import macros  # here, not at the top: it imports the model
    from model.traces import GESTURES

    moments = macros.moments()
    assert set(moments) == set(GESTURES)
    assert moments["wink"] == "a session starts (SessionStart)"
    assert moments["attention"] == "Claude asks for your permission (Notification permission_prompt)"


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


def test_nothing_public_shows_todays_mech():
    """#640, #649 (docs/adr/0019): today's printed parts derive from the designer's models, so neither the README nor a
    page of the site shows a picture of them: a picture it names is one the site publishes (the next Mech's), it draws
    no viewer (the viewer's page draws the published GLBs alone: site.test.mjs); the site's icon is no render."""
    from model.render import pictures

    texts = {
        "README.md": (ROOT / "README.md").read_text(),
        **{
            str(p.relative_to(ROOT)): p.read_text()
            for p in (ROOT / "docs").rglob("*.md")
            if not {"references", "research", "adr"} & set(p.parts)
        },
        "site/astro.config.mjs": (ROOT / "site" / "astro.config.mjs").read_text(),
    }
    named = {f: re.findall(r"noggin/images/([^\s\"')]+)", t) for f, t in texts.items()}
    assert {f: names for f, names in named.items() if set(names) - set(pictures.published())} == {}
    assert [f for f, t in texts.items() if re.search(r"\{\{ panels \}\}|noggin-viewer|favicon\.png", t)] == []


def test_every_stage_has_a_side_and_an_isometric_panel():
    """Cansin (#470): the panels come from the Stages in the code, each from the side and isometric, one WebP each
    with its lines in one grey for both themes (#489); the hero one WebP too."""
    from model import geometry as g
    from model.render import pictures

    panels = [f"{d.removeprefix('noggin-')}-{v}.webp" for d in g.STAGES for v in ("side", "isometric")]
    following = [f"{d}-{v}.webp" for d in ("next-mech-a", "next-mech-b") for v in ("side", "isometric")]  # #629, #642
    assert sorted(pictures.SITE["views"]) == sorted(
        [*panels, *following, "favicon.png"]
    )  # the site's icon: an eye (#603)
    assert pictures.SITE["hero"] == ["hero.webp"]


def test_the_panels_grid_has_a_column_per_stage_and_a_row_per_view_each_linking_its_full_size():
    """The grid the landing page and Pictures showed until #640 (Cansin, #470): one source, macros.py panels; each
    picture links to its file."""
    import macros

    grid = macros.panels()
    assert re.findall(r"<strong>([^<]+)</strong>", grid) == ["Stage 1", "Stage 2", "Stage 3"]
    assert re.findall(r"<span>([^<]*)</span>", grid) == ["", "Side", "Isometric"]
    links = re.findall(r'<a href="([^"]+)"><img src="([^"]+)"', grid)
    assert len(links) == 6 and all(href == src and src.endswith(".webp") for href, src in links)


def test_the_next_mech_has_its_own_panels():
    """#629: the next Mech's panels in a grid of their own, framed among themselves, one per Base candidate (#642)."""
    import macros

    grid = macros.next_panels()
    assert re.findall(r"<strong>([^<]+)</strong>", grid) == ["Next Mech (a)", "Next Mech (b)"]
    assert re.findall(r'<img src="[^"]+/([^/"]+)"', grid) == [
        "next-mech-a-side.webp",
        "next-mech-a-isometric.webp",
        "next-mech-b-side.webp",
        "next-mech-b-isometric.webp",
    ]


def test_the_site_publishes_the_next_mech_alone():
    """#649 (docs/adr/0019): the site's pictures are the next Mech's panels, its motions (#656, #663) and one per part,
    its viewer the next Mech's GLB, every name starting next-, and no document they draw has a part of today's print."""
    from model import geometry as g
    from model import stages
    from model.render import pictures
    from web import build

    stems = {stages.stem(p.file) for doc in g.NEXT for p in stages.STAGES[doc].parts.values()}
    published = pictures.published()
    # side and isometric per document (a Base candidate each, #642), the sweep (#656), the 7 it plays (#663) and a
    # picture per part
    assert len(published) == 2 * len(g.NEXT) + 1 + 7 + len(stems) == len(set(published))
    assert {"next-mech-a-isometric.webp", "next-eyes-rest.webp", "next-board-tower.webp"} <= {*published}
    assert build.PUBLIC == {"next-mech-a": "next-mech-a.glb", "next-mech-b": "next-mech-b.glb"}
    assert all(n.startswith("next-") for n in [*published, *build.PUBLIC.values()])
    assert {doc for doc, _ in pictures.next_parts().values()} | set(build.PUBLIC) == set(g.NEXT)
    assert [doc for doc in g.NEXT if stages.todays(doc)] == []


def test_the_home_and_the_readme_show_the_next_mech():
    """#661: the site's home shows the next Mech assembled, the latest the site serves, and its eyes sweeping, linking
    to Pictures and the viewer; the README's top shows it assembled too, linking to Pictures: Base candidate (a)'s,
    the first, until Cansin picks one (#642)."""
    from model import geometry as g

    site = "https://yellowpine.com/noggin/"
    picture = f"{site}images/{next(iter(g.NEXT))}-isometric.webp"
    home, readme = (ROOT / "docs" / "index.md").read_text(), (ROOT / "README.md").read_text()
    assert picture in home and "(pictures.md)" in home and f"{site}viewer/" in home
    assert f"{site}images/next-eyes-sweep.webp" in home
    assert picture in readme.split("## Setup")[0] and f"{site}docs/pictures/" in readme


def test_the_hero_is_800x400():
    """Cansin (#278, #293): the one 800x400 hero (shown nowhere until the clean-room Mech, #640)."""
    from model.render import pictures

    assert pictures.HERO_SIZE == (800, 400)


def test_the_viewer_explodes_stage_3_by_the_renders_offsets():
    """Cansin (#482): the viewer's Explode moves each of Stage 3's parts by its sub-assembly's offset in
    model/render/pictures.py EXPLODE, read from there (macros.json), in glTF's metres and Y-up (x, z, -y), and no
    picture of it is rendered."""
    import macros  # here, not at the top: it imports the model
    from model import stages
    from model.render import pictures

    explode = macros.explode()
    assert list(explode) == ["stage3"] and set(explode["stage3"]) == set(stages.STAGES["noggin-stage3"].parts)
    assert explode["stage3"]["top jaw:1"] == pytest.approx([0, 0.095, 0.045])  # the mouth: up and forward
    assert explode["stage3"]["base plate:1"] == [0, 0, 0]
    assert "exploded.jpg" not in sum(pictures.SITE.values(), [])


def test_the_motions_are_every_motion_of_the_pictures_from_the_code():
    """Checks' Blender bins (just blender-bins, #297, #496): the views on every Stage and the next Mech (#629) and the
    hero on stage 3, each with the documents its trajectories bake on; the gestures play in the viewer, not in GIFs
    (#468)."""
    from model.render import pictures

    assert pictures.motions() == [
        {"motion": "views", "stages": "noggin-stage1 noggin-stage2 noggin-stage3 next-mech-a next-mech-b"},
        {"motion": "hero", "stages": "noggin-stage3"},
    ]


def test_the_required_checks_gate_needs_every_job_and_never_skips():
    """`Checks`, the one required check of the workflow (#496): it needs every other job, runs past a failed or skipped
    one (a skipped required check passes) and fails unless each passed or was skipped as unchanged; Changes and Code
    never skip. A draft runs none of it (#414)."""
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "checks.yml").read_text())["jobs"]
    gate = jobs["checks"]
    assert sorted(gate["needs"]) == sorted(j for j in jobs if j != "checks")
    assert gate["if"] == "${{ !cancelled() && !github.event.pull_request.draft }}"
    green = gate["steps"][0]
    assert "re-actors/alls-green@" in green["uses"]
    assert green["with"]["jobs"] == "${{ toJSON(needs) }}"
    assert {j.strip() for j in green["with"]["allowed-skips"].split(",")} == set(gate["needs"]) - {"changes", "code"}


def test_no_real_photos_are_tracked():
    """Cansin, 2026-11-01: real photos of the build stay local (docs/references/build-photos) until staged
    photos exist."""
    globs = ["*.jpg", "*.jpeg", "*.heic", "*.JPG", "*.HEIC"]
    tracked = subprocess.run(["git", "ls-files", *globs], capture_output=True, text=True, check=True).stdout.split()
    assert tracked == [], tracked


def test_a_version_is_released_only_on_its_tag():
    """The footer links a release only from its tagged commit (#372, docs/adr/0017): git describe's X.Y.Z, not
    X.Y.Z-N-gHASH past it, nor a checkout without tags."""
    import macros  # here, not at the top: it imports the model

    assert [macros.released(v) for v in ("0.2.6", "0.2.6-3-gabc1234", "0.0.0-untagged")] == [True, False, False]


def test_the_reports_page_lists_each_sim_report_the_build_adds(tmp_path):
    """/reports/ is the site's own page (site/src/pages/reports.astro, #603); scripts/site_reports.sh copies the sim's
    reports beside it and lists each there, in place of the line saying there are none."""
    (tmp_path / "site" / "dist" / "reports").mkdir(parents=True)
    page = '<main><ul><li data-reports="">No reports in this build.</li></ul></main>'
    (tmp_path / "site" / "dist" / "reports" / "index.html").write_text(page)
    (tmp_path / "model" / "build" / "reports").mkdir(parents=True)
    for f in ("noggin-eyes-report.json", "noggin-eyes-junit.xml"):
        (tmp_path / "model" / "build" / "reports" / f).write_text("{}")
    subprocess.run([ROOT / "scripts" / "site_reports.sh"], cwd=tmp_path, check=True)
    built = tmp_path / "site" / "dist" / "reports"
    assert (built / "index.html").read_text() == (
        '<main><ul><li><a href="noggin-eyes-junit.xml">noggin-eyes-junit.xml</a></li>'
        '<li><a href="noggin-eyes-report.json">noggin-eyes-report.json</a></li></ul></main>'
    )
    assert (built / "noggin-eyes-report.json").read_text() == "{}"
