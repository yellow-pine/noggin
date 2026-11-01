# MuJoCo for the sim report: contacts, penetration, residuals, actuator force (2026-11-01, #149)

Version: `mujoco` 3.17.0 (uv.lock). `DOC/` = `https://mujoco.readthedocs.io/en/stable/`. Loops, stiff equalities, servo
actuators and tendons are in docs/research/2026-11-01-mujoco-loops.md; this note adds what the report reads.

## 1. Which pairs MuJoCo collides

- Candidates are body pairs (and explicit `pair`s). Filters: a collision function for the two geom types; a bounding
  sphere test "taking into account the contact margin"; "the two geoms cannot belong to the same body ... cannot
  belong to a parent and a child body, unless the parent is the world body", welded bodies counting as one; "geom
  pairs where neither body can move (both weld groups have no degrees of freedom) are skipped"; and
  `(contype1 & conaffinity2) || (contype2 & conaffinity1)`. DOC/computation/index.html#coselection
- So in model/mjcf.py a rigid group (the parts hung on one joint) never collides with itself, and two parts fixed to
  the world never with each other. The parent filter would also hide a part against the group it hangs on (a lid on
  the eye bracket once the eyes ride the tilt arm, the tilt horn on the pan turntable), so the report turns it off
  (`model.opt.disableflags |= mjDSBL_FILTERPARENT`): the pairs it then sees are exactly the pairs a joint moves apart.
  The drawn meshes (contype 0, conaffinity 0) never collide; only the CoACD pieces do.
- `mjDSBL_FILTERPARENT` "remove collisions with parent body": the bit disables the filter.
  DOC/APIreference/APItypes.html#mjtdisablebit

## 2. Contact distance and margin

- "The contact distance is positive when the two geoms are separated, zero when they touch, and negative when they
  penetrate." DOC/computation/index.html#contact . `mjContact.dist`: "distance between nearest points; neg:
  penetration"; `mjContact.geom`: the two geom ids. DOC/APIreference/APItypes.html#mjcontact
- `margin` is "the geometric inflation of the geom surfaces"; contacts are generated (and active) when the distance
  is below it; `gap` is an extra detection buffer beyond it. DOC/computation/index.html#comargingap , DOC/XMLreference.html#body-geom-margin
- So a pose's contacts within the report's clearance (0.1 mm, as the old engine's CLEARANCE_MM) come from setting
  `model.geom_margin` of the collision pieces to 0.1 mm and calling `mj_forward`: `data.contact[:data.ncon]`, each
  with its signed `dist`. The pose itself is reached with contacts off (mjcf.pose); the margin only widens detection
  for the one forward call, and nothing is stepped with it.
- A piece is a convex hull: a concave part's pieces can fill a little of its own clearance (model/test_mjcf.py
  TOUCH lists the pairs at rest), so the report compares each pair with its own rest reading. Measured against the
  exact meshes (model/engine/meshes.judge) the pieces both over-read (a lid shell's pieces 0.96 mm into the pupil the
  meshes clear by 0.48) and under-read (the R lower lid's pieces 0.03 mm deeper where the meshes go 1.86 mm into the
  eye bracket): model/test_report.py KNOWN_PAIRS lists each.

## 3. Residuals and actuator force

- Equality residual: `efc_pos` for `mjCNSTR_EQUALITY` rows; for a connect "the difference between the global 3D
  positions of these points". DOC/computation/index.html#coequality . With site connects it equals the sites'
  distance, which mjcf.residuals() reads (loops note 2).
- `data.actuator_force`: "actuator force in actuation space" (N.m on a hinge), clamped to `forcerange`.
  DOC/APIreference/APItypes.html#mjdata , DOC/XMLreference.html#actuator-general-forcerange
- Whole-model centre of mass: `data.subtree_com[0]` ("center of mass of each subtree"; body 0 is the world, whose
  subtree is every body). DOC/APIreference/APItypes.html#mjdata

## 4. The servo's figures (eyes/servo.py SPEC, docs/research/2026-10-31-electrical.md)

- Stall 1.0 kgf.cm and 0.14 s per 60 deg (428 deg/s) at 4.8 V; the actuator's forcerange is the stall (#148).
- Rated (continuous) 0.4 kgf.cm (model/sim.py RATED_KGF_CM): the report's threshold for the force a servo holds.
