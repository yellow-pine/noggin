"""The simulation (`make sim`, ADR 0006): for every document in stages.DOCS (the recorded sweep documents and the Stage
configurations) drive each horn from its minimum to its maximum limit in STEP_DEG steps, measure the moving chain
against every other part (contacts vs penetrations as the Fusion sweep judged them), record the driven joint angles and
centres of mass per pose, the placements, bounding boxes and masses, then fold in torque, curves, fits and beams
(model/sim.py) and write model/reports/<doc>-sim.json (committed, stamped with its inputs) in the shape
model/test_report.py reads. The eyes horns are also measured at the calibrated servo ends (eyes/calibration.json) past
the designer's limits, as check.py did.
Usage: python -m model.engine.run [doc ...]"""

import glob
import hashlib
import json
import os
import sys
import time
from multiprocessing import get_context

from model import beams, electrical, fits, sim
from model.engine import linkage, masses, mech, meshes, stages

OUT = os.path.join(stages.REPO, "model", "reports")  # committed: CI thresholds them (model/test_report.py)
# Repo files a report depends on (stamp); designer meshes are not in the repo, their fingerprints go in the report.
INPUTS = [
    "model/geometry.py",
    "model/sim.py",
    "model/fits.py",
    "model/beams.py",
    "model/electrical.py",
    "model/engine/[!t]*.py",  # the engine, not its tests
    "eyes/calibration.json",
    "eyes/eyes.py",
    "eyes/gaze_trace.py",
    "eyes/replay.py",
    "eyes/servo.py",
]
STEP_DEG, CLEARANCE_MM = 10, 0.1  # as check.py: below 0.1 mm the parts overlap
TABLES = {
    "noggin-eyes": (fits.EYES_JOINTS, beams.EYES_BEAMS),
    "noggin-stack": (fits.PT_JOINTS, beams.PT_BEAMS),
    "noggin-mouth": (fits.MOUTH_JOINTS, beams.MOUTH_BEAMS),
}
EYES_HORNS = {
    "L lid horn (inferred)": "l_lid",
    "R lid horn (inferred)": "r_lid",
    "L eye horn (inferred)": "l_eye",
    "R eye horn (inferred)": "r_eye",
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
            h.update(os.path.relpath(path, stages.REPO).encode() + b"\0" + open(path, "rb").read())
    h.update(json.dumps(sources, sort_keys=True).encode())
    return h.hexdigest()


def chain(horn):
    return [horn.crank] + [n for loop in horn.loops for n in (loop.coupler, *loop.rockers)]


def linked(stage, horn):
    """Pairs that touch by construction (a joint or a rigid group): the horn on its servo, bars on their pins, rockers on
    their pivots and rigid groups (eyeball + pupil, the pan mechanism), as check.py skipped them."""
    out = {frozenset((horn.crank, horn.crank.replace(" horn (inferred)", " servo")))}
    for loop in horn.loops:
        out.add(frozenset((loop.coupler, horn.crank)))
        out.update(frozenset((loop.coupler, r)) for r in loop.rockers)
        out.update(frozenset((a, b)) for a in loop.rockers for b in loop.rockers if a != b)
        out.update(frozenset((r, p)) for r in loop.rockers for p in PIVOT_PARTNER.get(r, ()))
    return out


PIVOT_PARTNER = {
    **{f"{s} {lid} lid:1": ["main bracket v2:1"] for s in "LR" for lid in ("inside", "outside")},
    **{f"{s} eyeball:1": ["main bracket v2:1"] for s in "LR"},
    "tilt arm:1": ["upright v2:1"],
    "pan base:1": ["bearing block:1"],
    "bottom jaw:1": ["top jaw:1"],
}


def neutral(stage, loaded):
    """Every part placed at neutral with its trees built: the static side of every pair, shared by the sweeps."""
    out = {n: meshes.Placed(loaded[n], stage.parts[n].matrix) for n in loaded}
    for p in out.values():
        _ = p.tree, p.ctrees
    return out


def measure(stage, loaded, table, placed, horn_name, deg, calibrated=False):
    """One pose of one horn as check.py measured it: the moving chain against every other part within NEAR_MM
    (pairs joined by construction skipped), contacts vs penetrations, the chain's centres of mass and joint angles."""
    horn = stage.horns[horn_name]
    movers = chain(horn)
    skip = linked(stage, horn)
    out = {
        "horn": horn_name,
        "deg": deg,
        "calibrated": calibrated,
        "contacts": [],
        "violations": [],
        "measurements": 0,
        "worst": None,
    }
    try:
        pose = stages.pose(stage, horn_name, deg)
    except linkage.Unreachable as e:
        out["unreachable"] = str(e)
        return out
    moved = {m: meshes.Placed(loaded[m], pose.parts[m]) for m in movers}
    out["pose"] = {
        "com": {m: [round(c, 2) for c in masses.com_at(table[m], pose.parts[m])] for m in movers},
        "joints": pose.joints,
    }
    for m, pm in moved.items():
        for o, po in placed.items():
            if o in movers or frozenset((m, o)) in skip or meshes.bbox_gap(pm, po) > meshes.NEAR_MM:
                continue
            d, depth = meshes.judge(pm, po)
            if d >= meshes.NEAR_MM:
                continue
            out["measurements"] += 1
            pair = [m, o]
            if out["worst"] is None or d < out["worst"]["min_mm"]:
                out["worst"] = {"min_mm": round(d, 2), "at_deg": deg, "pair": pair}
            if d < CLEARANCE_MM:
                hit = {"horn": horn_name, "deg": deg, "pair": pair}
                if depth:
                    out["violations"].append({**hit, "mm": round(d, 2), "depth_mm": round(depth, 3)})
                else:
                    out["contacts"].append(hit)
    return out


_SHARED = {}  # (stage, loaded, table, neutral placed) for the forked workers: inherited, never pickled


def _job(args):
    horn_name, deg, calibrated = args
    stage, loaded, table, placed = _SHARED["job"]
    t = time.time()
    out = measure(stage, loaded, table, placed, horn_name, deg, calibrated)
    out["seconds"] = time.time() - t
    return out


def sweep_jobs(stage, cal):
    """(horn, deg, calibrated) for every pose of every horn: the designer's limits in STEP_DEG steps, then the
    calibrated servo ends (eyes/calibration.json) past them, as check.py."""
    jobs = []
    for h, horn in stage.horns.items():
        lo, hi = horn.limits
        degs = list(range(lo, hi, STEP_DEG)) + [hi]
        jobs += [(h, d, False) for d in degs]
        jobs += [(h, d, True) for d in cal.get(h, ()) if d not in degs]
    return jobs


def report(doc, parallel=True):
    """The full report for one document, in the shape of model/reports/*.json."""
    stage = stages.STAGES[doc]
    loaded = meshes.load(stage)
    table = masses.table(stage, loaded)
    cal = {}
    if any(h in EYES_HORNS for h in stage.horns):
        ends = sim.calibrated_extremes(json.load(open(os.path.join(stages.REPO, "eyes", "calibration.json"))))
        cal = {h: ends[key] for h, key in EYES_HORNS.items() if h in stage.horns}
    placed = neutral(stage, loaded)
    _SHARED["job"] = (stage, loaded, table, placed)
    jobs = sweep_jobs(stage, cal)
    if parallel and len(jobs) > 1:
        with get_context("fork").Pool(min(len(jobs), os.cpu_count() or 1)) as pool:
            results = pool.map(_job, jobs, chunksize=1)
    else:
        results = list(map(_job, jobs))
    total = sum(m["g"] for m in table.values())
    out = {
        "doc": doc,
        "version": "engine",
        "clearance_mm": CLEARANCE_MM,
        "step_deg": STEP_DEG,
        "horns": {},
        "contacts": [],
        "bboxes": {},
        "violations": stages.placements(stage),
        "mass": {n: m["g"] for n, m in table.items()},
        "mass_source": {n: m["source"] for n, m in table.items()},
        "stage": {
            "total_g": round(total, 1),
            "com": [
                round(sum(m["g"] * masses.com_at(m, stage.parts[n].matrix)[i] for n, m in table.items()) / total, 1)
                for i in range(3)
            ],
        },
        "calibrated": {},
        "unreachable": {},
    }
    for n, p in placed.items():
        out["bboxes"][n] = [[round(c, 2) for c in p.lo], [round(c, 2) for c in p.hi]]
    for h in stage.horns:
        out["horns"][h] = {
            "min_mm": meshes.NEAR_MM,
            "at_deg": None,
            "pair": None,
            "note": f"nothing within {meshes.NEAR_MM} mm",
            "poses": {},
            "measurements": 0,
            "seconds": 0.0,
        }
        if h in cal:
            out["calibrated"][h] = {"lo": cal[h][0], "hi": cal[h][1]}
    for r in results:
        h, horn = r["horn"], out["horns"][r["horn"]]
        horn["measurements"] += r["measurements"]
        horn["seconds"] = round(horn["seconds"] + r["seconds"], 1)
        if "unreachable" in r:
            out["unreachable"].setdefault(h, []).append({"deg": r["deg"], "why": r["unreachable"]})
            continue
        if not r["calibrated"]:
            horn["poses"][r["deg"]] = r["pose"]
            if r["worst"] and r["worst"]["min_mm"] < horn["min_mm"]:
                horn.update(r["worst"])
                horn.pop("note", None)
        for key in ("contacts", "violations"):
            for hit in r[key]:
                if r["calibrated"]:
                    out["calibrated"].setdefault(h, {}).setdefault(key, []).append(
                        {"deg": hit["deg"], "pair": hit["pair"]}
                    )
                else:
                    out[key].append(hit)
    peak = mech.peak_accel(json.load(open(os.path.join(stages.REPO, "eyes", "calibration.json"))))
    dynamic = {
        h: mech.dynamic_torque(stage, table, h, sorted(int(d) for d in v["poses"]), peak.get(mech.HORN_SERVO[h], 0.0))
        for h, v in out["horns"].items()
        if v["poses"]
    }
    joints, links = [], []
    for sub in stages.DOCS[doc][0]:  # fits and beams of the sub-assemblies present
        j, l = TABLES.get(sub, ([], []))
        joints += j
        links += l
    sim.UP[doc] = stage.up
    out = sim.enrich(out, fits.fit_table(joints), beams.beam_table(links))
    src = sources(stage, joints, links)
    out["inputs"] = {"stamp": stamp(src), "sources": src}
    out["clutch"] = {h: mech.clutch(by_deg) for h, by_deg in dynamic.items()}
    if {mech.PAN, mech.TILT} <= set(stage.horns):  # the neck on the base: the Mech can tip
        outline = mech.footprint(placed["PandT base:1"].vertices)
        out["tip_over"] = mech.tip_over(stage, table, outline, STEP_DEG)
        out["cable_reach"] = mech.cable_reach(stage, STEP_DEG)
    if all(p in stage.parts for p in electrical.SERVO_PART.values()):  # the whole Mech: both Cores
        out["electrical"] = electrical.budget()
    for h, by_deg in dynamic.items():
        t = out["torque"][h]
        if mech.HORN_SERVO[h] not in peak:  # untraced (Core 2): what its choreography may reach
            t["accel_limit_deg_s2"] = round(mech.accel_limit(by_deg, t["limit_kgf_cm"]))
            t["inertia_g_mm2"] = round(max(v["inertia_g_mm2"] for v in by_deg.values()))
            continue
        deg = max(by_deg, key=lambda d: by_deg[d]["kgf_cm"])
        t.update(
            dynamic_kgf_cm=round(by_deg[deg]["kgf_cm"], 3),
            dynamic_at_deg=deg,
            inertia_g_mm2=round(by_deg[deg]["inertia_g_mm2"]),
            accel_deg_s2=round(peak[mech.HORN_SERVO[h]]),
        )
    return out


def main(docs):
    for doc in docs:
        t = time.time()
        r = report(doc)
        horns = ", ".join(  # timings vary per run: printed, not committed
            f"{h} {v['min_mm']} mm {v.pop('seconds')} s" for h, v in r["horns"].items()
        )
        with open(os.path.join(OUT, f"{doc}-sim.json"), "w") as f:
            json.dump(r, f, indent=1)
            f.write("\n")
        print(
            f"{doc}: {time.time() - t:.1f} s; {len(r['violations'])} violations, {len(r['contacts'])} contacts; {horns}"
        )


if __name__ == "__main__":
    main(sys.argv[1:] or list(stages.DOCS))
