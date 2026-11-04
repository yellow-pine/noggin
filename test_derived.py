"""Derived, not listed (docs/adr/0011): a workflow, the justfile or a doc never spells out a list the code holds (the
gestures, the servos, the documents the model simulates). A list is two or more of one list's names in a workflow or
the justfile, or three on one line of Markdown, where two is prose ("pan and tilt"). A name joined to another word by a
hyphen ("pan-tilt") is not the name."""

import json
import re
import subprocess
from pathlib import Path, PurePosixPath

import pytest
import yaml

from model import trajectories
from model.stages import DOCS
from noggin.core import CORES, GESTURES
from scripts.inputs import inputs

ROOT = Path(__file__).resolve().parent
LISTS = {"gesture": GESTURES, "servo": [s for ports in CORES.values() for s in ports.values()], "document": list(DOCS)}
HISTORY = ("docs/research/", "docs/adr/")  # what was decided or found then, in its own words
ALLOWED = {  # (file, list): why it spells them
    ("GLOSSARY.md", "servo"): "the Servo entry defines the names",
    ("docs/how-it-works.md", "servo"): "the diagram's Core 2 label, drawn as GitHub shows it",
    ("docs/build/wiring.md", "servo"): "the second Core's ports: #306 fills them from CHANNELS",
}


def spelled_lists():
    """{(file, list): [where]} for every list a workflow, the justfile or a doc spells out."""
    files = subprocess.run(
        ["git", "ls-files", "*.md", ".github/*.yml", "justfile"], cwd=ROOT, capture_output=True, text=True
    )
    found = {}
    for f in files.stdout.split():
        if f.startswith(HISTORY):
            continue
        text = (ROOT / f).read_text()
        chunks, min_hits = (enumerate(text.splitlines(), 1), 3) if f.endswith(".md") else ([("", text)], 2)
        for n, unit in chunks:
            for kind, names in LISTS.items():
                hit = sorted(m for m in names if re.search(rf"(?<![\w-]){re.escape(m)}(?![\w-])", unit))
                if len(hit) >= min_hits:
                    found.setdefault((f, kind), []).append(f"{f}:{n} {', '.join(hit)}")
    return found


def test_nothing_spells_out_a_list_the_code_holds():
    found = spelled_lists()
    assert [w for key, where in found.items() if key not in ALLOWED for w in where] == []
    assert [key for key in ALLOWED if key not in found] == [], "spelled out no more: drop it from ALLOWED"


MODEL_TESTS = subprocess.run(
    ["git", "grep", "-lE", r"pytest\.mark\.model([^_[:alnum:]]|$)", "--", "*.py"],
    cwd=ROOT,
    capture_output=True,
    text=True,
).stdout.split()
# What a cache key or paths filter in the workflows stands for: the entry files whose repo imports, followed through,
# it must cover (scripts/inputs.py), and the other files they read. A key the patterns miss restores stale outputs; a
# filter that misses one skips the checks of a PR that changes it.
DOCKERFILES = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob("ci/*.Dockerfile"))  # the CI images' sources (#481)
MADE_FROM = {
    "ours-convex": (["model/ours.py"], ["model/mjcf.py", "uv.lock"]),
    "sim": (["model/report.py", "model/test_report.py", "model/ours.py"], ["uv.lock"]),  # just sim: ours, report, test
    # the Mech's pictures and GLB (#649): the render code, the parts' make and Blender's pin
    "pictures": (["model/render/pictures.py", "web/build.py", "model/ours.py"], ["ci/blender.Dockerfile", "uv.lock"]),
    "mech": (["mech/standin.py", "mech/test_mech.py"], ["eyes/boot.py", "justfile"]),  # the Core's program, its tag
    # the release and title rules' tests (#732): the rules, their tests and the packages they run through (ADR 0010,
    # 0017)
    "release": (
        [],
        [
            "release.config.mjs",
            "ci/release.test.mjs",
            "ci/commitlint.config.mjs",
            "ci/commitlint.test.mjs",
            "ci/package-lock.json",
        ],
    ),
    # Convex, Shards and the Model shards: the tests marked model, just sim, the shard list and the parts' cut, and
    # beside their imports the Core program and calibration traces.py plays (from eyes/, so not an import inputs sees)
    # and the scripts, config and workflow that run them
    "model": (
        [*MODEL_TESTS, "conftest.py", "model/report.py", "model/shards.py", "model/convex_parts.py"],
        [
            *(s for s in trajectories.SOURCES if not s.startswith("model/")),
            "scripts/heavy.py",
            "scripts/inputs.py",
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            "justfile",
            ".github/workflows/checks.yml",
        ],
    ),
}


