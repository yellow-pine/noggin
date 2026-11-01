"""The sim report (`make sim`, ADR 0007): for every document in stages.DOCS (the recorded sweep documents and the Stage
configurations) the parts' placements against the geometry tables, the fits and beams, the electrical budget on the
whole Mech, and the MuJoCo half (model/mujoco_report.py), measured on the document's MJCF, committed beside it as
model/reports/<doc>.xml. Written to model/reports/<doc>-sim.json (committed, stamped with its inputs) in the shape
model/test_report.py reads.
Usage: python -m model.report [doc ...]"""

import glob
import hashlib
import json
import os
import sys
import time
from importlib.metadata import version

import mujoco

from model import beams, electrical, fits, mjcf, mujoco_report, stages
from model import geometry as g

OUT = os.path.join(stages.REPO, "model", "reports")  # committed: CI thresholds them (model/test_report.py)
# Repo files a report depends on (stamp); the meshes (make ours) are not committed, their fingerprints go in the report.
INPUTS = [
    "model/geometry.py",
    "model/stages.py",
    "model/linkage.py",
    "model/report.py",
    "model/sim.py",
    "model/fits.py",
    "model/beams.py",
    "model/electrical.py",
    "model/mjcf.py",  # the MuJoCo half (model/mujoco_report.py) and the committed MJCF
    "model/mujoco_report.py",
    "model/cables.py",
    "model/mating.py",
    "model/printed/*.py",  # our parts and the features they declare (the mating sites)
    "model/envelopes.py",
    "eyes/servo.py",  # the servo's speed and torque (model/electrical.py)
]
TABLES = {
    "noggin-eyes": (fits.EYES_JOINTS, beams.EYES_BEAMS),
    "noggin-stack": (fits.PT_JOINTS, beams.PT_BEAMS),
    "noggin-mouth": (fits.MOUTH_JOINTS, beams.MOUTH_BEAMS),
}


def fingerprint(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


def sources(stage, *tables):
    """{repo-relative path: fingerprint} of every mesh the document reads: its parts and the STLs its fit and beam
    tables measure."""
    paths = {p.file for p in stage.parts.values()}
    todo = list(tables)
    while todo:
        x = todo.pop()
        if isinstance(x, str) and x.endswith(".stl"):
            paths.add(x)
        elif isinstance(x, (list, tuple)):
            todo.extend(x)
    return {os.path.relpath(p, stages.REPO): fingerprint(p) for p in sorted(paths)}


def stamp(sources):
    """sha256 of the INPUTS in the repo and the recorded mesh fingerprints: a report whose stamp no longer matches is
    stale."""
    h = hashlib.sha256()
    for pattern in INPUTS:
        for path in sorted(glob.glob(os.path.join(stages.REPO, pattern))):
            if os.path.basename(path).startswith("test_"):
                continue
            h.update(os.path.relpath(path, stages.REPO).encode() + b"\0" + open(path, "rb").read())
    h.update(json.dumps(sources, sort_keys=True).encode())
    h.update(f"mujoco {version('mujoco')} coacd {version('coacd')}".encode())  # they decide the MuJoCo half
    return h.hexdigest()


def report(doc):
    """The full report for one document, in the shape of model/reports/*.json."""
    stage = stages.STAGES[doc]
    joints, links = [], []
    for sub in stages.DOCS[doc][0]:  # fits and beams of the sub-assemblies present
        j, l = TABLES.get(sub, ([], []))
        joints += j
        links += l
    out = {
        "doc": doc,
        "placements": stages.placements(stage),
        "fits": fits.fit_table(joints),
        "beams": beams.beam_table(links),
    }
    if all(f"{label} servo:1" in stage.parts for label in g.SERVO_LABEL.values()):  # the whole Mech: both Cores
        out["electrical"] = electrical.worst_case()
    src = sources(stage, joints, links)
    out["inputs"] = {"stamp": stamp(src), "sources": src}
    # the MuJoCo half, measured on the committed MJCF itself
    out["mujoco"] = mujoco_report.measure(doc, mujoco.MjModel.from_xml_path(mjcf.write(doc, OUT)))
    return out


def main(docs):
    for doc in docs:
        t = time.time()
        r = report(doc)
        with open(os.path.join(OUT, f"{doc}-sim.json"), "w") as f:
            json.dump(r, f, indent=1)
            f.write("\n")
        print(f"{doc}: {time.time() - t:.1f} s; {r['mujoco']['poses']} poses, {len(r['mujoco']['pairs'])} pairs")


if __name__ == "__main__":
    main(sys.argv[1:] or list(stages.DOCS))
