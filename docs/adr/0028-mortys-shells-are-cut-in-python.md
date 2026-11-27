# Morty's Shells are cut in Python, four of them

> Decided on 2026-11-27, ticket #850 (made while away; Cansin to confirm the collar). Builds on ADR 0027.

ADR 0027 makes Morty's Sculpt his Skin. This is how the Shells are cut from it (`model/morty/shells.py`) and which
Shells there are.

- **No Blender.** `just ours` cuts the Shells in plain Python: the inside is measured on a grid with scipy and meshed
  with scikit-image, and the solids are cut with manifold3d (a new dependency, Apache 2.0). The bones need Blender
  (ADR 0025) because their finish is authored in a scene. The Shells are authored nowhere: they follow from the Sculpt,
  the cuts and the wall. So they build on every CI job and on a Mac with no heavy slot, in seconds.
- **The Sculpt's own triangles are the outside.** Only the inside is new geometry, so the silhouette is the Sculpt's
  exactly, as ADR 0027 asks. The inside is made lighter, within 0.05 mm, so each Shell stays under the 200,000 faces
  MuJoCo reads from an STL.
- **"Outside" is what open air reaches.** This Sculpt's brows are sheets buried 75 mm deep in its head, joined to its
  surface by pinholes. A wall grown from every surface would follow them in. Where a groove is deeper than 1 mm, the
  wall is filled behind it, so no wall is open.
- **Four Shells: hair, face, chin, shirt.** The eyes get none: the eyeball caps, the mechanism's own, are the eye
  whites, and the face is open round each eye so the lids stow behind its rim (#967).
- **The collar is the head's lower seam.** On this Sculpt the head meets the shirt at the collar's crease, with no
  neck showing between. So everything above the collar turns with the head, and the shirt is the whole fixed body:
  the Motion regions neck, shoulders and torso are one Shell.
- **No floor.** The shirt ends open on the base plane, the documents' z 0. The Torso's floor carries the Mech.

## Considered Options

- A Blender step beside the bones' finish (the first plan): one heavy slot on the Mac, no build on a job without
  Blender, and nothing in it needs a scene.
- A wall grown from every surface of the Sculpt: it follows the brows' buried sheets into the head.
- A neck Shell between the head and the shirt: this Sculpt shows no neck to cut one from.
- An eye Shell cut from each dome: the lids sweep where the dome's wall would be (#967).
