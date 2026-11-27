"""The latest file (#998): Cansin's one Blender file of where the Mech stands, each layer from its newest candidate.

`just latest` (`python -m model.latest`, local only, never the GX10 or CI) writes LATEST: one rest-pose scene in the
head's frame with four collections, Mechanism, Skeleton, Skin reference (the private Morty, a toggle that starts off:
it shares the Shells' surface) and Skin Shells, each from
its layer's candidate (pick: the newest pushed of the open PRs whose changes touch the layer's files and whose head
contains main's newest commit touching them, else main) and labelled with its PR or branch, commit, date and gate
status, then the PRs passed over for lacking main's commit. A candidate's commit is exported once and
cached by commit (CACHE): its parts built without the Finish (`model.ours` without Blender), then its own review's
assemble step (model/review, export.py); the Skeleton is the raw warped bones of the candidate's own Skeleton scene,
and the Skin Shells are the Shells its own build cut from the Sculpt (shells(): their STLs, in the Skin's colours),
which show even when the candidate's assemble fails and whether or not a document wears them yet (#850), with its
eyeball caps, which its assemble places: a failed one leaves the Shells alone, its reason in the label. Written beside LATEST and
renamed into place with the review's receipt, under its own lock and the Mac's heavy lock (review.SLOT); Cansin's
Blender reloads it like the review (model/review/reload.py). Nothing here is committed, uploaded or published: the
Morty reference is read in place, and the file and cache stay on the Mac.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from itertools import takewhile

from model import geometry as g
from model import review, skeleton, stages
from scripts.gx10 import atomic_json, checksum

LATEST = os.environ.get("NOGGIN_LATEST", os.path.expanduser("~/Desktop/noggin-latest.blend"))  # Cansin's latest file
CACHE = os.environ.get("NOGGIN_LATEST_CACHE", os.path.expanduser("~/Library/Caches/noggin-latest"))  # by commit
LAYERS = ("Mechanism", "Skeleton", "Skin reference", "Skin Shells")
# a layer's files: the Skeleton scene and its pipeline; what cuts the Shells and places and cuts the reference too (the
# Skin's code, the Sculpt and its cutter, Morty's contours); the Morty reference's own workflow (model/review's); the
# rest of the model is the Mechanism's (this recipe and CI's test timings aside)
SKELETON = re.compile(r"model/(skeleton|skull)/")
SKIN = re.compile(r"model/(.+/)?(test_)?skin\.py$|model/morty/|model/contours\.json$")
REFERENCE = re.compile(r"model/review/")
NOT_MODEL = re.compile(r"model/(latest/|durations\.json$)")
OK, WAIT = {"SUCCESS", "SKIPPED", "NEUTRAL"}, {None, "", "PENDING", "EXPECTED"}
PRS = 100  # shortcut: the open PRs read in one query; page them once there are more
TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}  # whose PR code runs on this Mac, from a branch of this repo alone
BOTS = {"dependabot", "noggin-release"}  # the bots this repo already trusts (Dependabot, its Release App)
QUERY = (
    """query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) {
  pullRequests(states: OPEN, first: %d) { nodes { number headRefOid isCrossRepository authorAssociation author { login }
    files(first: 100) { nodes { path } }
    commits(last: 1) { nodes { commit { committedDate statusCheckRollup { contexts(first: 100) { nodes {
      ... on CheckRun { name conclusion } ... on StatusContext { context state } } } } } } } } } } }"""
    % PRS
)
SCRIPT, EXPORT = (os.path.join(os.path.dirname(os.path.abspath(__file__)), f) for f in ("blender.py", "export.py"))


def layers(path):
    """The layers a changed file touches."""
    if not path.startswith("model/") or NOT_MODEL.match(path):
        return set()
    if SKELETON.match(path):
        return {"Skeleton"}
    if SKIN.match(path):
        return {"Skin reference", "Skin Shells"}
    if REFERENCE.match(path):
        return {"Skin reference"}
    return {"Mechanism"}


def gate(checks):
    """pass, `pending: <names>` or `fail: <names>` from [(check, conclusion)], a conclusion None while it runs."""
    fail = [n for n, c in checks if c not in OK | WAIT]
    wait = [n for n, c in checks if c in WAIT]
    return f"fail: {', '.join(fail)}" if fail else f"pending: {', '.join(wait)}" if wait else "pass"


def trusted(pr):
    """Whether a PR's code may run here: its branch in this repo (no fork) and its author a member or a trusted bot."""
    return not pr["fork"] and (pr["association"] in TRUSTED or pr["author"] in BOTS)


