# Simulations run in Python; Fusion builds, pictures and referees

Once pins, axes and link lengths are right, every linkage of the Mech is a planar four-bar (lids, eyes, tilt, pan,
jaw), so posing parts is a rigid transform and no CAD kernel is needed to simulate. Fusion's API runs on its UI
thread only, a sweep there takes minutes and freezes the window (docs/research/2026-10-31-fusion-throughput.md).
So the simulation engine is Python in `model/`: one planar four-bar solver fed by `model/geometry.py`, part meshes
transformed rigidly, a KD-tree vertex screen (about 0.02 s per pair) with an exact closest-point check only on
pairs under twice the threshold, mass, centre of mass and inertia from the meshes with the spool densities. It
runs as `make sim` and in pytest in seconds, with no Fusion open, and carries the sweeps, contacts, transmission
curves, torque, clutch margin, tip-over and the electrical budget. Fusion keeps building the documents, making
the pictures, and stays available as the on-demand referee sweep (`make model-check`) after geometry changes.
Gate before the switch: the Python engine reproduces the recorded Fusion reports (model/reports: curves within
1 degree, minimum distances within 0.3 mm at the sampled poses, placements identical) as pytest fixtures.
Dependencies added: numpy, scipy, trimesh.

## Considered options

- Fusion as the engine: rejected, minutes per sweep on the UI thread.
- OCCT/FreeCAD headless: rejected, slower than Fusion on faceted bodies (88 s per pair measured).
- KD-tree only: rejected, a face-to-face overlap between vertices can slip through; exact check on near pairs.
- Replacing the Fusion sweep entirely: rejected by Cansin; it stays on demand as the referee.
