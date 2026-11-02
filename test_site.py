"""The site's sources (docs/adr/0009, 0013) as GitHub shows them, and the numbers the code gives the site
(macros.py): the built site itself is checked in site/ (site.test.mjs, smoke.pw.mjs). The README's pictures are built in
CI too (#226): none in git, every one a site URL the render job builds."""

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
    """reactions/director.py and install_hooks.py say which event plays what, eyes/eyes.py how often it blinks."""
    import macros  # here, not at the top: it imports the model

    table = macros.behaviour()
    for row in [
        "| SessionStart | wink (hello) |",
        "| UserPromptSubmit | thinking: lids low, gaze averted, micro-saccades, a blink every 5-8 s |",
        "| Stop | eureka, sized by how long the turn took: under 20 s small, under 3 min normal, longer big |",
        "| Notification permission_prompt | attention: half lids, a real left-right scan |",
        "| Notification idle_prompt | bored: drooping lids, heavy blinks, one long closure |",
        "| StopFailure | wince |",
        "| SessionEnd | back to rest (also when the last turn ends 15 min after its prompt, whatever Triggers"
        " arrive) |",
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
    "docs/ci-cd.md": "docs/ci-cd/#workflows",
}


@pytest.mark.parametrize("doc", SITE_TABLES)
def test_github_links_to_the_site_for_the_tables_built_from_the_code(doc):
    """GitHub hides the macros: its link lands on the site's page at the heading of the table built there (that the
    heading is there, site.test.mjs checks on the built site)."""
    page, anchor = SITE_TABLES[doc].split("#")
    assert f"(https://yellowpine.com/noggin/{page}#{anchor})" in github(doc)


def test_the_readme_is_for_contributors():
    """#279: the pitch, the hero, the call-out to the site, setup, checks, CI/CD, contributing, credits, licence;
    building and using the Mech are the site's."""
    readme = github("README.md")
    assert (
        "[Docs, build guide and live 3D viewer → https://yellowpine.com/noggin](https://yellowpine.com/noggin/)"
        in readme
    )
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


