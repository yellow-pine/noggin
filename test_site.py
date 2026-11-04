"""The site's sources (docs/adr/0009, 0013) as GitHub shows them, and the numbers the code gives the site
(macros.py): the built site itself is checked in site/ (site.test.mjs, smoke.pw.mjs). The pictures are none in git
(#226); the site shows the Mech's (#640, #649, docs/adr/0019)."""

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
    """Both Cores' ports (model/geometry.py CHANNELS), the Shield's GPIOs (eyes/eyes.py PORT_GPIO), the eye gimbal's
    calibrated ranges and rests (eyes/calibration.json, the model's nominals until a Stage 1 is calibrated, #896: lids
    closed 69, rest 90, open 105; yaw 65..115 and pitch 59.6..120.4, centred) and the Mech's neck's limits and its
    90 neutral (model/stages.py neck_sub; the neck Core has no program yet)."""
    import macros  # here, not at the top: it imports the model

    table = macros.wiring()
    for row in [
        "| 1 (eyes) | 1 | 3 | L lid | 69..105 | 90 |",
        "| 1 (eyes) | 2 | 2 | yaw | 65..115 | 90 |",
        "| 1 (eyes) | 3 | 1 | R lid | 69..105 | 90 |",
        "| 1 (eyes) | 4 | 0 | pitch | 59.6..120.4 | 90 |",
    ]:
        assert row in table, row
    neck = re.findall(r"^\| 2 \(neck\) \| (\d) \| (\d) \| (\w+) \| [\d.]+\.\.[\d.]+ \| 90 \|$", table, re.M)
    assert neck == [("1", "3", "tilt"), ("2", "2", "jaw"), ("3", "1", "pan")]


# #806, #819: a printed part's filament in each Preset, shown for the Presets that print it alone
WHITES = (
    '<span data-presets="default-build">PLA Pure Pure White (17100)</span>'
    '<span data-presets="morty">PLA Basic Jade White (10100)</span>'
    '<span data-presets="bart">PLA Matte Ivory White (11100)</span>'
)
BONES = (
    '<span data-presets="default-build">PETG Basic Black (30105)</span>'
    '<span data-presets="morty bart">PETG Basic Dark Beige (30403)</span>'
)


def test_the_buy_list_names_the_picked_presets_filaments_from_the_model():
    """#806, #819: docs/build/parts.md's buy list names each Preset's filaments by line, name and code, with the Colour
    groups each prints, shown for the Preset the header's bar picks (model/geometry.py THEMES and PRESETS)."""
    import macros

    assert "<!--{{ filaments }}-->" in (ROOT / "docs" / "build" / "parts.md").read_text()
    items = re.findall(r'<li data-presets="([\w-]+)">([^<]+)</li>', macros.filaments())
    assert [p for p, _ in items] == ["default-build", "morty", "bart"]
    assert items[0][1] == (
        "Default build: Bones, Joints, Linkages, Mounts PETG Basic Black (30105); face PLA Pure Milky Pink (17200);"
        " hair, pupils PLA Pure Absolute Black (17101); clothes, eye whites PLA Pure Pure White (17100); accessories"
        " PLA Pure Apricot (17300)"
    )
    assert (
        "Bones PETG Basic Dark Beige (30403)" in items[1][1] and "pupils, accessories PLA Matte Charcoal" in items[2][1]
    )


def test_each_stage_guide_lists_what_its_stage_adds_from_the_model():
    """#721: each Stage's guide (docs/build/stage-*.md) lists the parts and the servos its Stage adds to the one before,
    the Mech's Stages as model/geometry.py STAGES has them (#720): the eye block on its test stand with the eyes
    Core, then the Torso, the neck and the boards with the neck Core in the Torso (the stand comes off, #838), then the
    jaw."""
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
    mounts = '<span data-presets="default-build morty bart">PETG Basic Black (30105)</span>'  # the pedestal (#838)
    assert "| servo | 2 | bought |" in parts["2"] and f"| torso | 1 | Mounts: {mounts} |" in parts["2"]
    assert "It takes off: test stand." in parts["2"] and "test stand" not in parts["3"]
    assert f"| jaw | 1 | Bones: {BONES} |" in parts["3"] and "| servo | 1 | bought |" in parts["3"]
    row = r"^\| (\w+) \| ([\w ]+) \| [\d.]+\.\.[\d.]+ \|$"
    assert [re.findall(row, servos[n], re.M) for n in servos] == [
        [("eyes", "yaw"), ("eyes", "pitch"), ("eyes", "L lid"), ("eyes", "R lid")],
        [("neck", "pan"), ("neck", "tilt")],
        [("neck", "jaw")],
    ]


