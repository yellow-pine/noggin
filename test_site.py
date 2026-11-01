"""The site's sources (docs/adr/0009, 0013) as GitHub shows them, and the numbers the code gives the site
(macros.py): the built site itself is checked in site/ (site.test.mjs, smoke.pw.mjs). The README's pictures are built in
CI too (#226): none in git, every one a site URL the render job builds."""

import json
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
    workflows = list((ROOT / ".github" / "workflows").glob("*.yml"))
    assert [
        p.name for p in workflows if f"| {yaml.safe_load(p.read_text())['name']} | `{p.name}` |" not in readme
    ] == []
    assert "scripts/setup.sh" not in readme and "## Gestures" not in readme


@pytest.mark.parametrize("doc", ["docs/index.md", "docs/pictures.md"])
def test_the_gesture_grid_shows_every_gesture_the_model_plays(doc):
    """The grid stays plain HTML, so GitHub shows the GIFs too (#293); it lists model/traces.py's gestures, in order."""
    from model import traces

    grid = re.search(r'<div class="grid gestures">(.*?)</div>', (ROOT / doc).read_text(), re.S)
    assert grid and re.findall(r'images/(\w+)\.gif" alt="\1"', grid[1]) == list(traces.GESTURES)


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
    for row in [
        "| gestures | 400x300 | 400 wide, 8 fps, 64 colours, at most 1 MB |",
        "| hero | 800x400 | 800 wide, 8 fps, 64 colours, at most 3 MB |",
        "| Milky Pink | #F7CED7 | #F7CED7 | #F7CED7 |",
        "| Absolute Black | #000000 | #2B2B2E | #5A5A60 |",
        "| Pure White | #FFFFFF | #FFFFFF | #E8E8E8 |",
        "| background | | #F7F4EE | #F7F4EE |",
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


def test_the_hero_is_800x400_and_leads_the_readme():
    """Cansin (#278, #293): the one 800x400 hero, at its size and centred, leads the README (GitHub drops CSS, so a
    centred HTML paragraph, its width alone: GitHub's CSS would squash a fixed height on a phone); on the site it shows
    in a figure at its size (site.test.mjs)."""
    from model.render import pictures

    hero = "https://yellowpine.com/noggin/images/hero.gif"
    assert pictures.HERO_SIZE == (800, 400)
    readme = (ROOT / "README.md").read_text()
    assert re.search(rf'^<p align="center"><img src="{hero}" width="800" alt="[^"]+"></p>$', readme, re.M)
    assert readme.index(hero) < readme.index("## ")


def test_the_motions_list_is_every_motion_of_the_pictures_from_the_code():
    """`make pictures-list` (Site Checks' motions job, #297): the Stage views on every Stage, the hero on
    stage 3 and each gesture of model/traces.py on stage 1, each with the Stages its trajectories bake on."""
    from model import traces

    out = subprocess.run(["make", "-s", "pictures-list"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    assert json.loads(out) == [
        {"motion": "views", "stages": "noggin-stage1 noggin-stage2 noggin-stage3"},
        {"motion": "hero", "stages": "noggin-stage3"},
        *({"motion": g, "stages": "noggin-stage1"} for g in traces.GESTURES),
    ]


def test_site_checks_render_one_job_per_motion_and_names_none():
    """`render` fans out over the motions job's list (#297): a new gesture needs no workflow edit."""
    from model.render import pictures

    text = (ROOT / ".github" / "workflows" / "site-checks.yml").read_text()
    jobs = yaml.safe_load(text)["jobs"]
    assert "make -s pictures-list" in jobs["motions"]["steps"][-1]["run"]
    assert jobs["render"]["strategy"]["matrix"] == {"include": "${{ fromJSON(needs.motions.outputs.list) }}"}
    assert jobs["render"]["name"] == "render (${{ matrix.motion }})"
    assert [m for m in pictures.SITE if re.search(rf"\b{m}\b", text)] == []


def test_site_checks_looks_up_the_keys_the_blender_jobs_save():
    """A PR whose pictures and viewer are cached skips both Blender jobs and their image pulls (#386): `changes`
    looks up, and `site` restores, the keys render's runners and viewer save, else every PR run would go cold."""
    jobs = yaml.safe_load((ROOT / ".github" / "workflows" / "site-checks.yml").read_text())["jobs"]

    def key(job: str, id_: str) -> str:
        (step,) = [s for s in jobs[job]["steps"] if s.get("id") == id_]
        return step["with"]["key"]

    def inputs(k: str) -> str:
        return re.search(r"hashFiles\(.*\)", k)[0]

    render = inputs(key("render", "frames"))  # a key per motion over the same inputs
    assert key("changes", "pictures") == key("site", "images") == f"pictures-${{{{ {render} }}}}"
    assert key("changes", "viewer") == key("site", "viewer") == key("viewer", "viewer")


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
    job = yaml.safe_load((ROOT / ".github" / "workflows" / "site-checks.yml").read_text())["jobs"]["pictures"]
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
