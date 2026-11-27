"""Morty's head rings (model/head.json, #850), fitted again: `just rings` (`python -m model.review.rings`, after just
ours), on the Mac alone. Run it when a part in the head changes; it writes the rings and prints what it measured.

It reads the private Morty reference in place (morty-fixed.stl beside review.MORTY, placed as the review places it) and
writes none of it but the rings' numbers: at each ring's height the reference's radius round a centre, its eye domes
(our caps stand in for them), ears and nose (model/skin.py EAR, NOSE) left out and filled from the face round them,
smoothed round and up the head alike. Then it sweeps the Mech (the pan by the tilt, every other horn alone) and, where
a part needs more than the reference gives (a wall, the Shells' clearance and MARGIN), swells the rings over it: a
rounded hill SWELL wide on each such spot, so the head stays one smooth shape. Where the Shells are open nothing
counts: under the floor, the floor's notch, the eyes' openings, and the mouth's opening but at rest, where the mouth
cover closes it and rides the jaw."""

import json
import os

import numpy as np
import trimesh
from scipy.ndimage import gaussian_filter1d

from model import geometry as g
from model import gimbal as gm
from model import review, stages
from model import skin as sk
from model.printed import skin as shells

OUT = os.path.join(os.path.dirname(sk.__file__), "head.json")
DOC = g.dressed(next(d for d in g.MECH if d in g.SIMULATED), "morty")  # the whole Mech, mechanical, in his Skin
APEX = (37.0, 116.1)  # (y, z): the reference's crown on the midline
LOWEST = sk.HEAD_Z[0] - 5.0  # the lowest ring, under the floor, so the floor cuts a whole surface
# the rings' heights: closer under the apex, where the head turns over, then every 5 mm; on under LOWEST to smooth with
ZS = np.r_[[APEX[1] - u * u for u in np.arange(0.4, 6.01, 0.4)], np.arange(75.0, LOWEST - 20.1, -5.0)]
TH = np.radians(np.arange(0.0, 180.1, 15.0))
BIN = np.radians(7.5)
DOME = gm.CAP_R + 3.6  # the reference's eye domes, round the eyes' centres
MARGIN = 0.6  # past the wall and the clearance: what the surface between two rings and two angles may miss
SWELL = (20.0, 10.0)  # each hill's width: deg round the head, mm up and down it
PAN_TILT, ALONE = 7, 5  # the sweep's steps: the pan by the tilt, every other horn alone


def reference():
    """The Morty reference's mesh in the head's frame, mm."""
    at, head = review.morty_at()
    mesh = trimesh.load(os.path.join(os.path.dirname(review.MORTY), "morty-fixed.stl"), force="mesh")
    mesh.apply_transform(head @ at)
    top = mesh.vertices[np.argmax(mesh.vertices[:, 2])]
    assert np.allclose(top[1:], APEX, atol=0.6), top  # the crown the rings close in: measure it again if this moved
    return mesh


def _polar(x, y, c):
    return np.arctan2(np.abs(x), -(y - c)), np.hypot(x, y - c)