def pick(main, prs):
    """{layer: candidate}: of the trusted open PRs whose changes touch the layer, the most recently pushed whose head
    contains main's newest commit touching it (main's `commits`: {layer: sha}, a layer left out older than every PR; a
    PR's `contains`: which of those its head has), else main: a branch without main's change shows the layer as it
    was before it (#1066). Each record is {name, sha, date (ISO), files, checks: [(name, conclusion)]} and a PR's
    {contains, fork, author, association}; each candidate adds its label, which ends with the PRs pushed since that
    were passed over and the commit of main's they lack."""
    out, when = {}, datetime.fromisoformat
    for layer in LAYERS:
        base = main.get("commits", {}).get(layer)
        touching = sorted(
            (p for p in prs if trusted(p) and any(layer in layers(f) for f in p["files"])),
            key=lambda p: when(p["date"]),
            reverse=True,
        )
        over = list(takewhile(lambda p: base and base not in p["contains"], touching))
        c = [*touching, main][len(over)]
        note = f"; passed over {', '.join(p['name'] for p in over)} (without main's {base[:7]})" if over else ""
        out[layer] = c | {"label": f"{c['name']} {c['sha'][:7]} {c['date'][:10]} {gate(c['checks'])}{note}"}
    return out


def _run(args, **kw):
    return subprocess.run(args, check=True, capture_output=True, text=True, cwd=stages.REPO, **kw).stdout


def _checks(rollup):
    """[(name, conclusion)] from GitHub's check runs and status contexts."""
    return [
        (c.get("name") or c.get("context"), (c.get("conclusion") or c.get("state") or "").upper() or None)
        for c in rollup
    ]


def changed(log):
    """{layer: main's newest commit touching it} from `git log --format=@%H --name-only`, newest first."""
    out, sha = {}, None
    for line in log.splitlines():
        if line.startswith("@"):
            sha = line[1:]
        for layer in layers(line):
            out.setdefault(layer, sha)
    return out


def within(sha, head):
    """Whether commit `sha` is an ancestor of `head`, by git."""
    r = subprocess.run(["git", "merge-base", "--is-ancestor", sha, head], cwd=stages.REPO)
    if r.returncode > 1:  # 1 is git's "no"; anything else is a commit it lacks
        r.check_returncode()
    return not r.returncode


def records():
    """(main, [open PR]) as pick reads them, from origin and gh; each PR's push time is its head commit's date, and
    its `contains` git's ancestor check of main's `commits` against its fetched head."""
    _run(["git", "fetch", "-q", "origin", "main"])
    sha = _run(["git", "rev-parse", "origin/main"]).strip()
    date = _run(["git", "show", "-s", "--format=%cd", "--date=iso-strict-local", sha], env=os.environ | {"TZ": "UTC"})
    runs = _run(
        ["gh", "api", f"repos/{{owner}}/{{repo}}/commits/{sha}/check-runs", "--paginate", "--jq", ".check_runs[]"]
    )
    checks = _checks(json.loads(line) for line in runs.splitlines())
    # shortcut: main's last 300 commits on model/; a layer untouched in them counts as older than every open PR
    commits = changed(_run(["git", "log", "--format=@%H", "--name-only", "-n", "300", sha, "--", "model"]))
    main = {"name": "main", "sha": sha, "date": date.strip(), "files": [], "checks": checks, "commits": commits}
    nodes = json.loads(
        _run(["gh", "api", "graphql", "-F", "owner={owner}", "-F", "name={repo}", "-f", f"query={QUERY}"])
    )["data"]["repository"]["pullRequests"]["nodes"]
    prs = []
    for p in nodes:
        head = p["commits"]["nodes"][0]["commit"]
        prs.append(
            {
                "name": f"PR #{p['number']}",
                "sha": p["headRefOid"],
                "date": head["committedDate"],
                "files": [f["path"] for f in p["files"]["nodes"]],
                "checks": _checks((head["statusCheckRollup"] or {"contexts": {"nodes": []}})["contexts"]["nodes"]),
                "contains": [],
                "fork": p["isCrossRepository"],
                "author": (p["author"] or {}).get("login"),
                "association": p["authorAssociation"],
            }
        )
        if not trusted(prs[-1]):
            print(f"latest: skipped PR #{p['number']}: a fork or an outside author, whose code never runs here")
    if len(prs) == PRS:
        print(f"latest: only the {PRS} oldest open PRs are read", flush=True)
    heads = [p for p in prs if trusted(p) and any(layers(f) for f in p["files"])]  # pick's possible candidates
    if heads:
        _run(["git", "fetch", "-q", "origin", *(p["sha"] for p in heads)])
    for p in heads:
        p["contains"] = [c for c in set(commits.values()) if within(c, p["sha"])]
    return main, prs


