# MuJoCo for the four-bar: loops, stiff equalities, servos, tendons (2026-11-01, #148)

Version: `mujoco` 3.17.0 (uv.lock), the same release `stable` documents (changelog #version-3-17-0-october-22-2026).
`DOC/` = `https://mujoco.readthedocs.io/en/stable/`; `SRC/` = `https://github.com/google-deepmind/mujoco/blob/3.17.0/`.
Python names were checked against the installed 3.17.0 bindings (`dir()` and docstrings), and with a throwaway
MjSpec four-bar (crank, coupler, rocker, site connect, position servo, cable tendon) that ran clean.

## 1. Closing the loop: connect, not weld

- Kinematic loops are not allowed in the tree; "if loop joints are needed they should be modeled with equality
  constraints". DOC/overview.html#kinematic
- connect "connects two bodies at a point, effectively creating a ball joint outside the kinematic tree", residual
  dim 3. weld (dim 6) "suppress[es] all relative degrees of freedom". DOC/computation/index.html#coequality
- So the four-bar is a tree (crank hinge on world, coupler hinge on crank, rocker hinge on world) plus one connect at
  the coupler/rocker pin. The rocker's own hinge supplies the rotation; a weld there would lock the mechanism. Two
  connects on one body pair make a hinge, three or more amount to a weld. DOC/computation/index.html#coequality
- The docs advise against replacing tree joints with equalities ("slower and less accurate"); that is about joints
  the tree can hold. The loop-closing pin is the case equalities are for. DOC/computation/index.html#coequality
- Attributes: `body1` + `anchor` (body2 optional, default world), or `site1` + `site2`; `name`, `class`, `active`,
  `solref`, `solimp`. DOC/XMLreference.html#equality-connect
- `anchor` is in body1's local frame; the constraint "is assumed to be satisfied" at qpos0, "which lets the compiler
  compute the associated anchor point for body2". DOC/XMLreference.html#equality-connect-anchor . In source:
  setKinematics0 puts the anchor in world at qpos0 and stores it in body2's frame as eq_data[3..5]
  (SRC/src/engine/engine_setconst.c#L1184-L1191); at runtime both points go to world through xpos/xmat
  (SRC/src/engine/engine_core_constraint.c#L462-L491).
- Site form: the sites "are not required to overlap at the default configuration ... will 'snap together' at the
  beginning", and editing `site_pos` at runtime moves the constraint (eq_data then unused).
  DOC/XMLreference.html#equality-connect-site1 . Added in 3.2.3 (DOC/changelog.html#version-3-2-3-sep-16-2024);
  site-semantic bugs fixed in 3.2.4 (DOC/changelog.html#version-3-2-4-oct-15-2024).
- Planar redundancy: connect always adds 3 rows (SRC/src/engine/engine_core_constraint.c#L548-L564). With all hinge
  axes parallel the out-of-plane row has a zero Jacobian (checked: `efc_J` row all 0) and residual 0, so it is inert.
  Redundant rows are not a problem because constraints are soft: the regularizer R > 0
  (DOC/computation/index.html#soprimal) and the cost is "strongly convex in the M-norm"
  (DOC/computation/index.html#soalgorithms), so the solution is unique. Inferred from those two; the docs do not
  discuss redundant rows by name.

## 2. A stiff connect (static violation < 0.05 mm)

- Model: `aref = -b v - k r`, `d` = impedance in (0, 1) from solimp, clamped to [0.0001, 0.9999].
  DOC/modeling.html#csolver , DOC/modeling.html#csolverimpedance
- solref (default `0.02 1`): positive = (timeconst, dampratio), `b = 2/(dw tc)`, `k = d(r)/(dw^2 tc^2 dr^2)`;
  negative = (-stiffness, -damping), `b = damping/dw`, `k = stiffness d(r)/dw^2`. DOC/modeling.html#csolverreference
- Violation at rest, constant d: `r = au (1 - d) tc^2 dr^2` (positive form), `r = au (1 - d) / stiffness` (direct).
  `au` = the unconstrained acceleration in constraint space. DOC/modeling.html#csolverreference
- "timeconst should be at least two times larger than the simulation time step"; refsafe enforces
  `max(solref[0], 2*timestep)` per row. DOC/modeling.html#csolverreference , DOC/XMLreference.html#option-flag-refsafe .
  The clamp applies only to the positive form and not under integrator="discrete"
  (SRC/src/engine/engine_core_constraint.c#L1906-L1908), so the direct form is not clamped.
- Worked numbers (au ~ g = 9.81, dr = 1): default solref/solimp (tc 0.02, d0 0.9) gives 0.39 mm, too soft.
  tc 0.004 (2 x the default 0.002 step) with default solimp gives 0.016 mm; tc 0.02 with solimp `0.99 0.99` gives
  0.039 mm. Through the loop's lever ratios au can be several g, so measure it (below) rather than trust the estimate.
  The throwaway four-bar (dt 1 ms, solref `0.002 1`, servo holding) read 0.0006 mm.
- solimp (default `0.9 0.95 0.001 0.5 2`): d goes d0 -> dw over `width` (metres for an equality). Set d0 = dw for
  constant stiffness. DOC/modeling.html#csolverimpedance
- `o_solref`/`o_solimp` and the `override` flag "appl[y] only to contacts, and not to other types of constraints":
  no use for equalities. DOC/modeling.html#coverride , DOC/XMLreference.html#option-o-solref
- Solver: Newton is the default and "the best choice for most models ... usually around 5, and rarely more than 20"
  iterations, "used with aggressive tolerance values, say 1e-10". DOC/modeling.html#calgorithms ; defaults
  iterations 100, tolerance 1e-8. DOC/XMLreference.html#option-iterations , DOC/XMLreference.html#option-tolerance
- Reading it: after mj_forward, rows with `efc_type == mjCNSTR_EQUALITY` and `efc_id == eq id` hold the residual in
  `efc_pos` (pos1 - pos2, world, 3 rows for connect). DOC/APIreference/APItypes.html#mjtconstraint ,
  DOC/APIreference/APItypes.html#mjdata , SRC/src/engine/engine_core_constraint.c#L402 . With sites, the same number is
  `norm(data.site_xpos[a] - data.site_xpos[b])` (checked equal).

## 3. Position servos

- `<position>` sets gain `kp`, bias `0 -kp -kv`, so force = `kp (ctrl - length) - kv lengthdot`.
  DOC/XMLreference.html#actuator-position , DOC/computation/index.html#geactuatorforce . Hinge setpoints on purely
  rotational transmissions are "interpreted on the circle". DOC/XMLreference.html#actuator-position
- `forcerange` clamps the actuator output when `forcelimited` (auto: on if forcerange is set and autolimits);
  `ctrlrange`/`ctrllimited` clamp the control. kv forces are clamped by forcerange; actuator `damping` is not.
  DOC/XMLreference.html#actuator-general-forcerange , DOC/XMLreference.html#actuator-general-forcelimited ,
  DOC/XMLreference.html#actuator-general-damping , DOC/modeling.html#cforcerange . Output: `data.actuator_force`.
  DOC/computation/index.html#geactuation
- `gear` scales length, moment arm, velocity and force. DOC/XMLreference.html#actuator-general-gear
- `inheritrange` X > 0 sets ctrlrange to the joint range about its midpoint, scaled by X; joint/tendon only.
  DOC/XMLreference.html#actuator-position-inheritrange
- MjSpec: `a = spec.add_actuator(name=..., target='crank', trntype=mujoco.mjtTrn.mjTRN_JOINT)`, then
  `a.set_to_position(kp=..., kv=...)` (also dampratio, timeconst; -1 = unset; Python takes `inheritrange` as a bool, C
  `mjs_setToPosition` a double). `a.forcerange = [lo, hi]`. DOC/APIreference/APIfunctions.html#mjs-settoposition
- Joint: `body.add_joint(type=mjJNT_HINGE, axis=..., armature=..., damping=...)`. Armature "significantly improves
  simulation stability, even for small values". DOC/XMLreference.html#body-joint-armature
- Stability: implicit/implicitfast are implicit in velocity only, so they cover kv and damping, not kp
  (DOC/XMLreference.html#actuator-position-kv , DOC/computation/index.html#geintegrators). Explicit limit
  `h <~ 2/omega_max` (DOC/computation/index.html#geintegrators); for a servo `omega = sqrt(kp/I)` with I the reflected
  inertia plus armature (inferred). Only integrator="discrete" (new in 3.13.0) is implicit in position, so kp is stable
  "far beyond the explicit stability limit". DOC/changelog.html#version-3-13-0-september-8-2026

## 4. Spatial tendons as cables

- `<tendon><spatial>`: shortest path through `site` (and wrapping `geom`) children; `range` with `limited`.
  DOC/XMLreference.html#tendon-spatial , DOC/XMLreference.html#tendon-spatial-range
- A limit is one-sided: the residual is the distance to the nearer bound, active only when violated (or within
  margin). For a cable use `range="0 Lmax"`. Do not fake an equality with a narrow range.
  DOC/computation/index.html#colimit . Its stiffness is `solreflimit`/`solimplimit`.
- Length: `data.ten_length` (ntendon). DOC/APIreference/APItypes.html#mjdata
- MjSpec: `t = spec.add_tendon(name=..., range=[0, L], limited=mujoco.mjtLimited.mjLIMITED_TRUE)`, then
  `t.wrap_site('s0'); t.wrap_site('s1')` (spatial follows from the site wraps; checked). C: mjs_addTendon,
  mjs_wrapSite. DOC/APIreference/APIfunctions.html#mjs-wrapsite

## 5. Sites

- `body.add_site(name=..., pos=[...])` returns an MjsSite (checked); `data.site_xpos` (nsite x 3), or
  `data.site('name').xpos`. DOC/APIreference/APItypes.html#mjdata , DOC/python.html#pymodeledit

## 6. Posing runs and inertia

- No contacts: `model.opt.disableflags |= mujoco.mjtDisableBit.mjDSBL_CONTACT` (or `spec.option.disableflags`), MJCF
  `<flag contact="disable"/>`: "disables collision detection and all standard computations related to contact".
  DOC/APIreference/APItypes.html#mjtdisablebit , DOC/XMLreference.html#option-flag-contact
- `inertiafromgeom` auto infers from geoms "only when the inertial element is missing"; true always infers.
  DOC/XMLreference.html#compiler-inertiafromgeom . Geom `mass` sets that geom's density; geom mass is used only at
  compile time to infer the body's. DOC/XMLreference.html#body-geom-mass
- MjSpec trap: a body counts as having an inertial only when `body.ipos` is set (it defaults to NaN). `body.mass` and
  `body.inertia` without `ipos` are overwritten by the geoms (checked: 0.5 kg became 0.0042).
  SRC/src/user/user_objects.cc#L3045-L3048 . Set `ipos`, `mass`, `inertia` together, or `mass` on the geoms.
