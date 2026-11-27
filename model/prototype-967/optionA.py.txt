"""PROTOTYPE (#967 option A), throwaway: the re-laid eye gimbal as rough CadQuery solids about the L eye (the R its
mirror), checked against the lids' swept shell, the caps' sweep, each other over yaw x pitch, the rest of the head
(space.npz) and Morty's skin. Run: .venv/bin/python /tmp/967-proto/optionA.py"""
import sys, math; sys.path.insert(0, "/tmp/967-proto")
from lib import *
import cadquery as cq
from scipy.optimize import brentq
from model.printed import gimbal as pg
from model.envelopes import box
from model import linkage
P = dict(
    lam=33.0, rod=50.0, arm_deg=33.0, knee=(16.0, -128.0), core_flat2=14.8, in_deg=-15.0, arm=25.5, core_flat=15.5,           # the push-rod's lean down toward the back, its length, the bail's arm
    lid_y=59.5, lid_z=-8.5, pitch_back=0.0,                            # each lid servo's horn axis, y (37 today)
    rail_r=(35.4, 36.9), rail_w=16.0, rail_exit=(-30.0, -150.0), post_r=4.5, rail_front=0.0, rail_lat=(-7.0, 3.0), rail_wide=(12.0, (-13.0, 3.0)), rib=(36.0, 31.5, 3.0),
    fin_x=(0.0, 8.0), fin_t=3.0, fin=[(gm.CRANK, -28.5), (17.5, -28.5), (31.06, -12.55), (39.9, -16.1)],
    cross_y=(38.4, 48.4), cross_z=(-17.6, -14.6), tail_w=5.0,
    plate_y0=19.0,
)
E = np.array([C, 0, 0])
lam = math.radians(P["lam"])
B0 = E + (0, 0, gm.LEVER)
A0 = B0 + P["rod"] * np.array([0, math.cos(lam), -math.sin(lam)])
O = A0 + P["arm"] * np.array([0, math.sin(math.radians(P["arm_deg"])), math.cos(math.radians(P["arm_deg"]))])
PH = (gm.PITCH_HORN[0] + P["pitch_back"], gm.PITCH_HORN[1])
IN = (PH[0] + gm.CRANK - O[1]) / math.cos(math.radians(P["in_deg"]))
IP = O[1:] + IN * np.array([math.cos(math.radians(P["in_deg"])), math.sin(math.radians(P["in_deg"]))])  # the input pin     # the bail's input arm, so the pitch horn and servo stay where they are
print(f"push-rod: lever ball {B0.round(2)} -> bail ball {A0.round(2)}; bail axis (y, z) {O[1:].round(2)}; input arm {IN:.2f}")

def seg(points, t, x):
    """A flat arm t thick through the (y, z) points, over the x span."""
    out = None
    for a, b in zip(points, points[1:]):
        a, b = np.array(a, float), np.array(b, float)
        n = np.array([a[1] - b[1], b[0] - a[0]]) * t / 2 / np.linalg.norm(b - a)
        poly = [tuple(map(float, p)) for p in (a + n, b + n, b - n, a - n)]
        s = cq.Workplane("YZ", origin=(x[0], 0, 0)).polyline(poly).close().extrude(x[1] - x[0])
        s = s.union(pg.cyl("x", (0, *b), t / 2, x))
        out = s if out is None else out.union(s)
    return out.union(pg.cyl("x", (0, *points[0]), t / 2, x))

def unit(a, phi):
    a, phi = math.radians(a), math.radians(phi)
    return np.array([math.sin(a), -math.cos(a) * math.cos(phi), math.cos(a) * math.sin(phi)])