def test_the_model_notes_build_the_picture_sizes_and_colours_from_the_code():
    """model/render/pictures.py and blender.py, model/geometry.py SPOOLS, model/mjcf.py VIEW: as Cansin set them."""
    import macros  # here, not at the top: it imports the model

    notes = macros.picture_numbers()
    assert "| gestures |" not in notes  # the viewer plays them (#468)
    for row in [
        "| hero | 800x400 | 8 fps, at most 3 MB |",
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


def test_every_picture_ci_builds_is_shown_from_the_site():
    """The README's and the docs' pictures (the badges aside; Markdown images or the figures' <img>s, and the Stage
    panels' grid, macros.py) are the site's absolute /images URLs of files in the pictures manifest, and each of those
    is shown somewhere."""
    import macros  # here, not at the top: it imports the model, as pictures does
    from model.render import pictures

    texts = [
        (ROOT / "README.md").read_text(),
        *(p.read_text() for p in (ROOT / "docs").rglob("*.md") if not {"references", "research"} & set(p.parts)),
        macros.panels(),
    ]
    urls = {
        u.split("#")[0]
        for t in texts
        for u in re.findall(r"!\[[^\]]*\]\(([^)\s]+)", t) + re.findall(r'<img src="([^"]+)"', t)
        if u.startswith("http") and not u.startswith("https://img.shields.io/")
    }
    site = "https://yellowpine.com/noggin/images/"
    assert [u for u in urls if not u.startswith(site)] == []
    assert sorted(u.removeprefix(site) for u in urls) == sorted(sum(pictures.SITE.values(), []))


def test_every_stage_has_a_side_and_an_isometric_panel():
    """Cansin (#470): the panels come from the Stages in the code, each from the side and isometric, one WebP each
    with its lines in one grey for both themes (#489); the hero one WebP too."""
    from model import geometry as g
    from model.render import pictures

    panels = [f"{d.removeprefix('noggin-')}-{v}.webp" for d in g.STAGES for v in ("side", "isometric")]
    assert sorted(pictures.SITE["views"]) == sorted(panels)
    assert pictures.SITE["hero"] == ["hero.webp"]


def test_the_panels_grid_has_a_column_per_stage_and_a_row_per_view_each_linking_its_full_size():
    """The landing page's and Pictures' grid (Cansin, #470): one source, macros.py panels; each picture links to its
    file."""
    import macros

    grid = macros.panels()
    assert re.findall(r"<strong>([^<]+)</strong>", grid) == ["Stage 1", "Stage 2", "Stage 3"]
    assert re.findall(r"<span>([^<]*)</span>", grid) == ["", "Side", "Isometric"]
    links = re.findall(r'<a href="([^"]+)"><img src="([^"]+)"', grid)
    assert len(links) == 6 and all(href == src and src.endswith(".webp") for href, src in links)
    for page in ("index.md", "pictures.md"):
        assert "<!--{{ panels }}-->" in (ROOT / "docs" / page).read_text()


def test_the_hero_is_800x400_and_leads_the_readme():
    """Cansin (#278, #293): the one 800x400 hero, at its size and centred, leads the README (GitHub drops CSS, so a
    centred HTML paragraph, its width alone: GitHub's CSS would squash a fixed height on a phone), linking to the
    viewer (#468); on the site it shows in a figure at its size (site.test.mjs)."""
    from model.render import pictures

    hero = "https://yellowpine.com/noggin/images/hero.webp"
    assert pictures.HERO_SIZE == (800, 400)
    readme = (ROOT / "README.md").read_text()
    viewer = "https://yellowpine.com/noggin/viewer/"
    assert re.search(
        rf'^<p align="center"><a href="{viewer}"><img src="{hero}" width="800" alt="[^"]+"></a></p>$', readme, re.M
    )
    assert readme.index(hero) < readme.index("## ")


def test_the_viewer_explodes_stage_3_by_the_renders_offsets():
    """Cansin (#482): the viewer's Explode moves each of Stage 3's parts by its sub-assembly's offset in
    model/render/pictures.py EXPLODE, read from there (macros.json), in glTF's metres and Y-up (x, z, -y); Pictures
    and the Stage 3 build guide link to it, and no picture of it is rendered."""
    import macros  # here, not at the top: it imports the model
    from model import stages
    from model.render import pictures

    explode = macros.explode()
    assert list(explode) == ["stage3"] and set(explode["stage3"]) == set(stages.STAGES["noggin-stage3"].parts)
    assert explode["stage3"]["top jaw:1"] == pytest.approx([0, 0.095, 0.045])  # the mouth: up and forward
    assert explode["stage3"]["base plate:1"] == [0, 0, 0]
    link = "https://yellowpine.com/noggin/viewer/?stage=3&explode=1"
    assert all(link in (ROOT / "docs" / d).read_text() for d in ("pictures.md", "build/stage-3.md"))
    assert "exploded.jpg" not in sum(pictures.SITE.values(), [])


def test_the_motions_are_every_motion_of_the_pictures_from_the_code():
    """Checks' Blender bins (make blender-bins, #297, #496): the Stage views on every Stage and the hero on stage 3,
    each with the Stages its trajectories bake on; the gestures play in the viewer, not in GIFs (#468)."""
    from model.render import pictures

    assert pictures.motions() == [
        {"motion": "views", "stages": "noggin-stage1 noggin-stage2 noggin-stage3"},
        {"motion": "hero", "stages": "noggin-stage3"},
    ]


def test_the_blender_bins_name_no_motion():
    """A new motion needs no workflow edit (#297); the model shards' hero unit is the hero's collision sweep."""
    from model.render import pictures

    text = yaml.safe_dump(
        yaml.safe_load((ROOT / ".github" / "workflows" / "checks.yml").read_text())["jobs"]["blender"]
    )
    assert [m for m in pictures.SITE if re.search(rf"\b{m}\b", text)] == []


def test_checks_pictures_key_is_the_one_changes_looks_up():
    """A PR whose pictures are cached renders nothing (#386): the pictures- key `changes` looks up is the one the gate
    restores and saves (the one hash `changes` makes, #469), else every PR run would go cold."""
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "checks.yml").read_text())["jobs"]

    def key(job: str, id_: str) -> str:
        (step,) = [s for s in jobs[job]["steps"] if s.get("id") == id_]
        return step["with"]["key"]

    assert jobs["changes"]["outputs"]["pictures-hash"] == "${{ steps.inputs.outputs.pictures }}"
    assert key("changes", "pictures") == "pictures-${{ steps.inputs.outputs.pictures }}"
    assert key("checks", "images") == "pictures-${{ needs.changes.outputs.pictures-hash }}"


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


def test_a_version_is_released_once_its_changelog_section_is_written(tmp_path):
    """release-please's headings: the first release's bare, each later one's linking its compare (#372)."""
    import macros  # here, not at the top: it imports the model

    changelog = tmp_path / "CHANGELOG.md"
    assert not macros.released("0.1.0", changelog)
    changelog.write_text(
        "# Changelog\n\n## [0.2.0](https://github.com/o/r/compare/v0.1.0...v0.2.0) (2026-12-01)\n\n"
        "## 0.1.0 (2026-11-02)\n"
    )
    assert [macros.released(v, changelog) for v in ("0.1.0", "0.2.0", "0.2.1", "0.1")] == [True, True, False, False]
