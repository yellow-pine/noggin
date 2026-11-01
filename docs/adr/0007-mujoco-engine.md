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
  site pair whose distance must be zero (https://mujoco.readthedocs.io/en/stable/XMLreference.html#equality). Each
  four-bar is a tree of hinges closed by a connect at the rocker pin, as MuJoCo asks for loop joints (a weld would lock
  it); the servos hold at their 4.8 V stall torque. `mjcf.pose` slews the commands quasi-statically with contacts off
  and holds them under gravity; its gate (model/test_mjcf.py): every LIMITS end closes within 0.05 mm, the joints match
  the old engine's solve within 0.5 degrees, the leads stay under their lengths and the mating sites within 0.2 mm
  (docs/research/2026-11-01-mujoco-loops.md).
- **The sim report is MuJoCo-native** (#149): contacts and penetration per pair, constraint residuals (a linkage
  that cannot close), actuator force against the torque limit, tip-over, all sampled per pose; the tests, the stamp
  and CI's skip-if-fresh are rebuilt on it, and the committed MJCF is the artifact. `make sim` measures each horn's
  sweep and the pan x tilt grid (model/mujoco_report.py) into each report's "mujoco" section, beside the old engine's until it
  retires, and commits the MJCF it measured as model/reports/<doc>.xml; one stamp covers both, now with model/mjcf.py,
  model/mujoco_report.py and the mujoco and coacd versions. model/test_report.py fails a pair whose pieces go 0.05 mm deeper
  than at rest (the pieces' own error is in the rest reading; an overlap at rest fails model/test_mjcf.py), a four-bar open over 0.05 mm, a servo holding more than
  its rated 0.4 kgf.cm (the stall 1.0 is the actuator's limit, reported beside it), a joint a swing at the rated
  428 deg/s leaves over 1 degree off the slow pose, and the centre of mass off the base footprint. The listed
  exceptions carry the exact meshes' reading (docs/research/2026-11-01-mujoco-report.md).
- **Blender draws every picture** (#150): everything public-facing (README, docs, PR pictures: views, the Stage strip,
  GIFs) stays Blender's style B, posed from MuJoCo's poses instead of the old engine's. MuJoCo's viewer is for local
  checks only, with its built-in toggles: `make view` opens `python -m mujoco.viewer` on a document
  (https://mujoco.readthedocs.io/en/stable/python.html#interactive-viewer). Its visual settings are one rgba per
  part, its spool's colour with black and white pulled in to #5A5A60 and #E8E8E8 (model/mjcf.py VIEW; the viewer has
  no outlines), and a flat skybox in the
  pictures' background colour (#F7F4EE; https://mujoco.readthedocs.io/en/stable/XMLreference.html#asset-texture),
  under a headlight that draws a face toward the camera in its exact colour (ambient 0.5, diffuse 0.5, no specular;
  MuJoCo's default dims and greys every colour).
- **Trajectories are the one source of motion** (#179, GLOSSARY): MuJoCo plays each gesture's writes (model/traces.py
  `commands`, at their own times) and the README hero's keys (model/render/hero.py, every 20 ms, a servo's PWM period)
  on each Stage. Each servo slews its command at its rated no-load speed (eyes/servo.py `Plant`, 4.8 V) and its
  position actuator follows under the load within the stall torque, contacts off. `make trajectories` writes every
  part's frame per 100 ms to model/build/trajectories/<doc>/<motion>.json (position in metres, quaternion w x y z,
  MuJoCo's world), stamped with the engine's inputs, the meshes and its own sources; a Stage whose files carry its stamp
  is skipped; the hero only on the Stages with the neck (2 and 3, #180). Blender's pictures (#150) and the web viewer's
  glTF (#180) will render from them. A full-speed step of the pan
  servo to its -40 limit carries the stage 3 head through the pan four-bar's toggle (it ends 41.5 degrees round instead
  of 24.9): the hero's eased keys stay clear (the head within 1.4 degrees of its keys; model/test_trajectories.py holds it to 2), and
  the head program (the second Core) must ease its pan moves likewise.
- **Z-up, in metres.** The eyes-frame documents (noggin-eyes, noggin-mouth) are carried into the PT frame by one
  `<frame>` (stages.BASE_IN_EYES undone), so every model is Z-up as the Stages are, gravity along -Z; inside it the
  bodies keep the document's numbers.
- **The old engine retires** (#151) once the new one covers it. Until then both run. The first ticket's gate
  (model/test_mjcf.py): in every document each body sits where the old engine's pose puts it, within 0.1 mm, and no two parts that are not
  mounted to each other overlap at rest by more than 0.05 mm (MuJoCo's distance between their pieces; the pairs the
  pieces make overlap though the parts do not are listed with their measured clearance). That guard found the eyes'
  rail 5 mm deep in the desk base (stage 1), a conflict with Cansin's photo settled for the build by #172: the desk
  eye bracket, its stem in the plate's slot (docs/model-notes.md, docs/research/2026-11-01-eyes-on-plate.md).

Dependencies added: mujoco, coacd.

## Considered options

- Keep growing model/engine: rejected, every new question (torque under gravity, a linkage under load, tip-over)
  is another hand-written solver.
- MuJoCo's renderer for the pictures: rejected (2026-10-31, Cansin): Blender's style B is the look. Its viewer
  starts from the settings above and may add shadows and materials (#150, 2026-11-01); it stays for local checks.
- MuJoCo colliding the raw meshes: rejected, the convex hull hides every clearance inside a part.
- A rigid flex per part (MuJoCo's non-convex collisions, same page, flexcomp): rejected for now, a mesh geom with
  convex pieces is the plain path and keeps each part one body with ordinary geoms.