def rail():
    """The yaw bearing: the post under the yoke's stem, a strip of the sphere's inside back to the belt, out through
    it, and a pylon down to the plate."""
    d0, d1 = np.array([0, 0, -1.0]), unit(*P["rail_exit"])
    n = np.cross(d0, d1); n /= np.linalg.norm(n)
    v = np.cross(n, d0)
    t1 = math.acos(float(d0 @ d1))
    plane = cq.Plane(origin=tuple(E), xDir=tuple(d0), normal=tuple(n))
    def fan(t_a, t_b, r, lat=P["rail_lat"]):
        pts = [(0.0, 0.0)] + [(r * math.cos(t), r * math.sin(t)) for t in np.linspace(t_a, t_b, 24)]
        lo, hi = lat
        return cq.Workplane(plane).polyline(pts).close().extrude(hi - lo).translate(tuple(n * lo))
    ball = lambda r: pg.ball(r, tuple(E))
    shell = ball(P["rail_r"][1]).cut(ball(P["rail_r"][0]))
    strip = shell.intersect(fan(-math.radians(P["rail_front"]), t1, 60)).union(shell.intersect(fan(math.radians(P["rail_wide"][0]), t1, 60, P["rail_wide"][1])))
    out_r = 42.0
    strut = ball(out_r).cut(ball(P["rail_r"][0])).intersect(fan(t1 - math.radians(5), t1, 60))
    r0, r1, rw = P["rib"]  # a rib up the strip's middle, from r0 deg along it on: past the crank's and the tie-bar's sweep
    strip = strip.union(ball(P["rail_r"][0] + 0.1).cut(ball(r1)).intersect(fan(math.radians(r0), t1, 60, (-rw - 1.5, -1.5))))
    tip = E + out_r * d1
    lat = P["rail_w"] / 2 * abs(n[0])
    pylon = box((tip[0] - 5, tip[0] + 8), (tip[1] - 2.5, tip[1] + 2.5), (gm.PLATE_Z[1], tip[2] + 1))
    post = pg.cyl("z", (C, 0, 0), P["post_r"], (-math.sqrt(P["rail_r"][0] ** 2 - P["post_r"] ** 2) - 0.2, gm.YOKE["stem_z"]))
    return strip.union(strut).union(post), pylon, tip

def tie():
    w = (C + P["fin_x"][0], C + P["fin_x"][1])
    f = seg(P["fin"], P["fin_t"], w).union(pg.cyl("z", (C, gm.CRANK, 0), 3.5, gm.TIE_Z))
    out = f.union(f.mirror("YZ"))
    out = out.union(box((-C - 8, C + 8), P["cross_y"], P["cross_z"]))
    horn = (gm.YAW_Y + gm.CRANK, sum(gm.TIE_Z) / 2)
    out = out.union(seg([horn, (P["cross_y"][0] + 2, sum(P["cross_z"]) / 2)], 3.0, (-P["tail_w"] / 2, P["tail_w"] / 2)))
    return out.union(pg.cyl("z", (0, horn[0], 0), 3.5, gm.TIE_Z))

def rod():
    a, b = B0[1:], A0[1:]
    out = seg([a, b], 4.0, (C - 2.5, C + 2.5))
    return out.union(pg.ball(4.5, tuple(B0))).union(pg.ball(4.5, tuple(A0)))

def bail():
    end = C + gm.BAIL_END
    out = pg.cyl("x", (0, O[1], O[2]), 3.0, (-end, end))
    for s in (1, -1):
        knee = O[1:] + P["knee"][0] * np.array([math.cos(math.radians(P["knee"][1])), math.sin(math.radians(P["knee"][1]))])
        out = out.union(seg([O[1:], knee, A0[1:]], 4.0, (s * C - 1.5, s * C + 1.5))).union(pg.ball(3.0, (s * C, A0[1], A0[2])))
    out = out.union(seg([O[1:], IP], 6.0, gm.BAIL_INPUT_X))
    return out

def pitch_bar():
    return seg([IP, (IP[0], PH[1])], 6.0, gm.PITCH_BAR_X)

def septum():
    """The lids' carrier: a wall on the midline from the eye line back, and a post down to the plate behind the tie-bar."""
    out = box((-1.3, 1.3), (-3.0, 20.0), (-4.5, 4.5)).union(box((-5, 5), (18.0, 54.0), (-4.5, 4.5)))
    return out.union(box((-5, 5), (50.0, 54.0), (gm.PLATE_Z[1], 4.5)))

def uprights():
    end = C + gm.BAIL_END
    return box((end, end + 4), (O[1] - 4, O[1] + 4), (gm.PLATE_Z[1], O[2] + 4))

