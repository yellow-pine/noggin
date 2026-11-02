"""Derived, not listed (docs/adr/0011): a workflow, the justfile or a doc never spells out a list the code holds (the
gestures, the servos, the documents the model simulates). A list is two or more of one list's names in a workflow or
the justfile, or three on one line of Markdown, where two is prose ("pan and tilt"). A name joined to another word by a
hyphen ("pan-tilt") is not the name."""

import json
import re
import subprocess
from pathlib import Path, PurePosixPath

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
    # the next Mech's pictures and GLB (#649): the render code, the parts' make and Blender's pin
    "next": (["model/render/pictures.py", "web/build.py", "model/ours.py"], ["ci/blender.Dockerfile", "uv.lock"]),
    "mech": (["mech/standin.py", "mech/test_mech.py"], ["eyes/boot.py", "justfile"]),  # the Core's program, its tag
    # the release rules' test (#732): the rules, the test and the semantic-release it runs them through (docs/adr/0017)
    "release": ([], [".releaserc.json", "ci/release.test.mjs", "ci/package-lock.json"]),
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


def test_the_next_mechs_key_hashes_no_justfile_workflow_or_test():
    """A justfile, workflow or test edit renders no picture and bakes no GLB (#469, #649): its key hashes only what the
    render code reads."""
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    tooling = [
        f
        for f in tracked
        if f == "justfile" or f.startswith(".github/") or PurePosixPath(f).name.startswith(("test_", "conftest"))
    ]
    assert {f for globs in patterns()["next"] for f in tooling if covered(f, globs)} == set()


def test_the_sim_key_hashes_no_justfile_or_workflow():
    """A CI edit re-runs no 10-13 min sim (#732): its key hashes what the reports are made from, as the next Mech's."""
    tooling = ("justfile", ".github/workflows/checks.yml")
    assert {f for globs in patterns()["sim"] for f in tooling if covered(f, globs)} == set()


def test_the_jobs_run_in_our_images_by_the_main_tag():
    """Every job's image is one ci/*.Dockerfile builds, by the :main tag images.yml pushes on main (#481)."""
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
    assert covered("model/printed/lid.py", ["model/printed/**", "!model/build/**"])
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
