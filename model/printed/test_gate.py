"""Seam: the gate (#50). Each part in printed.PARTS stands in for the designer's mesh in every document that places it,
and the engine must see the same Mech: transmission identical (every driven joint at every swept pose) and every
clearance it measures against the part (those under NEAR_MM, as model/engine/run.py) within CLEARANCE_MM of the
designer's, with no new penetration. Clearances are
exact to NEAR_MM here (the sweep's vertex screen above EXACT_MM depends on tessellation). Local only: skipped without
docs/references and model/build/steps (make model-step-meshes)."""

import os

import pytest

from model import printed
from model.engine import linkage, meshes, run, stages

CLEARANCE_MM = 0.3
HAVE_REFERENCES = os.path.isdir(stages.MODELS["eyes"]) and os.path.isfile(stages.step("horn"))
pytestmark = pytest.mark.skipif(
    not HAVE_REFERENCES, reason="local references only (docs/references, model/build/steps)"
)


def placing(stem):
    """(doc, part names) for every document that places the designer's `stem`."""
    for doc in stages.DOCS:
        names = [n for n, p in stages.STAGES[doc].parts.items() if os.path.basename(p.file) == stem + ".stl"]
        if names:
            yield doc, names


CASES = [(stem, doc, names) for stem in printed.PARTS for doc, names in placing(stem)]


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    out = tmp_path_factory.mktemp("printed")
    return {stem: printed.export(stem, str(out / f"{stem}.stl")) for stem in printed.PARTS}


@pytest.mark.parametrize("stem, doc, names", CASES, ids=[f"{s}-{d}" for s, d, _ in CASES])
def test_ours_stands_in_for_the_designers_mesh(stem, doc, names, exported, monkeypatch):
    monkeypatch.setattr(meshes, "EXACT_MM", meshes.NEAR_MM)
    theirs = stages.STAGES[doc]
    ours = theirs._replace(parts={**theirs.parts, **{n: theirs.parts[n]._replace(file=exported[stem]) for n in names}})
    loaded = {"theirs": meshes.load(theirs)}
    loaded["ours"] = {**loaded["theirs"], **meshes.load(ours, names)}
    still = {}  # parts the horn does not move keep their neutral placement: placed once

    def placed(k, n, pose, moving):
        if moving:
            return meshes.Placed(loaded[k][n], pose.parts[n])
        if (k, n) not in still:
            still[k, n] = meshes.Placed(loaded[k][n], theirs.parts[n].matrix)
        return still[k, n]

    off, worst, near = [], 0.0, 0
    for h, horn in theirs.horns.items():
        movers, skip = run.chain(horn), run.linked(theirs, horn)
        pairs = [(m, o) for m in movers for o in theirs.parts if o not in movers and frozenset((m, o)) not in skip]
        pairs = [p for p in pairs if set(p) & set(names)]
        lo, hi = horn.limits
        for deg in [*range(lo, hi, run.STEP_DEG), hi]:
            try:
                poses = {k: stages.pose(s, h, deg) for k, s in (("theirs", theirs), ("ours", ours))}
            except linkage.Unreachable:
                continue
            if poses["ours"].joints != poses["theirs"].joints:
                off.append((h, deg, "joints", poses["theirs"].joints, poses["ours"].joints))
            for pair in pairs:
                (dt, deep_t), (do, deep_o) = (
                    meshes.judge(placed(k, pair[0], poses[k], True), placed(k, pair[1], poses[k], False))
                    for k in ("theirs", "ours")
                )
                dt, do = min(dt, meshes.NEAR_MM), min(do, meshes.NEAR_MM)  # the sweep measures nothing beyond NEAR_MM
                worst, near = max(worst, abs(do - dt)), near + (min(dt, do) < meshes.NEAR_MM)
                if abs(do - dt) > CLEARANCE_MM or (deep_o > 0) != (deep_t > 0):
                    off.append(
                        (h, deg, pair, "theirs", round(dt, 2), round(deep_t, 2), "ours", round(do, 2), round(deep_o, 2))
                    )
    print(f"{stem} in {doc}: {near} clearances under {meshes.NEAR_MM} mm, worst difference {worst:.3f} mm")
    assert off == [], "\n".join(map(str, off))