def servo_cloud(label, y=None, z=None, dy=0.0):
    face, shaft, tab, _ = gm.drives()[label]
    face = (face[0], (face[1] if y is None else y) + dy, face[2] if z is None else z)
    return trimesh.transform_points(cloud("servo"), gm.servo_matrix(face, shaft, tab))

def mirror(p): return p * (-1, 1, 1)
def moved(p, m): return trimesh.transform_points(p, m)

# ---- pitch kinematics: the bail's turn for the eye's pitch, the rod's length kept ----
ROD = float(np.linalg.norm(A0 - B0))
def A_at(beta): return O * (1, 1, 1) + linkage.rotation(g.X, beta)[:3, :3] @ (A0 - O)
def B_at(p): return E + gm.core(0, p) @ (0, 0, gm.LEVER)
def beta_of(p): return brentq(lambda b: np.linalg.norm(A_at(b) - B_at(p)) - ROD, -60, 60)
def ang(u, v): return math.degrees(math.acos(abs(float(u @ v)) / np.linalg.norm(u) / np.linalg.norm(v)))
print("pitch  bail  rod-lever  rod-arm   (deg; a rod square to its lever reads 90)")
betas = {}
for p in (-15, -7.5, 0, 7.5, 15):
    b = betas[p] = beta_of(p); A, B = A_at(b), B_at(p)
    print(f"  {p:5.1f} {b:6.2f} {ang(A - B, B - E):8.1f} {ang(A - B, A - O):8.1f}")
four = linkage.four_bar((0, *PH), (0, PH[0] + gm.CRANK, PH[1]), (0, O[1], O[2]), (0, *IP), g.X)
sv = {p: brentq(lambda s: four(s)[0] - betas[p], -80, 80) for p in betas}
def bar_deg(s):
    _, a, b = four(s); a, b = np.array(a), np.array(b)
    return ang(b - a, a - (0, *PH)), ang(b - a, b - (0, O[1], O[2]))
print("pitch servo for pitch -15..15:", {p: round(v, 1) for p, v in sv.items()}, " bar meets horn, input arm at", [tuple(round(x, 1) for x in bar_deg(sv[p])) for p in (-15, 0, 15)])

# ---- the solids, as clouds ----
print("building"); 
rail_s, pylon_s, tip = rail()
S = {"rail": solid_cloud(rail_s), "pylon": solid_cloud(pylon_s), "tie-bar": solid_cloud(tie()), "push-rod": solid_cloud(rod()),
     "bail": solid_cloud(bail()), "pitch bar": solid_cloud(pitch_bar()), "bail upright": solid_cloud(uprights()), "septum": solid_cloud(septum())}
S["L lid servo"] = servo_cloud("L lid", P["lid_y"], P["lid_z"]); S["pitch servo"] = servo_cloud("pitch", dy=P["pitch_back"]); S["yaw servo"] = servo_cloud("yaw")
S["plate front"] = solid_cloud(box((C - 30, C + 30), (P["plate_y0"], P["plate_y0"] + 10), gm.PLATE_Z))
OLD = {n: part(n) for n in ("L yaw yoke:1", "L eyeball core:1")}
_c = OLD["L eyeball core:1"] - E
OLD["L eyeball core:1"] = OLD["L eyeball core:1"][0.674 * _c[:, 1] + 0.738 * _c[:, 2] < P["core_flat2"]]  # a flat on its upper back
OLDR = {n: part(n, mech=False) for n in ("L yaw yoke:1",)}
print(f"rail leaves the sphere at {tip.round(1)}")

def yaw_pose(yaw):  # {name: 4x4}
    ys = gm.eyes(*gm.servos(yaw, 0.0))["L"][0]
    t = np.eye(4); t[:3, 3] = linkage.rotation(g.Z, yaw, (0, gm.YAW_Y, 0))[:3, :3] @ (0, gm.CRANK, 0) - (0, gm.CRANK, 0)
    return {"tie-bar": t, "yoke": linkage.rotation(g.Z, ys, tuple(E))}