def measured(mesh):
    """(each ring's centre y, the reference's radius at each ring and angle as measured, the same smoothed)."""
    secs = []
    for z in ZS:
        loop = max(mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]).discrete, key=len)
        x, y = loop[:, 0], loop[:, 1]
        out = (np.linalg.norm(np.c_[np.abs(x) - gm.SPACING / 2, y, np.full(len(x), z)], axis=1) < DOME) & (y < 0)
        out |= (np.hypot(y - sk.EAR[0], z - sk.EAR[1]) < sk.EAR[2] + 7.5) & (np.abs(x) > 60)
        out |= (np.abs(x) < sk.NOSE[0] + 1) & (np.abs(z - sk.NOSE[1]) < sk.NOSE[0] + 1) & (y < 0)
        secs.append((x[~out], y[~out]))

    def radii(centres):
        ref = np.full((len(ZS), len(TH)), np.nan)
        for k, (x, y) in enumerate(secs):
            th, r = _polar(x, y, centres[k])
            for i, t in enumerate(TH):
                j = np.abs(th - t) < BIN
                if j.any():
                    ref[k, i] = np.median(r[j])
        idx = np.arange(len(ZS))
        for i in range(len(TH)):  # what was left out: from the rings over and under it first (the face behind an eye)
            ok = ~np.isnan(ref[:, i])
            gap = (idx > idx[ok].min()) & (idx < idx[ok].max()) & ~ok
            ref[gap, i] = np.interp(idx[gap], idx[ok], ref[ok, i])
        for k in range(len(ZS)):  # else from round its own ring
            ok = ~np.isnan(ref[k])
            ref[k] = np.interp(TH, TH[ok], ref[k, ok])
        return ref

    centres = np.array([(y.min() + y.max()) / 2 for _, y in secs])
    small = np.clip((10 - np.arange(len(ZS))) / 6, 0, 1)  # 1 on the small rings under the apex: kept as measured
    ref = radii(centres)
    # each ring's centre midway from its front to its back as filled, one smooth line under the small rings
    mid = centres + (ref[:, -1] - ref[:, 0]) / 2
    centres = small * centres + (1 - small) * gaussian_filter1d(mid, 2.0, mode="nearest")
    raw = radii(centres)
    ref = gaussian_filter1d(raw, 1.0, axis=1, mode="reflect")
    odd = np.vstack([-ref[::-1], np.zeros((1, len(TH))), ref])  # a radius falls to 0 at the apex: mirrored odd there
    up = gaussian_filter1d(odd, 1.2, axis=0, mode="nearest")[len(ref) + 1 :]
    return centres, raw, small[:, None] * ref + (1 - small[:, None]) * up


def _configs(stage):
    lim = {h: x.limits for h, x in stage.horns.items()}
    out = [
        {"pan horn": p, "tilt horn": t}
        for p in np.linspace(*lim["pan horn"], PAN_TILT)
        for t in np.linspace(*lim["tilt horn"], PAN_TILT)
    ]
    out += [{h: d} for h in lim if h not in ("pan horn", "tilt horn") for d in np.linspace(*lim[h], ALONE)]
    return [{}, *out]  # rest first


def needed(centres):
    """(the radius each ring needs at each angle to clear the swept Mech, 0 where nothing is; the part that needs
    it)."""
    stage = stages.STAGES[DOC]
    rest = {n: p.matrix for n, p in stage.parts.items()}
    face = next(n for n, p in stage.parts.items() if stages.stem(p.file) == "morty face")  # drawn in the head's frame
    clouds = {}
    for n, p in stage.parts.items():
        if stages.stem(p.file) not in sk.SHELLS:
            mesh = trimesh.load(stages.stl(stages.stem(p.file)), force="mesh")
            even = trimesh.sample.sample_surface_even(mesh, max(300, int(mesh.area / 2)), seed=0)[0]
            clouds[n] = np.vstack([mesh.vertices, even])
    eye_r, across = shells.EYES
    mouth_x, mouth_y, mouth_z = shells.MOUTH
    neck_x, neck_up = sk.NECK
    edges = (ZS[:-1] + ZS[1:]) / 2
    need, part = np.zeros((len(ZS), len(TH))), np.full((len(ZS), len(TH)), "", dtype=object)
    for config in _configs(stage):
        by = {n: np.eye(4) for n in rest}  # the tilt carries the pan (#978), every other horn alone
        for horn in ("tilt horn", "pan horn", *(h for h in config if h not in ("pan horn", "tilt horn"))):
            if horn in config:
                moved = stages.pose(stage, horn, config[horn]).parts
                by = {n: by[n] @ moved[n] @ np.linalg.inv(rest[n]) for n in rest}
        into = np.linalg.inv(by[face] @ rest[face])
        for n, cloud in clouds.items():
            q = trimesh.transform_points(cloud, into @ by[n] @ rest[n])
            x, y, z = q.T
            eyes = np.minimum(
                np.hypot(x - gm.SPACING / 2, np.hypot(y, z)), np.hypot(x + gm.SPACING / 2, np.hypot(y, z))
            )
            mouth = (np.abs(x) < mouth_x) & (y < mouth_y) & (z < mouth_z)
            notch = (np.abs(x) < neck_x) & (z < sk.HEAD_Z[0] + neck_up)
            open_ = ((eyes < eye_r) & (y < 5.0) & (np.abs(x) < across)) | (z < sk.HEAD_Z[0])
            open_ |= (notch | mouth) if config else (notch & ~mouth)  # at rest the mouth cover closes the mouth
            x, y, z = x[~open_], y[~open_], z[~open_]
            k = np.searchsorted(-edges, -z)  # its nearest ring
            th, r = _polar(x, y, centres[k])
            i = np.rint(th / (2 * BIN)).astype(int)
            mine = np.zeros_like(need)
            np.maximum.at(mine, (k, i), r)
            for s in (-1, 1):  # and the angle beside it, near their border: the surface there is their blend
                near = ((th - TH[i]) * s > 0.6 * BIN) & (i + s >= 0) & (i + s < len(TH))
                np.maximum.at(mine, (k[near], i[near] + s), r[near])
            more = mine > need
            need[more], part[more] = mine[more], n.removesuffix(":1")
    need[need > 0] += sk.WALL + gm.LID_CLEAR_MM + MARGIN
    return need, part


