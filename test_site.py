"""The site's sources (docs/adr/0009, 0013) as GitHub shows them, and the numbers the code gives the site
(macros.py): the built site itself is checked in site/ (site.test.mjs, smoke.pw.mjs). The pictures are none in git
(#226); the site shows the next Mech's (#640, #649, docs/adr/0019)."""

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
    assert [f for f in tracked if os.path.basename(f) in pictures.published()] == []


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
    **{f"docs/build/stage-{n}.md": f"docs/build/stage-{n}/#servos-it-adds" for n in (1, 2, 3)},  # #721
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
    centred) and the next Mech's neck's limits and its 90 neutral (model/stages.py next_neck; the neck Core has no
    program yet)."""
    import macros  # here, not at the top: it imports the model

    table = macros.wiring()
    for row in [
        "| 1 (eyes) | 1 | 3 | L lid | 39..102 | 61.4 |",
        "| 1 (eyes) | 2 | 2 | L eye | 58..118 | 88 |",
        "| 1 (eyes) | 3 | 1 | R lid | 39..102 | 64 |",
        "| 1 (eyes) | 4 | 0 | R eye | 58..118 | 88 |",
    ]:
        assert row in table, row
    neck = re.findall(r"^\| 2 \(neck\) \| (\d) \| (\d) \| (\w+) \| [\d.]+\.\.[\d.]+ \| 90 \|$", table, re.M)
    assert neck == [("1", "3", "tilt"), ("2", "2", "jaw"), ("3", "1", "pan")]


# #806: a printed part's filament in each value of its Colour group's Theme category, each shown in it alone
WHITES = (
    '<span data-skin="morty">PLA Basic Jade White (10100)</span>'
    '<span data-skin="bart">PLA Matte Ivory White (11100)</span>'
)
BONES = (
    '<span data-skeleton="realistic">PETG Basic Dark Beige (30403)</span>'
    '<span data-skeleton="mechanical">PETG Matte Gray (35102)</span>'
)


def test_the_buy_list_names_the_picked_themes_filaments_from_the_model():
    """#806: docs/build/parts.md's buy list names each Theme value's filaments by line, name and code, each Colour
    group's, shown for the value the header's bar picks (model/geometry.py THEMES)."""
    import macros

    assert "<!--{{ filaments }}-->" in (ROOT / "docs" / "build" / "parts.md").read_text()
    items = re.findall(r'<li data-(\w+)="(\w+)">([^<]+)</li>', macros.filaments())
    assert [(c, v) for c, v, _ in items] == [
        ("skeleton", "realistic"), ("skeleton", "mechanical"), ("skin", "morty"), ("skin", "bart")
    ]  # fmt: skip
    assert items[0][2] == (
        "Skeleton realistic: Bones PETG Basic Dark Beige (30403), Joints PETG Matte White (35100), Linkages PETG Basic"
        " Red (30201), Mounts PETG Basic Black (30105)"
    )
    assert "pupils PLA Matte Charcoal (11101)" in items[3][2]


def test_each_stage_guide_lists_what_its_stage_adds_from_the_model():
    """#721: each Stage's guide (docs/build/stage-*.md) lists the parts and the servos its Stage adds to the one before,
    the next Mech's Stages as model/geometry.py STAGES has them (#720): the eye block on its test stand with the eyes
    Core, then the Torso, the neck and the boards with the neck Core (the stand comes off), then the jaw."""
    import macros

    parts, servos = macros.stage_guides()
    assert list(parts) == list(servos) == ["1", "2", "3"]
    for row in [
        "| Core | 1 | bought |",
        f"| L eyeball cap | 1 | eye whites: {WHITES} |",
        "| servo | 4 | bought |",
        "| Shield | 1 | bought |",
        f"| test stand | 1 | Bones: {BONES} |",
    ]:
        assert row in parts["1"], row
    assert "| servo | 2 | bought |" in parts["2"] and f"| torso | 1 | Bones: {BONES} |" in parts["2"]
    assert "It takes off: test stand." in parts["2"] and "test stand" not in parts["3"]
    assert f"| jaw | 1 | Bones: {BONES} |" in parts["3"] and "| servo | 1 | bought |" in parts["3"]
    row = r"^\| (\w+) \| ([\w ]+) \| [\d.]+\.\.[\d.]+ \|$"
    assert [re.findall(row, servos[n], re.M) for n in servos] == [
        [("eyes", "yaw"), ("eyes", "pitch"), ("eyes", "L lid"), ("eyes", "R lid")],
        [("neck", "pan"), ("neck", "tilt")],
        [("neck", "jaw")],
    ]


def test_the_themes_table_names_each_colour_groups_bambu_filament_from_the_model():
    """#805: docs/face-design.md's table of each Theme value's Colour groups and their filaments, from
    model/geometry.py THEMES."""
    import macros

    table = macros.themes()
    for row in [
        "| Skeleton | mechanical | Mounts | board rack | PETG Basic Black (30105) | #000000 |",
        "| Skin | morty | eye whites | L eyeball cap, R eyeball cap | PLA Basic Jade White (10100) | #FFFFFF |",
        "| Skin | morty | hair and pupils |  | PLA Basic Cocoa Brown (10802) | #6F5034 |",
        "| Skin | bart | face |  | PLA Basic Sunflower Yellow (10402) | #FEC600 |",
    ]:
        assert row in table, row
    assert (
        "| Skeleton | realistic | Joints | eyeball core, yaw yoke, bail, pan yoke | PETG Matte White (35100) |" in table
    )


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
    """model/render/pictures.py and blender.py, model/geometry.py THEMES (#805), model/mjcf.py VIEW: as Cansin set
    them."""
    import macros  # here, not at the top: it imports the model

    notes = macros.picture_numbers()
    assert "| gestures |" not in notes  # the viewer plays them (#468)
    for row in [
        "| panels | 800 wide, as tall as the tallest | WebP |",
        "| realistic | Bones | PETG Basic Dark Beige (30403) | #DBC8B6 | #DBC8B6 | #DBC8B6 |",
        "| mechanical | Joints | PETG Basic Black (30105) | #000000 | #2B2B2E | #5A5A60 |",
        "| morty | eye whites | PLA Basic Jade White (10100) | #FFFFFF | #FFFFFF | #E8E8E8 |",
        "| lines | | | | #5F5F5F | |",
        "| background | | | | transparent | #F7F4EE |",
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


STAGE_DOCS = ["next-stage1", "next-stage2", "next-mech-back"]  # #720: Stage 3 the head variant's (Back since #712)
LOOKS = ["", "-mechanical"]  # its Skeleton realistic (as Bones) and mechanical (#704, #805)
SKELETONS = ["realistic", "mechanical"]


def test_every_document_has_a_side_and_an_isometric_panel():
    """Cansin (#470): the panels come from the next Mech's documents in the code, each Stage in each look (#720), from
    the side and isometric, one WebP each with its lines in one grey for both themes (#489)."""
    from model.render import pictures

    panels = [f"{d}{look}-{v}.webp" for look in LOOKS for d in STAGE_DOCS for v in ("side", "isometric")]
    assert [pictures.picture(*p) for p in pictures.PANELS] == panels


def test_the_next_mech_has_its_own_panels():
    """#629, #720: Pictures shows each Stage of the next Mech in every Skeleton, framed among themselves, each Stage's
    name and pictures shown in its own Skeleton alone (#806: the header's Theme bar picks it)."""
    import macros

    grid = macros.next_panels()
    names = [(s, f"Stage {n}") for s in SKELETONS for n in (1, 2, 3)]
    assert re.findall(r'<strong data-skeleton="(\w+)">([^<]+)</strong>', grid) == names
    views = re.findall(r'<a href="[^"]+" data-skeleton="(\w+)"><img src="[^"]+/([^/"]+)"', grid)
    assert views == [
        (s, f"{d}{look}-{v}.webp")
        for s, look in zip(SKELETONS, LOOKS, strict=True)
        for d in STAGE_DOCS
        for v in ("side", "isometric")
    ]


def test_pictures_shows_each_stage_at_explodes_parts_level():
    """#811: Pictures has each Stage with every part apart under its name, in each Skeleton, shown in it alone."""
    import macros

    grid = macros.next_exploded()
    names = [f"Stage {n}, its parts apart" for n in (1, 2, 3)] * 2
    assert re.findall(r"<figcaption>([^<]+)</figcaption>", grid) == names
    cells = re.findall(r'<figure data-skeleton="(\w+)"><a [^>]+><img src="[^"]+/([^/"]+)"', grid)
    assert cells == [
        (skeleton, f"{d}{look}-parts-exploded.webp")
        for skeleton, look in zip(("realistic", "mechanical"), LOOKS, strict=True)
        for d in STAGE_DOCS
    ]
    assert "<!--{{ next_exploded }}-->" in (ROOT / "docs" / "pictures.md").read_text()


def test_the_site_publishes_the_next_mech_alone():
    """#649 (docs/adr/0019): the site's pictures are the next Mech's panels, its motions (#656, #663) and one per part,
    its viewer the next Mech's GLBs, a Stage each in each look (#720), every name starting next-."""
    from model import geometry as g
    from model import stages
    from model.render import pictures
    from web import build

    stems = {stages.stem(p.file) for doc in g.STAGES for p in stages.STAGES[doc].parts.values()}
    published = pictures.published()
    # side and isometric per document, each at the Parts level (#811), the front doors' own two (#739), the sweep (#656)
    # and the 7 it plays (#663), each per Skeleton (#806), and a picture per part
    assert len(published) == 3 * len(g.STAGES) + 2 * (2 + 1 + 7) + len(stems) == len(set(published))
    assert {"next-stage1-isometric.webp", "next-eyes-rest.webp", "next-test-stand.webp"} <= {*published}
    assert {"next-stage1-front.webp", "next-mech-back-side-exploded.webp"} <= {*published}
    assert {"next-stage1-mechanical-front.webp", "next-eyes-mechanical-sweep.webp"} <= {*published}
    assert {"next-stage1-parts-exploded.webp", "next-mech-back-mechanical-parts-exploded.webp"} <= {*published}
    assert build.PUBLIC == {f"{d}{look}": f"{d}{look}.glb" for look in LOOKS for d in STAGE_DOCS}
    assert all(n.startswith("next-") for n in [*published, *build.PUBLIC.values()])
    assert {doc for doc, _ in pictures.next_parts().values()} <= set(build.PUBLIC) == set(g.STAGES)


FRONT = [  # #739: the front doors' three, in order, as Bones (#704): (picture, caption, link)
    ("next-stage1-front.webp", "Stage 1, from the front", "docs/pictures/"),
    ("next-mech-back-isometric.webp", "Stage 3", "viewer/?stage=3"),
    ("next-mech-back-side-exploded.webp", "Stage 3, exploded", "viewer/?stage=3&amp;explode=1"),
]
FRONT_MECHANICAL = [  # #806: the same three in the mechanical Skeleton, its own in the viewer
    ("next-stage1-mechanical-front.webp", "Stage 1, from the front", "docs/pictures/"),
    ("next-mech-back-mechanical-isometric.webp", "Stage 3", "viewer/?stage=3&amp;skeleton=mechanical"),
    (
        "next-mech-back-mechanical-side-exploded.webp",
        "Stage 3, exploded",
        "viewer/?stage=3&amp;skeleton=mechanical&amp;explode=1",
    ),
]


def test_the_home_shows_the_front_doors_three_pictures_from_the_code():
    """#739: the site's home shows Stage 1 from the front, Stage 3 isometric and Stage 3 from the side exploded, side
    by side in that order, each under its caption and linking to Pictures or its Stage in the viewer; no eyes' sweep
    (it is on Pictures). #806: the three in each Skeleton, each shown in its own alone."""
    import macros  # here, not at the top: it imports the model

    site = "https://yellowpine.com/noggin/"
    home, grid = (ROOT / "docs" / "index.md").read_text(), macros.front()
    assert "<!--{{ front }}-->" in home and "next-eyes-sweep" not in home
    assert 'class="noggin-front not-content"' in grid
    cells = re.findall(
        r'<figure data-skeleton="(\w+)"><a href="([^"]+)"><img src="([^"]+)" alt="([^"]+)"[^>]*></a><figcaption>', grid
    )
    assert cells == [
        (s, f"{site}{link}", f"{site}images/{f}", caption)
        for s, front in zip(SKELETONS, (FRONT, FRONT_MECHANICAL), strict=True)
        for f, caption, link in front
    ]


def test_the_readmes_top_shows_the_front_doors_three_pictures_at_one_height_in_one_centred_row():
    """#739: the README's top shows the home's three, in order, each linking where the home's does under its caption,
    at one img height (GitHub strips CSS, #716), in one centred one-row table."""
    site = "https://yellowpine.com/noggin/"
    top = (ROOT / "README.md").read_text().split("## Setup")[0]
    row = re.search(r'<div align="center"><table><tr>(.*?)</tr></table></div>', top, re.S)
    assert row
    cells = re.findall(
        r'<td align="center"><a href="([^"]+)"><img src="([^"]+)" height="(\d+)" alt="([^"]+)"></a>'
        r"<br><sub>([^<]+)</sub>",
        row[1],
    )
    assert [(link, src, alt) for link, src, _, alt, _ in cells] == [
        (f"{site}{link}", f"{site}images/{f}", caption) for f, caption, link in FRONT
    ]
    assert [c for *_, c in cells] == [c for _, c, _ in FRONT]
    assert len({h for _, _, h, _, _ in cells}) == 1
    assert "next-eyes-sweep" not in top


def test_the_viewer_switches_the_stage_and_the_skeleton_and_marks_a_stage_that_fails_a_gate(tmp_path, monkeypatch):
    """#720: the viewer's Stage switch has a button per Stage, 1 to 3, each its GLB as Bones, and each Skeleton (#805)
    its GLB's suffix, the header's Theme bar picking one (#806). #705: with just sim's ranking of today's head
    variants, the Stage that is one is marked with what its mechanical document fails, the one physics runs on (#809),
    unmarked else (a ranking of other documents: main's reports before the variants' first sim)."""
    import json

    import macros

    monkeypatch.setattr(macros, "RANKING", tmp_path / "next-mech-ranking.json")
    unranked = macros.stage_switch()
    assert unranked["buttons"] == [{"glb": d, "label": f"{n}"} for n, d in enumerate(STAGE_DOCS, 1)]
    assert unranked["skeletons"] == {"realistic": "", "mechanical": "-mechanical"}
    fails = {"next-mech-back-mechanical": ["head size", "tilt loop"]}
    ranking = {"order": list(fails), "variants": {d: {"fails": f} for d, f in fails.items()}}
    macros.RANKING.write_text(json.dumps(ranking))
    assert [b["label"] for b in macros.stage_switch()["buttons"]] == ["1", "2", "3: head size, tilt loop"]
    macros.RANKING.write_text(json.dumps({"order": ["next-mech-a"], "variants": {"next-mech-a": {"fails": []}}}))
    assert macros.stage_switch() == unranked


@pytest.mark.parametrize(
    ("workflow", "runs"),
    [("checks.yml", "${{ !cancelled() }}"), ("pr-gate.yml", "${{ !cancelled() && !github.event.pull_request.draft }}")],
)
def test_the_checks_gate_needs_every_job_and_never_skips(workflow, runs):
    """`Checks`, the one required check of a PR's gate and the one main's Deploy and Release wait on (#496, #722, #795):
    it needs every other job of its workflow but the Deploy after it, runs past a failed or skipped one (a skipped
    required check passes) and fails unless each passed or, conditioned on its inputs, was skipped as unchanged. A draft
    runs none of it (#414)."""
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / workflow).read_text())["jobs"]
    gate = jobs["checks"]
    assert sorted(gate["needs"]) == sorted(j for j in jobs if j not in ("checks", "deploy"))
    assert gate["if"] == runs
    green = gate["steps"][0]
    assert "re-actors/alls-green@" in green["uses"]
    assert green["with"]["jobs"] == "${{ toJSON(needs) }}"
    skips = {j.strip() for j in green["with"].get("allowed-skips", "").split(",") if j.strip()}
    unchanged = {j for j in gate["needs"] if "needs.changes.outputs" in jobs[j].get("if", "")}
    unchanged |= {j for j in gate["needs"] if "if" not in jobs[j] and set(jobs[j].get("needs", [])) & unchanged}
    assert skips == unchanged  # and a job with no `if` skips with such a need: Blender with Render (#780)


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
    for f in ("next-mech-back-sim.json", "next-mech-back-junit.xml"):
        (tmp_path / "model" / "build" / "reports" / f).write_text("{}")
    subprocess.run([ROOT / "scripts" / "site_reports.sh"], cwd=tmp_path, check=True)
    built = tmp_path / "site" / "dist" / "reports"
    assert (built / "index.html").read_text() == (
        '<main><ul><li><a href="next-mech-back-junit.xml">next-mech-back-junit.xml</a></li>'
        '<li><a href="next-mech-back-sim.json">next-mech-back-sim.json</a></li></ul></main>'
    )
    assert (built / "next-mech-back-sim.json").read_text() == "{}"
