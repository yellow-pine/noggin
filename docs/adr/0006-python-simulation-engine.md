# Simulations run in Python; Fusion builds the documents

Once pins, axes and link lengths are right, every linkage of the Mech is a planar four-bar (lids, eyes, tilt, pan,
jaw), so posing parts is a rigid transform and no CAD kernel is needed to simulate. Fusion's API runs on its UI
thread only, a sweep there takes minutes and freezes the window (docs/research/2026-10-31-fusion-throughput.md).
So the simulation engine is Python in `model/`: one planar four-bar solver fed by `model/geometry.py`, part meshes
transformed rigidly, a KD-tree vertex screen (about 0.02 s per pair) with an exact closest-point check only on
pairs under twice the threshold, mass, centre of mass and inertia from the meshes with the spool densities. It
runs as `make sim` and in pytest in seconds, with no Fusion open, and carries the sweeps, contacts, transmission
curves, torque, clutch margin, tip-over and the electrical budget. Fusion keeps building the documents; the Fusion sweep is removed once the
condition below is met.
Gate before the switch: the Python engine reproduces the recorded Fusion reports (model/reports: curves within
1 degree, minimum distances within 0.3 mm at the sampled poses, placements identical) as pytest fixtures.
Dependencies added: numpy, scipy, trimesh.

## Considered options

- Fusion as the engine: rejected, minutes per sweep on the UI thread.
- OCCT/FreeCAD headless: rejected, slower than Fusion on faceted bodies (88 s per pair measured).
- KD-tree only: rejected, a face-to-face overlap between vertices can slip through; exact check on near pairs.
- Keeping the Fusion sweep as an on-demand referee: rejected (2026-10-31, second pass): a sweep that takes minutes
  and freezes the window gives false comfort and never gets run. Condition met 2026-10-31 (T14): the engine passes
  the gate on the three recorded documents and sweeps them in 8.0 s wall (M-series Mac, 10 cores) against the 150 s
  the Fusion sweeps recorded (18.8x; all six documents including the Stage configurations in 24 s), so check.py and
  sweep.py are deleted, the recorded reports stay as frozen gate fixtures (model/engine/test_gate.py), `make sim`
  green is the Stage criterion, and Fusion only builds the documents.

## Update 2026-10-31 (#45, #47)

`make sim` writes model/reports/<doc>-sim.json, committed and stamped with a hash of its inputs (geometry tables,
engine code, part fingerprints, the Core program's gestures); CI fails on a reported collision, an over-length lead,
a mating mismatch (#67: holes and shafts coaxial within 0.2 mm, servos in their pockets) or a stale stamp. Every picture is rendered in Blender from the engine's poses (docs/model-notes.md).

## Update 2026-10-31 (#50, #58)

CI runs `make sim` itself on our own geometry: the CadQuery printed parts (model/printed) and hardware envelopes
(model/envelopes.py), written by `make ours`.

## Update 2026-10-31 (#97): our model is the source

Once our parts matched the designer's meshes within 0.3 mm with every joint mated (tag `stock-parity`), the model
stopped checking itself against them. The gate (model/printed/test_gate.py and model/engine/test_gate.py, the latter
on the recorded Fusion reports), the Bambu STEP meshing (model/build/steps) and the guide sheets are deleted, and
nothing reads docs/references. `make sim` runs on our geometry everywhere, so the committed reports are ours. The
mating check fits the features our parts declare (each part's features(), model/envelopes.py FEATURES) on our meshes,
and the horn limits are our own, each with its reason (geometry.LIMITS). The recorded Fusion reports that stay
(noggin-eyes, noggin-pan-tilt) are linkage and mass fixtures
(the Fusion documents, history).