def swelled(ref, need):
    """The swell over `ref` where `need` is more: the highest of a rounded hill on every such spot, smoothed, still over
    each."""
    lack = np.maximum(need - ref, 0.0)
    round_ = np.r_[TH, 2 * np.pi - TH[-2:0:-1]]  # all the way round: a hill reaches over the midline
    all_ = np.c_[lack, lack[:, -2:0:-1]]
    hills = np.zeros_like(lack)
    for k, j in zip(*np.nonzero(all_ > 0.05), strict=True):
        dth = np.abs((TH[None, :] - round_[j] + np.pi) % (2 * np.pi) - np.pi)
        dz = (ZS[:, None] - ZS[k]) / SWELL[1]
        hills = np.maximum(hills, all_[k, j] * np.exp(-0.5 * dz**2 - 0.5 * (dth / np.radians(SWELL[0])) ** 2))
    soft = gaussian_filter1d(gaussian_filter1d(hills, 0.6, axis=1, mode="reflect"), 0.6, axis=0, mode="nearest")
    high = lack > 0.3
    return soft * max(1.0, float((lack[high] / soft[high]).max())) if high.any() else soft


def main():
    centres, raw, ref = measured(reference())
    need, part = needed(centres)
    swell = swelled(ref, need)
    rings = ref + swell
    kept = ZS >= LOWEST - 1e-6
    assert (rings[kept] >= need[kept] - 0.05).all(), float((need - rings)[kept].max())
    print("where a part needs over 1 mm more than the reference (ring z: deg round, mm, part):")
    for k in np.nonzero(kept)[0]:
        lack = [
            (int(np.degrees(t)), round(float(v), 1), p)
            for t, v, p in zip(TH, need[k] - ref[k], part[k], strict=True)
            if v > 1.0
        ]
        if lack:
            print(f"  {ZS[k]:6.1f}: {lack}")
    off = (rings - raw)[kept]
    print(f"rings - reference, mm: {off.min():.1f} to {off.max():.1f}, rms {np.sqrt((off**2).mean()):.2f}")
    print(
        f"within 2 mm on {100 * np.mean(np.abs(off) < 2):.0f}% of the head, swelled over 1 mm on {100 * np.mean(swell[kept] > 1):.0f}%"
    )
    with open(OUT) as f:
        note = json.load(f)["note"]
    rows = [
        [round(float(z), 2), round(float(c), 1), *np.round(r, 1).tolist()]
        for z, c, r in zip(ZS[kept], centres[kept], rings[kept], strict=True)
    ]
    with open(OUT, "w") as f:  # a ring a line
        f.write(
            '{\n "note": %s,\n "apex": %s,\n "theta": %s,\n "rings": [\n%s\n ]\n}\n'
            % (
                json.dumps(note),
                json.dumps(APEX),
                json.dumps(np.degrees(TH).round().tolist()),
                ",\n".join(f"  {json.dumps(r)}" for r in rows),
            )
        )
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