def pitch_pose(p):
    b = betas.get(p) or beta_of(p)
    bm = linkage.rotation(g.X, b, (0, O[1], O[2]))
    return {"bail": bm, "push-rod": gm._carry(B0, A0, B_at(p), A_at(b)), "core": linkage.rotation(g.X, -p, tuple(E))}

print("\n== against the lids' swept shell (r 37.4..39.6 about each eye centre)")
fixed = ["septum", "rail", "pylon", "bail upright", "L lid servo", "pitch servo", "yaw servo", "plate front"]
for n in fixed:
    both = np.vstack([S[n], mirror(S[n])]) if n not in ("pitch servo", "yaw servo", "septum") else S[n]
    report2(n, both); report2(n, both, shaped=False)
for shaped in (True, False):
    report2("tie-bar, yaw -25..25", np.vstack([moved(S["tie-bar"], yaw_pose(y)["tie-bar"]) for y in np.linspace(-25, 25, 11)]), shaped)
    for n in ("push-rod", "bail"):
        pts = np.vstack([moved(S[n], pitch_pose(p)[n]) for p in np.linspace(-15, 15, 7)])
        report2(f"{n}, pitch -15..15", np.vstack([pts, mirror(pts)]), shaped)

print("\n== against the caps (37.4 mm, out to the opening's edge, 4 mm thick), over yaw x pitch")
for n in ("rail", "pylon", "L lid servo"):
    cap_sweep(n, np.vstack([S[n], mirror(S[n])]))
cap_sweep("septum", S["septum"])
for yaw in (-25, 0, 25):
    ty = moved(S["tie-bar"], yaw_pose(yaw)["tie-bar"])
    hit = max(int(in_cap(ty, gm.eyes(*gm.servos(yaw, p))[sd][0], gm.eyes(*gm.servos(yaw, p))[sd][1], s).sum()) for p in (-15, 0, 15) for sd, s in (("L", 1), ("R", -1)))
    print(f"  tie-bar at yaw {yaw}: {hit} pts in a cap")
for p in (-15, 0, 15):
    rp = moved(S["push-rod"], pitch_pose(p)["push-rod"])
    hit = max(int(in_cap(rp, yaw, p).sum()) for yaw in (-25, 0, 25))
    print(f"  push-rod at pitch {p}: {hit} pts in the L cap")

print("\n== gaps, mm (clouds, to about 0.3): least over yaw -25..25 (tie-bar, yoke) and pitch -15..15 (rod, bail, core)")
def least(a, b, poses):
    return min(gap(pa, pb) for pa, pb in poses)
Y, PT = np.linspace(-25, 25, 11), np.linspace(-15, 15, 7)
yp = {y: yaw_pose(y) for y in Y}; pp = {p: pitch_pose(p) for p in PT}
tieY = {y: moved(S["tie-bar"], yp[y]["tie-bar"]) for y in Y}
rows = []
for style, yk in (("mechanical", OLD["L yaw yoke:1"]), ("realistic", OLDR["L yaw yoke:1"])):
    yokeY = {y: moved(yk, yp[y]["yoke"]) for y in Y}
    crank = lambda p: p  # the crank is the tie-bar's own pin: skip the yoke's points within 5 mm of the pin
    def far(y):
        pin = yp[y]["yoke"] @ (C, gm.CRANK, -27, 1)
        return yokeY[y][np.linalg.norm(yokeY[y][:, :2] - pin[:2], axis=1) > 5.5]
    rows.append((f"tie-bar / yoke ({style}), past its pin's 5.5 mm", min(gap(tieY[y], far(y)) for y in Y)))
    rows.append((f"rail / yoke ({style})", min(gap(S["rail"], yokeY[y][yokeY[y][:, 2] > -26.5]) for y in Y)))
    rows.append((f"pylon / yoke ({style})", min(gap(S["pylon"], yokeY[y]) for y in Y)))
    rows.append((f"push-rod / yoke ({style})", min(gap(moved(S["push-rod"], pp[p]["push-rod"]), yokeY[y]) for y in Y[::5] for p in PT[::3])))
