# Morty's Shells are cut in Python, four of them

> Decided on 2026-11-27, ticket #850 (made while away). Cansin confirmed the collar and set the eye openings the
> same day (spec #893, "Decided by Cansin (2026-11-27, second grilling round…)"). Builds on ADR 0027.

ADR 0027 makes Morty's Sculpt his Skin. This is how the Shells are cut from it (`model/morty/shells.py`) and which
Shells there are.

- **No Blender.** `just ours` cuts the Shells in plain Python: the inside is measured on a grid with scipy and meshed
  with scikit-image, and the solids are cut with manifold3d (a new dependency, Apache 2.0). The bones need Blender
  (ADR 0025) because their finish is authored in a scene. The Shells are authored nowhere: they follow from the Sculpt,
  the cuts and the wall. So they build on every CI job and on a Mac with no heavy slot, in seconds.
- **The Sculpt's own triangles are the outside.** Only the inside is new geometry, so the silhouette is the Sculpt's
  exactly, as ADR 0027 asks. The inside is made lighter, within 0.05 mm, so each Shell stays under the 200,000 faces
  MuJoCo reads from an STL.
- **The Shells are cut from the Sculpt's outer skin, what open air reaches.** Behind each brow this Sculpt has a
  pocket: a slab of empty space reaching 86 mm back and to the middle of the head, joined to the surface by cracks
  under 0.8 mm wide at the brow's inner end (the original has them too, so the adoption did not make them). A wall
  grown from every surface would follow a pocket in. So a pocket's walls are left out whole and each crack is capped
  where it leaves the outside (#850, `outer()`): a brow is its ridge on the face and nothing behind it.
- **Four Shells: hair, face, chin, shirt.** The eyes get none: the eyeballs, the mechanism's own, are the eye
  whites.
- **An eye's opening is the Sculpt's own dome's edge, exactly** (Cansin): the face is open inside each eye white's
  cut and no further. So the lids cannot hide whole behind the rim: an open lid's edge rests at the rim and shows
  there as a sliver (#967). The face's wall comes to 36.3 mm from each eye's centre at its nearest (38.0 before), and
  what turns under the rim keeps a worn Shell's 0.5 mm inside that.
- **The collar is the head's lower seam** (confirmed by Cansin). On this Sculpt the head meets the shirt at the
  collar's crease, with no neck showing between. So everything above the collar turns with the head, the neck's skin
  too, sliding round the neck's bones, which never move; and the shirt is the whole fixed body.
- **No floor.** The shirt ends open on the base plane, the documents' z 0. The Torso's floor carries the Mech.

## Considered Options

- A Blender step beside the bones' finish (the first plan): one heavy slot on the Mac, no build on a job without
  Blender, and nothing in it needs a scene.
- A wall grown from every surface of the Sculpt: it follows the pockets behind the brows into the head.
- Telling a pocket's walls by how deep they lie under the open air (the first cut, #1037): where a pocket comes
  within the wall's thickness of the outside, at each brow's inner end, its walls counted as outside, and the face
  held 0.1 cm² of them with a spur of wall to 2.4 mm deep behind.
- A neck Shell between the head and the shirt: this Sculpt shows no neck to cut one from.
- An eye Shell cut from each dome: the lids sweep where the dome's wall would be (#967).
- The face open to a 38.0 mm sphere about each eye's centre, so the lids stow hidden under its rim (#1037 to
  #1046): the opening stood 0.3 to 2.6 mm outside the dome's edge, and Cansin chose his eyes' own outline over
  hidden lids.
