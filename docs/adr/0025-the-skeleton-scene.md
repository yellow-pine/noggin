# The realistic Skeleton is a Blender scene

> Decided with Cansin on 2026-11-03/04, spec #893 (its grilling on #872), ticket #873. Amends ADR 0009, 0019, 0020 and
> 0023.

The realistic Skeleton's bones are authored by hand, landmark by landmark, until Cansin has no more edits, and Cansin
audits them by turning them in Blender, not in code or pictures. So their source is one committed Blender scene,
`model/skeleton/skeleton.blend` (the Skeleton scene, GLOSSARY), not a Python module: its bones, each with a Warp shape
key (rewarp.py's thin-plate spline from the Landmarks, scipy loaded from the gitignored `.blender-site/`, never installed
into Blender) and a Sculpt key over it for hand edits, and a Finish per exported bone (a live Geometry Nodes SDF stack:
the cranium shelled, the mechanism carved round with clearance, crumbs dropped, meshed). CI fits it to the Mech it just
built: Blender opens the scene, deletes its Scene Mech, puts the Stage 3 document's parts where each bone sees them
(at rest and over every horn's range), runs every Finish and exports each bone (model/skeleton `finish()`, part of `just
ours`), which the pictures, the Viewer and the print files then draw. #873 moved the 3Demon skull and the atlas and axis
in unchanged and removed `model/printed/skull.py`; the bones themselves change from #874.

- **ADR 0009, sources only:** the scene is a source, binary and compressed, under a size cap (a test, no LFS). Its Scene
  Mech is the one derived copy the repo holds: a light, decimated copy of the Stage 3 Mech, so the scene opens fitted,
  which CI replaces on every run and never publishes. The numbers the gates share with the Finish (its voxel, clearance,
  wall) stay in `model/skeleton` and are set on the Finish at export.
- **ADR 0019 (and 0024):** nothing changes in what is published: the exported bones, their pictures and GLB, as before.
- **ADR 0020:** the realistic Skeleton's bones stay visual only; physics runs on the mechanical documents.
- **ADR 0023:** from #874 the bones are one source, BodyParts3D 4.0 (treated as CC BY-SA 2.1 JP, its own LICENSE.md),
  warped into Morty at life size (the cranium within ±10% of an adult's), in place of 3Demon and the atlas-axis. The real
  Morty sculpt is a fit reference kept local only (`docs/references`), never committed or published; a coarse hull of
  our own (low-poly, no sculpt detail) may be committed, so CI can check the bones lie inside him (Cansin, 2026-11-04).

## Considered Options

- Keep the bones in Python (skull.py's voxel carve): reviewable as text, but Cansin can't edit or audit a fit that lives
  in code, and every hand edit would have to be translated into numbers.
- Commit the finished bones: no Blender in CI, but they would go stale the moment the Mech moved, and they are an
  output (ADR 0009).
- Git LFS for the scene: past the free tier's bandwidth for a public repo's clones; a compressed scene under a cap
  instead.