coreP = {p: moved(OLD["L eyeball core:1"], pp[p]["core"]) for p in PT}
rodP = {p: moved(S["push-rod"], pp[p]["push-rod"]) for p in PT}
bailP = {p: moved(S["bail"], pp[p]["bail"]) for p in PT}
rows.append(("tie-bar / rail", min(gap(tieY[y], S["rail"]) for y in Y)))
rows.append(("tie-bar / pylon (both sides)", min(gap(tieY[y], np.vstack([S["pylon"], mirror(S["pylon"])])) for y in Y)))
rows.append(("tie-bar / core", min(gap(tieY[y], coreP[p]) for y in Y[::5] for p in PT[::3])))
rows.append(("tie-bar / yaw servo", min(gap(tieY[y], S["yaw servo"]) for y in Y)))
rows.append(("tie-bar / L lid servo (both)", min(gap(tieY[y], np.vstack([S["L lid servo"], mirror(S["L lid servo"])])) for y in Y)))
rows.append(("tie-bar / push-rod", min(gap(tieY[y], rodP[p]) for y in Y[::5] for p in PT)))
rows.append(("tie-bar / bail", min(gap(tieY[y], bailP[p]) for y in Y[::5] for p in PT)))
rows.append(("tie-bar / septum", min(gap(tieY[y], S["septum"]) for y in Y)))
rows.append(("bail / septum", min(gap(bailP[p], S["septum"]) for p in PT)))
rows.append(("septum / lid servos, yaw servo", min(gap(S["septum"], np.vstack([S["L lid servo"], mirror(S["L lid servo"]), S["yaw servo"]])), 99)))
rows.append(("rail / core", min(gap(S["rail"], coreP[p]) for p in PT)))
ballless = lambda p, c: p[np.linalg.norm(p - c, axis=1) > 5.0]
rows.append(("push-rod / core, past the lever ball's 5 mm", min(gap(rodP[p], ballless(coreP[p], B_at(p))) for p in PT)))
rows.append(("push-rod / L lid servo", min(gap(rodP[p], S["L lid servo"]) for p in PT)))
rows.append(("bail / L lid servo (both)", min(gap(bailP[p], np.vstack([S["L lid servo"], mirror(S["L lid servo"])])) for p in PT)))
from scipy.spatial import cKDTree
for p in PT:
    sv_ = np.vstack([S["L lid servo"], mirror(S["L lid servo"])]); d_, i_ = cKDTree(sv_).query(bailP[p])
    if d_.min() < 0.5: print("   bail meets a lid servo at pitch", p, "bail point", bailP[p][d_.argmin()].round(1), "servo point", sv_[i_[d_.argmin()]].round(1))
rows.append(("bail / pitch servo", min(gap(bailP[p], S["pitch servo"]) for p in PT)))
rows.append(("L lid servo / pitch servo", gap(S["L lid servo"], S["pitch servo"])))
rows.append(("L lid servo / pylon", gap(S["L lid servo"], S["pylon"])))
rows.append(("pitch bar / L lid servo", gap(S["pitch bar"], S["L lid servo"])))
for n, v in rows: print(f"  {n:52s} {v:6.2f}" + ("   <-- UNDER 0.5" if v < 0.5 else ""))

print("\n== the rest of the head (others swept over pan, tilt, jaw; mm voxels)")
occupied("septum", S["septum"])
for n in ("pylon", "bail upright", "L lid servo", "pitch servo", "pitch bar"):
    occupied(n, np.vstack([S[n], mirror(S[n])]) if n in ("pylon", "bail upright", "L lid servo") else S[n])
occupied("tie-bar swept", np.vstack(list(tieY.values()))); occupied("bail swept", np.vstack(list(bailP.values()))); occupied("push-rod swept", np.vstack([np.vstack(list(rodP.values())), mirror(np.vstack(list(rodP.values())))]))

print("\n== under Morty's skin (2.1 mm at least)")
for n in ("bail upright", "L lid servo", "pylon"):
    skin(n, np.vstack([S[n], mirror(S[n])]))
skin("bail swept", np.vstack(list(bailP.values()))); skin("tie-bar swept", np.vstack(list(tieY.values()))); skin("pitch servo", S["pitch servo"])
