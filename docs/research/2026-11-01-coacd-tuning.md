# CoACD tuned until MuJoCo's contacts read what the meshes do (2026-11-01, #190)

Versions: `coacd` 1.0.14 and `mujoco` 3.17.0 (uv.lock). `COACD/` = `https://github.com/SarahWeiii/CoACD/blob/1.0.14/`;
`DOC/` = `https://mujoco.readthedocs.io/en/stable/`, checked against the 3.17.0 sources of its pages
(`https://github.com/google-deepmind/mujoco/blob/3.17.0/doc/`). Measured on the Mac (M-series, other agents sharing the
machine, so the seconds are upper bounds) against model/engine/meshes.judge, the old engine's exact-mesh check.

## 1. What CoACD's parameters do (primary sources)

- **threshold** (default 0.05): "concavity threshold for terminating the decomposition (0.01~1)" (COACD/README.md).
  A part is cut again while its cost `h > threshold` (COACD/src/process.cpp#L564); the cost is the larger of a sampled
  surface Hausdorff distance between the part and its hull and a volume term `0.3 * cbrt(3 |V_hull - V| / 4 pi)`
  (COACD/src/cost.cpp#L9-L90, `rv_k = 0.3` in COACD/src/config.h#L58). It is **normalised**: the mesh is scaled so its
  longest side is 2 (COACD/src/model_obj.cpp#L622-L646), so 0.05 lets a hull stray 2.5 % of the part's longest side,
  1.2 mm on a 48 mm lid, 2.9 mm on the 115 mm eye bracket.
- **real_metric** (default False): the threshold in the mesh's own units; CoACD converts it to
  `threshold * 2 / longest side * 0.8` (COACD/public/coacd.cpp#L79-L86). Our meshes are in mm, so `threshold=0.15,
  real_metric=True` asks for 0.15 mm whatever the part's size. The README's news calls it "ideal for ... CAD models".
- **preprocess_mode** (default "auto") and **preprocess_resolution** (default 50): "auto" runs a manifold check and, when
  it fails, rebuilds the mesh from a voxel grid of that resolution (COACD/public/coacd.cpp#L93-L99). The check asks for
  every directed edge once and its opposite present (COACD/src/process.cpp#L21-L75). At 50 voxels a 48 mm lid is
  remeshed at ~1 mm. The README: "Make sure your input mesh is 2-manifold solid if you set -pm to off".
- **resolution** (default 2000): samples for the Hausdorff term. **mcts_iterations / mcts_max_depth / mcts_nodes**
  (Python defaults 150 / 3 / 20, COACD/python/package/__init__.py#L81-L100): the cut search; the README's tip is to
  raise them for fewer pieces, not for accuracy. **merge** (default True) and **max_convex_hull** (-1): merging stops
  once a merge would exceed the threshold, so it never trades accuracy (COACD/src/process.cpp#L360-L378).
  **decimate / max_ch_vertex, extrude, apx_mode "box", pca**: coarsen or reshape the hulls; not for clearance.
- **seed**: CoACD is stochastic; a fixed seed repeats the pieces for the same input (README tip 5).
- The Hausdorff term measures from the hull's surface to the part's *surface* (COACD/src/hausdorff.h#L149-L190), so a
  hull that fills a shallow corner next to another face of the same piece reads as close to the part: no threshold
  bounds how far it fills that corner.

## 2. MuJoCo settings that touch the reported distance

- `margin` (default 0): contacts are generated within it; the two geoms' margins are summed
  (DOC/computation/index.html#coMarginGap). The report sets 0.1 mm on each piece, so a pair is seen from 0.2 mm in.
  `gap` only adds inactive contacts beyond the margin (DOC/XMLreference.html#body-geom-gap): nothing to gain here.
- `nativeccd` (default on): GJK/EPA, which "computes the correct values at all distances"; the legacy MPR pipeline
  does not (DOC/computation/index.html#coDistance). `ccd_iterations` 35 and `ccd_tolerance` 1e-6
  (DOC/XMLreference.html#option-ccd_iterations): raising them to 2000 and 1e-10 changed no reading by more than
  0.014 mm. `multiccd` (on by default) adds points to a contact between two flat faces "to model edge or surface
  contacts" (DOC/computation/index.html#coMultiCCD), and those points carry their own depth: the eye horn lying flat on
  the eyeball bar read 0.198 mm in with it and 0.020 without (the two pieces' common region is 0.02 mm thick). The
  report wants a distance, not a contact patch, so it turns multiccd off (`mjDSBL_MULTICCD`) with the parent filter.
- `maxhullvert` (default -1, unlimited): only coarsens a hull (DOC/XMLreference.html#asset-mesh-maxhullvert).
  `inertia` changes masses, not distances. A penetration's `dist` is EPA's depth: the shortest move that parts the
  two convex pieces (DOC/APIreference/APItypes.html#mjcontact). judge reports the deepest vertex instead, which is
  never more and misses two edges that cross.
- MuJoCo collides a mesh by its convex hull and asks for non-convex objects as a union of convex geoms, naming CoACD
  (DOC/computation/index.html#coDecomposition). Mesh SDF octrees serve only the tactile sensor
  (DOC/XMLreference.html, sensor/tactile), so CoACD stays the way.

## 3. What was measured

Every pair a joint moves apart, at rest and at every LIMITS end (and the neck's corners), in noggin-eyes,
noggin-pan-tilt and noggin-mouth: MuJoCo's per-pair minimum (model/mujoco_report.py) against judge's signed reading,
both clamped to the 0.2 mm detection band.

| setting | worst disagreement | CoACD CPU |
| --- | --- | --- |
| CoACD defaults (main before #190) | 4.6 mm (lid shells), 3.3 (lower lid / bracket), 2.7 (jaws), 2.1 (plate / turntable), 1.4 (lid / pupil: the false 0.96 overlap), 0.17 (horn / servo) | 860 s, eyes alone |
| + degenerate faces dropped | eyeball / bracket 0.94 -> 0.78 (judge 0.77), servo bracket / lower lid now 0.068 (judge 0.067); lids still 3.7 | 454 s, eyes |
| every part at 0.15 mm real metric | base plate 6045 pieces, eyeballs 1700 each, servo 852: 16 000 pieces in the eyes model, out of MuJoCo's arena | over 3000 s |
| chosen (5) | 0.05 mm everywhere but the pairs of 4 | about 5 min wall, all six documents |

- The two lids' and two eyeballs' meshes from `make ours` each carry one or two zero-area slivers on an OCCT seam, so
  CoACD's manifold check fails and "auto" voxel-remeshes them at ~1 mm. `mesh.update_faces(mesh.nondegenerate_faces())`
  makes every part a closed 2-manifold (all 33 checked) and CoACD keeps its exact surface.
- Upper lid alone, real-metric thresholds: 0.3 mm 202 pieces 23 s (strays 0.24 mm); 0.15 mm 514 pieces 33 s (0.19 max,
  0.065 p99); 0.08 mm 1782 pieces 62 s; 0.05 mm 5496 pieces 301 s. Normalised 0.05 / 0.02: 37 / 102 pieces, strays
  1.18 / 0.48 mm. The horn: 0.15 mm 83 pieces (0.10), 0.08 mm 241 pieces (0.07) 66 s. merge on or off: the same.
- A fine cut leaves a few flat slivers (fewer than 4 vertices), which MuJoCo refuses to compile; they are dropped.
- With thousands of pieces the lids nest in 7000 contacts at the report's margin, past MuJoCo's arena in mj_forward;
  the report now runs `mj_kinematics` and `mj_collision` only (no constraints are needed to read distances).

## 4. Where they still differ, and who is right

Checked per pair: the hull intersection of MuJoCo's two deepest pieces (scipy halfspace intersection), and whether its
points lie inside each exact mesh (judge's own ray parity, `meshes.inside`).

- **The meshes overlap where judge says they touch** (MuJoCo right). Before #189's fix (lid limits -49..+39): the lid
  ears crossed 3.0 mm at -39 and -49, where judge read 0 and 1.39 (a 3 x 5 x 5 mm region inside both lids, with no
  vertex of either inside the other); the upper lid went 1.14 mm into the eye bracket (judge 0.78) and the lower lid
  1.93 mm (judge 1.86). At #189's limits (-31..+31) there is still overlap, and judge reads all of it as 0: the ears
  1.20 mm at +29, 1.09 at +31 and 0.28 at -31; the upper lid 0.36 mm and the lower lid 0.11 mm into the eye bracket
  at +31. The build runs the lids without binding, so these are shape errors, open on #210. #151 loses nothing by
  retiring judge.
- **The pieces fill a corner the meshes leave open** (judge right): 0.93 mm in the turntable's recess corner over the
  bearing's rim; 0.31 mm in the top jaw's hinge-pin hole; the turntable 0.057 mm proud of its mesh under the tilt horn
  at tilt -60 (0.118 read, 0.174 clear); 0.07 mm on the eyeball against the desk bracket at +-20, where the meshes
  touch. Each is a designed contact, or a clearance the report compares with its own rest reading. The first three did
  not move between 0.3 and 0.15 mm.
- Settled: the false 0.96 mm lid-into-pupil is gone (lid / pupil and lid / eyeball now read the meshes' 0.48 mm, out
  of the band); the right lower lid's 1.86 mm at the old +39 read 1.93; the horn on its servo shaft reads 0.237 against
  0.216. The report's pieces-only exceptions from before (the pupils, the eyeball bar on the rail, the plate under the
  upright, the tilt horn over the turntable) all go; the eyeball's 0.07 mm on the desk bracket at +-20 takes their place
  (it is past the report's 0.05 mm, within the test's contact band).

## 5. Chosen, and its cost

- Every part: CoACD's defaults (threshold 0.05 normalised, seed 0) on the degenerate-free mesh. Finer, in mm with
  real_metric: the horn 0.08; the two lids 0.15; the base plate, both eye brackets, the pan turntable and the jaws 0.3.
  The report measures with multiccd off and with `mj_collision` only.
- `test_the_pieces_read_the_clearance_the_exact_meshes_do` in model/test_mjcf.py pins it in every moving document. It
  lists section 4's pairs: DEEPER may read deeper up to a cap, never shallower; FILLED gets its own tolerance. It
  checks rest and the LIMITS ends; the report's sweep steps between them are not compared with judge.
- Cost on the shared Mac: a cold `python -m model.mjcf` over the six documents takes about 5 min wall. That makes
  4518 pieces, 24 MB in model/build/convex (base plate 1565, lower lid 591, upper lid 514, eye bracket 493, desk eye
  bracket 346, turntable 299, horn 241). The committed MJCFs grow from 1.0 to 6.6 MB. The agreement test runs about
  150 s over the six documents, and `make sim` about 6.5 min of CPU. The cache is keyed on the mesh CoACD gets and its
  settings, so only a changed part is cut again.
