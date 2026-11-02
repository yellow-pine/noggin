"""The sim report (`just sim`, ADR 0007): for every document in stages.DOCS the electrical budget where both Cores are,
the next Mech's eye gimbal (model/gimbal.py; its bounding box and lid drives' sweep, model/printed/gimbal.py), neck
(model/neck.py) and head variant (model/base.py, model/candidates.py), and the MuJoCo half (model/mujoco_report.py),
measured on the document's MJCF, written beside it as model/build/reports/<doc>.xml. Written to
model/build/reports/<doc>-sim.json in the shape model/test_report.py reads, and the head variants' ranking from theirs to
model/build/reports/next-mech-ranking.json: build outputs, never committed; CI builds them and the site publishes main's
at /reports (docs/adr/0009).
Usage: python -m model.report [doc ...]"""

import concurrent.futures
import json
import multiprocessing
import os
import sys
import time

import mujoco
import numpy as np

from model import base, candidates, convex_parts, electrical, gimbal, mjcf, mujoco_report, neck, stages
from model import geometry as g
from model.printed import gimbal as gimbal_parts

OUT = os.path.join(stages.REPO, "model", "build", "reports")  # CI thresholds them (model/test_report.py)


def report(doc):
    """The full report for one document, in the shape of model/build/reports/*-sim.json."""
    stage = stages.STAGES[doc]
    out = {"doc": doc}
    if "next-eyes" in stages.DOCS[doc]:  # the next Mech's eye gimbal moves by its own kinematics (#630)
        out["gimbal"] = {**gimbal.report(), "block_mm": gimbal_parts.bounds(), "sweep": gimbal_parts.sweep()}
    if {"next Core 1:1", "next Core 2:1"} <= set(stage.parts):  # the whole Mech: both Cores
        out["electrical"] = electrical.worst_case()
    # the MuJoCo half, measured on the MJCF written beside the report
    model = mujoco.MjModel.from_xml_path(mjcf.write(doc, OUT))
    if "next-neck" in stages.DOCS[doc]:  # the next Mech's neck moves by its own kinematics (#641)
        out["neck"] = neck.report(head(doc, model))
    if doc in g.NEXT:  # its head variant's figures for the ranking (#686)
        out["variant"] = candidates.report(doc, model)
    out["mujoco"] = mujoco_report.measure(doc, model)
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


def simulate(doc):
    """Writes the document's report; returns its log line."""
    t = time.time()
    r = report(doc)
    with open(os.path.join(OUT, f"{doc}-sim.json"), "w") as f:
        json.dump(r, f, indent=1)
        f.write("\n")
    return f"{doc}: {time.time() - t:.1f} s; {r['mujoco']['poses']} poses, {len(r['mujoco']['pairs'])} pairs"


def main(docs):
    """Each document in a process of its own (spawn, as mjcf.spec's pool), so CI's sim fits its PR budget; each part's
    convex pieces first, once, or two documents sharing a stale part would cut it into the same folder at once."""
    with concurrent.futures.ProcessPoolExecutor(mp_context=multiprocessing.get_context("spawn")) as pool:
        list(pool.map(mjcf.convex, *zip(*convex_parts.parts().values())))
        for line in pool.map(simulate, docs):
            print(line)
    ranked = [os.path.join(OUT, f"{doc}-sim.json") for doc in g.NEXT]
    if set(g.NEXT) <= set(docs):  # the head variants ranked, beside their reports, when this run made them all (#686)
        with open(os.path.join(OUT, "next-mech-ranking.json"), "w") as f:
            json.dump(base.rank({doc: json.load(open(p)) for doc, p in zip(g.NEXT, ranked)}), f, indent=1)
            f.write("\n")


if __name__ == "__main__":
    main(sys.argv[1:] or sorted(stages.DOCS, reverse=True))  # the Stages, the longest, start first
