"""Derived, not listed (docs/adr/0011): a workflow, the Makefile or a doc never spells out a list the code holds (the
gestures, the servos, the documents the model simulates). A list is two or more of one list's names in a workflow or
the Makefile, or three on one line of Markdown, where two is prose ("pan and tilt"). A name joined to another word by a
hyphen ("pan-tilt") is not the name."""

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
HISTORY = ("docs/research/", "docs/adr/", "CHANGELOG.md")  # what was decided or found then, in its own words
ALLOWED = {  # (file, list): why it spells them
    ("GLOSSARY.md", "servo"): "the Servo entry defines the names",
    ("docs/how-it-works.md", "servo"): "the diagram's Core 2 label, drawn as GitHub shows it",
    ("docs/build/wiring.md", "servo"): "the second Core's ports: #306 fills them from CHANNELS",
}


def spelled_lists():
    """{(file, list): [where]} for every list a workflow, the Makefile or a doc spells out."""
    files = subprocess.run(
        ["git", "ls-files", "*.md", ".github/*.yml", "Makefile"], cwd=ROOT, capture_output=True, text=True
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
    "convex": (
        [],
        ["model/mjcf.py", "model/stages.py", "uv.lock"],
    ),  # a part's pieces: its mesh, settings and clip  # make ours; mjcf's CoACD settings
    "sim": (["model/report.py"], ["uv.lock"]),
    "trajectories": (["model/trajectories.py"], ["uv.lock"]),
    # the Blender jobs' outputs and the site's checks: the images they run in too
    "images": (["model/render/pictures.py"], ["uv.lock", *DOCKERFILES]),
    "pictures": (["model/render/pictures.py"], ["uv.lock", *DOCKERFILES]),  # every motion together, for changes (#386)
    "viewer": (["web/build.py"], ["uv.lock", *DOCKERFILES]),
    "mesa": (["model/render/blender.py"], ["ci/blender.Dockerfile"]),  # Eevee's shaders, as its Mesa compiles them
    "mech": (["mech/standin.py", "mech/test_mech.py"], ["eyes/boot.py", "Makefile"]),  # the Core's program, its tag
    "site": (["macros.py", "web/build.py", "model/render/pictures.py"], ["site/package.json", *DOCKERFILES]),
    # Convex, Shards and the Model shards: the tests marked model, make sim, the shard list and the parts' cut, and
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
            "Makefile",
            ".github/workflows/check.yml",
        ],
    ),
}


# prefix-[matrix-]hash[-lock]: the lock step's hash is uv.lock minus the release's version bump (scripts/lock_hash.py)
KEY = re.compile(
    r"([a-z-]+?)-(?:\$\{\{ matrix\.\w+ \}\}-)?\$\{\{ hashFiles\((.*)\) \}\}(-\$\{\{ steps\.lock\.outputs\.hash \}\})?"
)


def patterns():
    """{name: [patterns]} for each cache key (by its prefix) and paths filter of the workflows, every copy of it."""
    found = {}
    for f in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        for job in yaml.safe_load(f.read_text())["jobs"].values():
            for step in job.get("steps", []):
                with_ = step.get("with", {})
                if m := KEY.fullmatch(with_.get("key", "")):
                    found.setdefault(m[1], []).append(re.findall(r"'([^']+)'", m[2]) + ["uv.lock"] * bool(m[3]))
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