# prefix-[matrix-]hash
KEY = re.compile(r"([a-z-]+?)-(?:\$\{\{ matrix\.\w+ \}\}-)?\$\{\{ hashFiles\((.*)\) \}\}")
# prefix-[matrix-]hash, the hash one the code derives (#469): NAME=$(python3 scripts/inputs.py --hash FILE...), in the
# step `inputs` and the outputs NAME-hash of the job `changes`
DERIVED = re.compile(
    r"([a-z-]+?)-(?:\$\{\{ matrix\.\w+ \}\}-)?\$\{\{ (?:steps\.inputs|needs\.changes)\.outputs\.(\w+?)(?:-hash)? \}\}"
)
HASHED = re.compile(r"(\w+)=\$\(python3 scripts/inputs\.py --hash ([^)]+)\)")


def patterns():
    """{name: [patterns]} for each cache key (by its prefix) and paths filter of the workflows, every copy of it."""
    found = {}
    for f in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        jobs = yaml.safe_load(f.read_text())["jobs"]
        hashed = {
            name: sorted(inputs(*files.split()))
            for step in jobs.get("changes", {}).get("steps", [])
            if step.get("id") == "inputs"
            for name, files in HASHED.findall(step["run"])
        }
        for job in jobs.values():
            for step in job.get("steps", []):
                with_ = step.get("with", {})
                if m := KEY.fullmatch(with_.get("key", "")):
                    found.setdefault(m[1], []).append(re.findall(r"'([^']+)'", m[2]))
                elif m := DERIVED.fullmatch(with_.get("key", "")):
                    found.setdefault(m[1], []).append(hashed[m[2]])
                if "paths-filter" in step.get("uses", ""):
                    for name, globs in yaml.safe_load(with_["filters"]).items():
                        found.setdefault(name, []).append(globs)
    return found


def covered(file, globs):
    return any(PurePosixPath(file).full_match(g) for g in globs if not g.startswith("!"))


def test_every_cache_key_and_paths_filter_covers_what_it_is_made_from():
    found = patterns()
    assert MODEL_TESTS, "git grep found no test marked model"
    assert set(found) == set(MADE_FROM), "a key or filter new to the workflows: say what it is made from"
    missed = {
        (name, i, file)
        for name, (entries, others) in MADE_FROM.items()
        for i, globs in enumerate(found[name])
        for file in sorted(inputs(*entries) | {*others})
        if not covered(file, globs)
    }
    assert missed == set()


def test_the_mechs_key_hashes_no_justfile_workflow_or_test():
    """A justfile, workflow or test edit renders no picture and bakes no GLB (#469, #649): its key hashes only what the
    render code reads."""
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    tooling = [
        f
        for f in tracked
        if f == "justfile" or f.startswith(".github/") or PurePosixPath(f).name.startswith(("test_", "conftest"))
    ]
    assert {f for globs in patterns()["pictures"] for f in tooling if covered(f, globs)} == set()


def test_the_sim_key_hashes_no_justfile_or_workflow():
    """A CI edit re-runs no 10-13 min sim (#732): its key hashes what the reports are made from, as the Mech's."""
    tooling = ("justfile", ".github/workflows/checks.yml")
    assert {f for globs in patterns()["sim"] for f in tooling if covered(f, globs)} == set()


def test_the_jobs_run_in_our_images_by_the_main_tag():
    """Every job's image is one ci/*.Dockerfile builds, by the :main tag ci-images.yml pushes on main (#481)."""
    ours = {f"ghcr.io/yellow-pine/noggin-ci-{PurePosixPath(i).stem}:main" for i in DOCKERFILES}
    images = [
        job["container"]["image"]
        for f in (ROOT / ".github" / "workflows").glob("*.yml")
        for job in yaml.safe_load(f.read_text())["jobs"].values()
        if "container" in job
    ]
    assert images
    assert [i for i in images if i not in ours] == []


def test_a_pattern_covers_a_file_as_hashfiles_and_paths_filter_match_it():
    assert covered("model/printed/gimbal.py", ["model/printed/**", "!model/build/**"])
    assert not covered("model/fits.py", ["model/printed/**", "model/geometry.py"])


