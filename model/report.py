"""The sim report (`just sim`, ADR 0007): for every document physics runs on (geometry.SIMULATED, the mechanical ones:
#809) the electrical budget where both Cores are,
the next Mech's eye gimbal (model/gimbal.py; its bounding box and lid drives' sweep, model/printed/gimbal.py), neck
(model/neck.py) and head variant (model/base.py, model/candidates.py), and the MuJoCo half (model/mujoco_report.py),
measured on the document's MJCF, written beside it as model/build/reports/<doc>.xml. Written to
model/build/reports/<doc>-sim.json in the shape model/test_report.py reads, and the head variants' ranking from theirs to
model/build/reports/next-mech-ranking.json: build outputs, never committed; CI builds them and the site publishes main's
at /reports (docs/adr/0009). CI measures each in parts on as many runners (model/shards.py; SIM_PART=i/n: its share
of the poses and motions, model/mujoco_report.py, into model/build/sim-part-<i>-of-<n>) and merges them (--merge).
Usage: [SIM_PART=i/n] python -m model.report [doc ...]; python -m model.report --merge"""

import concurrent.futures
import json
import multiprocessing
import os
import shutil
import sys
import time

import mujoco
import numpy as np

from model import base, candidates, convex_parts, electrical, gimbal, mjcf, mujoco_report, neck, stages
from model import geometry as g
from model.printed import gimbal as gimbal_parts

OUT = os.path.join(stages.REPO, "model", "build", "reports")  # CI thresholds them (model/test_report.py)
RANKED = [d for d in g.NEXT if d in g.SIMULATED]  # the head variants ranked (#686), each in its mechanical document


def folder(part):
    """Where a part (i, n) writes its reports: OUT for the whole, model/build/sim-part-<i>-of-<n> for a share."""
    return OUT if part[1] == 1 else os.path.join(mjcf.BUILD, f"sim-part-{part[0]}-of-{part[1]}")


def report(doc, part=(0, 1)):
    """The full report for one document, in the shape of model/build/reports/*-sim.json, or its part (i, n): its share of
    the MuJoCo half, the first part the rest too (merge() joins them)."""
    stage, first = stages.STAGES[doc], part[0] == 0
    out = {"doc": doc}
    if "next-eyes" in stages.DOCS[doc] and first:  # the next Mech's eye gimbal moves by its own kinematics (#630)
        out["gimbal"] = {
            **gimbal.report(),
            "block_mm": gimbal_parts.bounds(gimbal_parts.at_rest(mechanical=True)),
            "sweep": gimbal_parts.sweep(),
        }
    if {"next Core 1:1", "next Core 2:1"} <= set(stage.parts) and first:  # the whole Mech: both Cores
        out["electrical"] = electrical.worst_case()
    # the MuJoCo half, measured on the MJCF written beside the report
    model = mujoco.MjModel.from_xml_path(mjcf.write(doc, folder(part)))
    if "next-neck" in stages.DOCS[doc] and first:  # the next Mech's neck moves by its own kinematics (#641)
        out["neck"] = neck.report(head(doc, model))
    if doc in g.NEXT and first:  # its head variant's figures for the ranking (#686)
        out["variant"] = candidates.report(doc, model)
    out["mujoco"] = mujoco_report.measure(doc, model, part)
    return out


def head(doc, model):
    """(grams, centre of mass in the head's frame, mm) of what the next Mech's tilt turns (neck.HEAD, the eye gimbal
    and the carrier with the boards riding the head mount), as the MJCF weighs and places them."""
    data = mujoco.MjData(model)
    mujoco.mj_kinematics(model, data)
    ids = [model.body(n).id for n in stages.STAGES[doc].horns["tilt horn"].loops[0].rockers]
    kg = model.body_mass[ids]
    com = (kg @ data.xipos[ids]) / kg.sum() * 1000  # the MJCF's root is the document's frame (up is z)
    return float(kg.sum() * 1000), tuple(float(c) for c in com - np.array(stages.DOCS[doc]["next-neck"][0]))


def _dump(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def simulate(doc, part=(0, 1)):
    """Writes the document's report (or its part's); returns its log line."""
    t = time.time()
    r = report(doc, part)
    _dump(os.path.join(folder(part), f"{doc}-sim.json"), r)
    return f"{doc}: {time.time() - t:.1f} s; {r['mujoco']['poses']} poses, {len(r['mujoco']['pairs'])} pairs"


def rank(docs):
    """The head variants ranked, beside their reports, when these documents hold them all (#686)."""
    if set(RANKED) <= set(docs):
        _dump(os.path.join(OUT, "next-mech-ranking.json"), base.rank({d: json.load(open(path(d))) for d in RANKED}))


def path(doc):
    return os.path.join(OUT, f"{doc}-sim.json")


def merge():
    """Each document's report from its parts in model/build/sim-part-*-of-<n> (all n of them, or it fails), its MJCF
    from the first; then the ranking."""
    found = [tuple(map(int, f.split("-")[2::2])) for f in os.listdir(mjcf.BUILD) if f.startswith("sim-part-")]
    n = found[0][1]
    assert sorted(found) == [(i, n) for i in range(n)], found
    docs = sorted(f.removesuffix("-sim.json") for f in os.listdir(folder((0, n))) if f.endswith("-sim.json"))
    os.makedirs(OUT, exist_ok=True)
    for doc in docs:
        parts = [json.load(open(os.path.join(folder((i, n)), f"{doc}-sim.json"))) for i in range(n)]
        _dump(path(doc), {**parts[0], "mujoco": mujoco_report.merge([p["mujoco"] for p in parts])})
        shutil.copy(os.path.join(folder((0, n)), f"{doc}.xml"), OUT)
        print(f"{doc}: {n} parts merged")
    rank(docs)


def main(docs, part=(0, 1)):
    """Each document in a process of its own (spawn, as mjcf.spec's pool), so CI's sim fits its PR budget; each part's
    convex pieces first, once, or two documents sharing a stale part would cut it into the same folder at once."""
    os.makedirs(folder(part), exist_ok=True)
    with concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn")) as pool:
        list(pool.map(mjcf.convex, *zip(*convex_parts.parts().values())))
        for line in pool.map(simulate, docs, [part] * len(docs)):
            print(line)
    if part[1] == 1:
        rank(docs)


if __name__ == "__main__":
    if sys.argv[1:] == ["--merge"]:
        merge()
    else:
        i, n = map(int, os.environ.get("SIM_PART", "0/1").split("/"))
        main(sys.argv[1:] or sorted(g.SIMULATED, reverse=True), (i, n))  # the whole Mech, the longest, first