def test_the_palettes_table_names_each_colour_groups_bambu_filament_from_the_model():
    """#805, #819: docs/face-design.md's table of each Palette's Colour groups and their filaments, from
    model/geometry.py THEMES."""
    import macros

    table = macros.themes()
    for row in [
        "| Skeleton | robot | Mounts | torso, torso lid, cranium tray | PETG Basic Black (30105) | #000000 |",
        "| Skeleton | black | Mounts | torso, torso lid, cranium tray | PETG Basic Black (30105) | #000000 |",
        "| Skin | morty | eye whites | L eyeball cap, R eyeball cap, cansin L pupil plug, cansin R pupil plug, cansin"
        " teeth, bart L pupil plug, bart R pupil plug | PLA Basic Jade White (10100) | #FFFFFF |",
        # Morty's Shells (#665), Cansin's (#813), Bart's (#807)
        "| Skin | morty | hair | morty hair, cansin hair, cansin L brow, cansin R brow, bart hair | PLA Basic Cocoa"
        " Brown (10802) | #6F5034 |",
        "| Skin | bart | clothes | morty shirt front, morty shirt back, cansin shirt front, cansin shirt back, bart"
        " shirt front, bart shirt back | PLA Matte Scarlet Red (11200) | #DE4343 |",
        "| Skin | default | accessories | cansin sunglasses | PLA Pure Apricot (17300) | #FFB673 |",
    ]:
        assert row in table, row
    assert (
        "| Skeleton | anatomical | Joints | eyeball core, yaw yoke, bail, pan yoke | PETG Matte White (35100) |"
        in table
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
    """model/render/pictures.py and blender.py, model/geometry.py THEMES (#805, #819), model/mjcf.py VIEW: as Cansin set
    them."""
    import macros  # here, not at the top: it imports the model

    notes = macros.picture_numbers()
    assert "| gestures |" not in notes  # the viewer plays them (#468)
    for row in [
        "| the front doors and the posters | 800 wide, as tall as the tallest | WebP |",
        "| anatomical | Bones | PETG Basic Dark Beige (30403) | #DBC8B6 | #DBC8B6 | #DBC8B6 |",
        "| robot | Joints | PETG Basic Black (30105) | #000000 | #424245 | #5A5A60 |",
        "| black | Bones | PETG Basic Black (30105) | #000000 | #424245 | #5A5A60 |",
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
    page of the site shows a picture of them: a picture it names is one the site publishes (the Mech's), it draws
    no viewer by hand (the viewer's page and macros.py's draw the published GLBs alone: site.test.mjs); the site's icon
    is no render."""
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


STAGE_DOCS = ["stage1", "stage2", "mech-back"]  # #720: Stage 3 the head variant's (Back since #712)
SHAPES = ["", "-mechanical"]  # each document in its Skeleton shape realistic (as Bones) and mechanical (#704, #805)


def test_render_makes_six_stills_the_readmes_three_and_a_poster_per_stage():
    """#898: Blender renders the README's three (the front doors, #739) and one poster per Stage, isometric in the
    default Preset, and nothing else; the viewer stands in for every other picture. The GLBs: a Stage each in each
    Skeleton shape (#720), Stage 3 bare too (#876)."""
    from model import geometry as g
    from model.render import pictures
    from web import build

    assert pictures.published() == [
        "stage1-front.webp",
        "mech-back-bare-isometric.webp",
        "mech-back-side-exploded.webp",
        "stage1-isometric.webp",
        "stage2-isometric.webp",
        "mech-back-isometric.webp",
    ]
    assert pictures.DRAWN["stage1"] == ("stage1-mechanical", "Default build")  # the default
    assert pictures.DRAWN["mech-back-bart"] == ("mech-back-bart", "Bart")  # in his own Skin (#807)
    bare = {f"mech-back{s}-bare": f"mech-back{s}-bare.glb" for s in SHAPES}  # Stage 3 Skinless (#876)
    dressed = {f"mech-back{s}-{k}": f"mech-back{s}-{k}.glb" for s in SHAPES for k in ("bart", "cansin")}
    assert build.PUBLIC == {f"{d}{s}": f"{d}{s}.glb" for s in SHAPES for d in STAGE_DOCS} | bare | dressed
    assert set(map(build.document, build.PUBLIC)) == {*g.STAGES, *g.DRESSED}


def embeds(html):
    """(data-stage, data-link, caption) of each viewer embed in a grid of macros.py viewers."""
    pattern = r'<figure[^>]*><div class="noggin-viewer" data-stage="([^"]+)" data-link="([^"]*)">.*?<figcaption>([^<]+)'
    return re.findall(pattern, html)


def test_pictures_shows_each_stage_from_the_side_isometric_and_apart_in_the_viewer():
    """#898: the panels and Explode's Parts level (#811) are viewer embeds: each Stage from the side, isometric and
    with every part apart, in the Preset the header's bar picks (the viewer follows it, #819)."""
    import macros

    how = (("view=side", ", from the side"), ("view=isometric", ""), ("explode=2", ", its parts apart"))
    cells = embeds(macros.stage_views())
    assert cells == [(doc, link, f"Stage {n}{label}") for n, doc in enumerate(STAGE_DOCS, 1) for link, label in how]
    assert "<!--{{ stage_views }}-->" in (ROOT / "docs" / "pictures.md").read_text()


def test_pictures_shows_each_part_alone_in_the_viewer():
    """#898: each part's picture is a viewer embed of the first Stage it is in, that part at full look and the rest
    ghosted (part=), under its name; a part of one Skeleton shape alone (the skull's bones) shown for its Presets."""
    import macros

    grid = macros.part_pictures()
    cells = {caption: (stage, link) for stage, link, caption in embeds(grid)}
    assert cells["test stand"] == ("stage1", "part=test+stand&view=isometric")
    assert cells["jaw"] == ("mech-back", "part=jaw&view=isometric")
    assert cells["Core"] == ("stage1", "part=Core+1&view=isometric")
    assert len(cells) == len(re.findall("<figure", grid)) > 40
    figures = re.findall(r'<figure(?: data-presets="([\w -]+)")?><div[^>]+part=([^&"]+)', grid)
    marks = {part: mark for mark, part in figures}
    assert marks["atlas"] == "morty bart" and marks["jaw"] == marks["Core+1"] == ""


# #739: the front doors' three, in order, in the default Preset, the Default build (#819), bare of its Skin (#843):
# (picture, caption, link), each its Stage in the viewer (#839)
FRONT = [
    ("stage1-front.webp", "Stage 1, from the front", "viewer/?stage=1"),
    ("mech-back-bare-isometric.webp", "Stage 3", "viewer/?stage=3"),
    ("mech-back-side-exploded.webp", "Stage 3, exploded", "viewer/?stage=3&amp;explode=1"),
]


def test_the_home_shows_the_front_doors_three_pictures_from_the_code():
    """#739: the site's home shows Stage 1 from the front, Stage 3 isometric and Stage 3 from the side exploded, side
    by side in that order, each under its caption and linking to its Stage in the viewer (#839); no motion. #843: the
    one three, whichever Preset is picked."""
    import macros  # here, not at the top: it imports the model

    site = "https://yellowpine.com/noggin/"
    home, grid = (ROOT / "docs" / "index.md").read_text(), macros.front()
    assert "<!--{{ front }}-->" in home and "eyes-sweep" not in home
    assert 'class="noggin-front not-content"' in grid
    cells = re.findall(
        r'<figure><a href="([^"]+)"><img src="([^"]+)" alt="([^"]+)"[^>]*></a><figcaption>',
        grid,
    )
    assert cells == [(f"{site}{link}", f"{site}images/{f}", caption) for f, caption, link in FRONT]


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
    assert "eyes-sweep" not in top


def test_the_viewer_switches_the_stage_and_the_skeleton_and_marks_a_stage_that_fails_a_gate(tmp_path, monkeypatch):
    """#720: the viewer's Stage switch has a button per Stage, 1 to 3, each its GLB as Bones, and each Skeleton shape
    (#805, #819) its GLB's suffix, the Preset or the viewer's own mix picking one. #705: with just sim's ranking of
    today's head variants, the Stage that is one is marked with what its mechanical document fails, the one physics
    runs on (#809), unmarked else (a ranking of other documents: main's reports before the variants' first sim)."""
    import json

    import macros

    monkeypatch.setattr(macros, "RANKING", tmp_path / "mech-ranking.json")
    unranked = macros.stage_switch()
    assert unranked["buttons"] == [{"glb": d, "label": f"{n}"} for n, d in enumerate(STAGE_DOCS, 1)]
    assert unranked["skeletons"] == {"realistic": "", "mechanical": "-mechanical"}
    # #876, #813, #807: where Stage 3 has its GLB
    assert unranked["skins"] == {"none": "-bare", "cansin": "-cansin", "bart": "-bart"}
    fails = {"mech-back-mechanical": ["head size", "tilt loop"]}
    ranking = {"order": list(fails), "variants": {d: {"fails": f} for d, f in fails.items()}}
    macros.RANKING.write_text(json.dumps(ranking))
    assert [b["label"] for b in macros.stage_switch()["buttons"]] == ["1", "2", "3: head size, tilt loop"]
    macros.RANKING.write_text(json.dumps({"order": ["mech-a"], "variants": {"mech-a": {"fails": []}}}))
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
    for f in ("mech-back-sim.json", "mech-back-junit.xml"):
        (tmp_path / "model" / "build" / "reports" / f).write_text("{}")
    subprocess.run([ROOT / "scripts" / "site_reports.sh"], cwd=tmp_path, check=True)
    built = tmp_path / "site" / "dist" / "reports"
    assert (built / "index.html").read_text() == (
        '<main><ul><li><a href="mech-back-junit.xml">mech-back-junit.xml</a></li>'
        '<li><a href="mech-back-sim.json">mech-back-sim.json</a></li></ul></main>'
    )
    assert (built / "mech-back-sim.json").read_text() == "{}"