RECIPES = json.loads(
    subprocess.run([ROOT / ".venv/bin/just", "--dump", "--dump-format", "json"], cwd=ROOT, capture_output=True).stdout
)["recipes"].values()
HEAVY = {r["name"] for r in RECIPES if {"group": "heavy"} in r["attributes"]}


def test_every_recipe_under_the_heavy_lock_is_in_the_heavy_group():
    """A recipe that takes the lock (HEAVY, scripts/heavy.py) is heavy, so the deny list below must ban it."""
    locked = {r["name"] for r in RECIPES if '["variable", "HEAVY"]' in json.dumps(r["body"])}
    assert locked
    assert locked <= HEAVY


def test_claude_codes_deny_list_bans_the_heavy_recipes_and_no_other():
    """CI builds the heavy recipes, never an agent's session (#611): .claude/settings.json's permissions.deny names
    each in the forms agents run it."""
    deny = json.loads((ROOT / ".claude/settings.json").read_text())["permissions"]["deny"]
    assert HEAVY
    assert {r for r in deny if re.match(r"Bash\((uv run )?just ", r)} == {
        f"Bash({runner}just {name} *)" for name in HEAVY for runner in ("", "uv run ")
    }


def _table_servos(table, column):
    """The servo names in a Markdown table's column, by its header."""
    head, _, *rows = table.splitlines()
    i = [c.strip() for c in head.strip("|").split("|")].index(column)
    return [r.strip("|").split("|")[i].strip() for r in rows if r.startswith("|")]


def test_the_eye_program_drives_stage_1s_servos_on_their_ports():
    """One yaw and one pitch servo for both eyes and a lid servo per eye (#896): the eyes Core's ports are Stage 1's
    horns, and the eye program (eyes/eyes.py keeps its own GPIO -> servo map: the Core runs it alone) names what each
    GPIO drives as the ports do; the wiring table and Stage 1's servo table name the same servos."""
    import eyes  # the Core's program (eyes/ is on sys.path: conftest.py)
    import macros
    from model.geometry import SERVO_LABEL

    names = {pin: name for pin, name in eyes.NAME.items() if pin != eyes.PAN}
    assert {eyes.PORT_GPIO[str(port)]: servo for port, servo in CORES["eyes"].items()} == names
    assert eyes.NAME[eyes.PAN] in CORES["neck"].values()  # the neck Core's, by its core.json (#688)
    stage_1 = _table_servos(macros.stage_guides()[1]["1"], "Servo")
    assert sorted(SERVO_LABEL[s] for s in CORES["eyes"].values()) == sorted(stage_1)
    wiring = macros.wiring()
    wired = zip(_table_servos(wiring, "Core"), _table_servos(wiring, "Servo"), strict=True)
    assert sorted(s for core, s in wired if core == "1 (eyes)") == sorted(stage_1)


def test_the_calibration_is_the_models_nominals_until_a_stage_1_is_calibrated():
    """eyes/calibration.json and the eye program's fallback are Stage 1's horns about their 90 neutral (#896,
    inferred): the yaw over its range, the pitch centred where the gaze is level and as far each way as both ends
    allow, each lid closed where its lids meet, resting with its edge over the pupil, open at its open edge."""
    import eyes
    from model import gimbal, stages

    cal = json.loads((ROOT / "eyes/calibration.json").read_text())
    horns = stages.SUBS["eyes"]().horns
    yaw, pitch = horns["yaw horn"].limits, horns["pitch horn"].limits
    level, reach = 90 + gimbal.servos(0, 0)[1], min(-pitch[0], pitch[1])
    lid = {"lo": gimbal.LID_SHUT, "rest": gimbal.LID_REST, "hi": gimbal.LID_EDGES[1]}
    nominal = {"yaw_lo": 90 + yaw[0], "yaw_hi": 90 + yaw[1], "pitch_lo": level - reach, "pitch_hi": level + reach}
    nominal |= {f"{s}_lid_{k}": 90 + edge - gimbal.LID_REST for s in "lr" for k, edge in lid.items()}
    assert {k: cal[k] for k in nominal} == pytest.approx(nominal, abs=0.05)
    assert {k: eyes.DEFAULT_CAL[k] for k in cal} == cal
