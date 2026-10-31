# The model's engine is MuJoCo

> Supersedes ADR 0006's own engine (its planar four-bar solver, KD-tree contacts and mesh masses). Decided in the
> grilling of 2026-10-31, spec #146; tickets #147 to #151. MuJoCo simulates; Blender draws every picture.

ADR 0006 moved the simulation out of CAD into Python, and the engine grew in model/engine: our own four-bar solver,
contact screen, masses, cables and mating. That is a robotics simulator written by hand. MuJoCo is the best-known
open-source one (Apache-2.0), on PyPI as `mujoco` with wheels for macOS arm64 and Linux x86_64/aarch64 (3.17.0,
https://pypi.org/project/mujoco/), so the model moves onto it: libraries before custom code.

- **The model is MJCF.** `model/mjcf.py` builds one MJCF per document (stages.DOCS: the sub-assemblies and the Stage
  configurations) from our parts (model/printed, model/envelopes.py, written by `make ours`) and our pivots and
  frames (model/geometry.py), in metres (each mesh `scale` 0.001; MuJoCo has no fixed units, its default gravity is
  SI). Every part is a body at its placement. MuJoCo centres and aligns each mesh on its inertia and composes that
  offset into the geom, so a mesh drawn from its designed frame lands where that frame is put
  (https://mujoco.readthedocs.io/en/stable/XMLreference.html#asset-mesh).
- **Collisions through CoACD convex pieces.** MuJoCo collides a mesh by its convex hull (same page), which would fill
  every bore, slot and pocket of our parts. Each part is cut into approximately convex pieces by CoACD (MIT, `coacd`
  on PyPI, abi3 wheels for macOS arm64 and Linux x86_64/aarch64, 1.0.14, https://pypi.org/project/coacd/), each piece
  its own mesh asset, as CoACD's README advises for MuJoCo (https://github.com/SarahWeiii/CoACD, `--split`). The
  pieces collide (geom group 3, hidden in the viewer until toggled); the full mesh is drawn (group 2) and neither
  collides nor weighs. Decomposition takes seconds per part, so the pieces are cached in model/build/convex, each
  part decomposed again only when its mesh, clip or the CoACD settings change (CI caches them with model/build/ours).
- **Linkages, actuators, cables, mating** (#148): the four-bars are equality constraints, the servos position
  actuators with their torque limits, the leads spatial tendons with the real lengths as limits, each screw or pin a
  site pair whose distance must be zero (https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality).
- **The sim report is MuJoCo-native** (#149): contacts and penetration per pair, constraint residuals (a linkage
  that cannot close), actuator force against the torque limit, tip-over, all sampled per pose; the tests, the stamp
  and CI's skip-if-fresh are rebuilt on it, and the committed MJCF is the artifact.
- **Blender draws every picture** (#150): everything public-facing (README, docs, PR pictures: views, the Stage strip,
  GIFs) stays Blender's style B, posed from MuJoCo's poses instead of the old engine's. MuJoCo's viewer is for local
  checks only, with its built-in toggles: `make view` opens `python -m mujoco.viewer` on a document
  (https://mujoco.readthedocs.io/en/stable/python.html#interactive-viewer). Its visual config is one rgba per part from
  the colour table the pictures use (model/render/scene.py, Absolute Black drawn #2B2B2E) and a flat skybox in the
  pictures' background colour (scene.BG; https://mujoco.readthedocs.io/en/stable/XMLreference.html#asset-texture),
  under MuJoCo's default light.
- **Z-up, in metres.** The eyes-frame documents (noggin-eyes, noggin-mouth) are carried into the PT frame by one
  `<frame>` (stages.BASE_IN_EYES undone), so every model is Z-up as the Stages are, gravity along -Z; inside it the
  bodies keep the document's numbers.
- **The old engine retires** (#151) once the new one covers it. Until then both run. The first ticket's gate (model/test_mjcf.py): in
  every document each body sits where the old engine's pose puts it, within 0.1 mm, and no two parts that are not
  mounted to each other overlap at rest by more than 0.05 mm (MuJoCo's distance between their pieces; the pairs the
  pieces make overlap though the parts do not are listed with their measured clearance). That guard found the eyes
  sunk 5 mm into the desk base (stage 1: the bracket rail inside the plate); #147 lifts them onto the rail.

Dependencies added: mujoco, coacd.

## Considered options

- Keep growing model/engine: rejected, every new question (torque under gravity, a linkage under load, tip-over)
  is another hand-written solver.
- MuJoCo's renderer for the pictures, or tuned lights, materials and shadows for its viewer: rejected (2026-10-31,
  Cansin): Blender's style B is the look, and MuJoCo's viewer only has to tell the parts apart.
- MuJoCo colliding the raw meshes: rejected, the convex hull hides every clearance inside a part.
- A rigid flex per part (MuJoCo's non-convex collisions, same page, flexcomp): rejected for now, a mesh geom with
  convex pieces is the plain path and keeps each part one body with ordinary geoms.