def export(c, morty=review.MORTY):
    """The candidate's assembled review file (model/review's assemble step, at rest, no Finish) and its job, cached by
    commit and the Morty reference's stamp; raises with the reason when its export fails."""
    home = os.path.join(CACHE, c["sha"])
    stamp = os.stat(morty).st_mtime_ns if os.path.isfile(morty) else "none"
    blend = os.path.join(home, f"assembled-{stamp}.blend")
    if os.path.isfile(blend):
        return blend, os.path.join(home, f"job-{stamp}.json")
    src = os.path.join(home, "src")
    py, log = os.path.join(stages.REPO, ".venv/bin/python"), os.path.join(home, "export.log")
    if not os.path.isfile(os.path.join(src, "model/build/ours/.done")):
        if c["name"].startswith("PR #"):
            _run(["git", "fetch", "-q", "origin", f"pull/{c['name'][4:]}/head"])
        shutil.rmtree(src, ignore_errors=True)
        os.makedirs(src)
        archive = subprocess.Popen(["git", "archive", c["sha"]], cwd=stages.REPO, stdout=subprocess.PIPE)
        subprocess.run(["tar", "-x", "-C", src], stdin=archive.stdout, check=True)
        if archive.wait():
            raise RuntimeError(f"git archive {c['sha'][:7]} failed")
        print(f"latest: building {c['name']} {c['sha'][:7]}'s parts (no Finish)", flush=True)
        # shortcut: main's venv runs every candidate; a PR that changes uv.lock builds with main's dependencies
        # no Blender: no Finish, so its Skeleton is the raw warped bones
        _logged("its parts", [py, "-m", "model.ours"], src, log, BLENDER="/nonexistent")
        open(os.path.join(src, "model/build/ours/.done"), "w").close()
    print(f"latest: assembling {c['name']} {c['sha'][:7]}", flush=True)
    _logged("its assemble", [py, EXPORT, blend, morty], src, log, PYTHONPATH=src)
    return blend, os.path.join(home, f"job-{stamp}.json")


def shells(src):
    """[[Shell, its STL, its filament's hex]]: each Shell the build in the source tree `src` cut from a Sculpt
    (g.SHELLS), which lies in the head's frame at rest, in its Colour group's filament (the review's Preset); none
    where that commit cut none."""
    ours = os.path.join(src, os.path.relpath(stages.OURS, stages.REPO))
    return [
        [f"{shape} {n}", path, g.filament(group, review.PRESET)[3]]
        for shape, names in g.SHELLS.items()
        for n, group in names.items()
        if os.path.isfile(path := os.path.join(ours, f"{shape} {n}.stl"))
    ]


def _logged(what, args, cwd, log, **env):
    """Runs args in cwd, its output appended to log; raises with its last line on a failure."""
    with open(log, "a") as f:
        r = subprocess.run(args, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, env=os.environ | env)
    if r.returncode:
        last = open(log).read().strip().splitlines()[-1:] or ["no output"]
        raise RuntimeError(f"{what} failed: {last[0][:200]} (log: {log})")


def build(out=LATEST, morty=review.MORTY):
    """The latest file at `out`: each layer's candidate exported (cached), then composed in one Blender, written beside
    `out` and renamed into place with its receipt, under its lock (one writer) and the heavy lock (one heavy job)."""
    main, prs = records()
    picked = pick(main, prs)
    held, part = [review.lock(out + ".lock")], out.removesuffix(".blend") + ".tmp.blend"
    try:
        held.append(review.lock(review.SLOT, wait=True))
        layers_, done = {}, {}
        for layer, c in picked.items():
            if c["sha"] not in done:
                try:
                    done[c["sha"]] = (*export(c, morty), None)
                except Exception as e:  # noqa: BLE001 the layer stays empty, its reason in its label
                    done[c["sha"]] = (None, None, str(e))
            blend, job, reason = done[c["sha"]]
            home = os.path.join(CACHE, c["sha"])
            if layer == "Skeleton" and os.path.isfile(os.path.join(home, "head.json")):  # its own scene's raw bones
                blend, job, reason = os.path.join(home, "src", skeleton.SCENE), os.path.join(home, "head.json"), None
            if not reason and layer == "Skin reference" and not os.path.isfile(morty):
                reason = f"no Morty reference at {morty}"
            cut = shells(os.path.join(home, "src")) if layer == "Skin Shells" else []
            layers_[layer] = {"label": c["label"], "sha": c["sha"], "blend": None if reason else blend, "job": job}
            # its cut Shells show regardless: with a reason, they are all of the layer
            layers_[layer] |= {"shells": cut, "reason": reason}
            print(f"latest: {layer}: {c['label']}" + (f" ({reason})" if reason else ""), flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "latest.json")
            with open(path, "w") as f:
                json.dump({"layers": layers_, "alpha": review.ALPHA["Skin"]}, f)
            review._blender(["-P", SCRIPT, "--", path, part])
        os.replace(part, out)
        atomic_json(out.removesuffix(".blend") + ".blend.ready.json", {"sha256": checksum(out), "layers": layers_})
    finally:
        if os.path.exists(part):
            os.remove(part)
        for f in held:
            f.close()
    print(f"latest: wrote {out}", flush=True)
