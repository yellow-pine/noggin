# Morty's Shells are cut in Python, seven of them

> Decided on 2026-11-27, ticket #850 (made while away). Cansin confirmed the collar and set the eye openings the
> same day (spec #893, "Decided by Cansin (2026-11-27, second grilling round…)"), and made the brows dark after
> looking at the review file (#850): four Shells became six. On 2026-11-28 he picked the hair in two pieces (spec
> #893, fourth round): seven. Builds on ADR 0027.

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
- **Seven Shells: the hair's crown and its back, face, a brow over each eye, chin, shirt.** The eyes get none: the
  eyeballs, the mechanism's own, are the eye whites.
- **The hair is two Shells, cut on a level seam at eye level** (Cansin, 2026-11-28). As one piece it is a hood, from
  the forehead over the crown down to the collar and forward to behind the ears, tucked in under a skull that is
  widest at eye level: no straight way takes it off (straight up, 19% of its surface has bone ahead of it; at the
  best slant, 40° back, 3.6%). Cut level, 10 mm above the eyes' centres (`shells.LEVEL`), the crown lifts straight
  up and the back slides straight back, each clear of the skull and the mechanism all the way, with the head at
  rest. 10 is the highest level in the range Cansin picked (0 to 20) at which the back comes no nearer the skull on
  its way than where it rests, 2.5 mm; at 20 it passes 0.4 mm from it. The seam is one the Sculpt does not have: a
  0.8 mm line round dark hair (ADR 0029). The crown's Seats face up on the skull's calvaria cap and the back's face
  back on its occiput, in bone (#874).
- **A brow is its own Shell, in the hair's filament** (Cansin: the brow's shape is right, and it should be dark). On
  this Sculpt a brow is a slab standing 1.4 to 2.3 mm proud of the forehead, 8 mm across, from over the nose round
  to the temple. Its Shell is the wall inside the slab's outline, cut through, and the face steps back a seam's gap
  from it (ADR 0029). The outline is traced on the original sculpt in a front view turned 40° toward the brow's
  side: the slab's foot, or its top's own edge where that hides the foot from the view. The plain front view sees
  the temple end edge on, where a gap measured in the view would open to three times its size on the surface.
- **A brow is glued in the face, on a tab behind each end** (ticket #850, made while away; proposed to Cansin on
  the ticket first). A brow is 8 mm across and a Seat 14, so it has none. Its own outline locates it, 0.2 mm off
  the face all round instead of a seam's gap, since it never moves against the face. Behind two stretches of it
  the face runs on as a tab 1 mm thick, 0.4 mm under the brow for the glue: from 4.4 to 11.9 mm in from its nose
  end, and its last 12 mm at the temple. A tab lies in the depth of the face's own wall beside the brow, which
  stands proud of it, so the wall is thickened nowhere. Elsewhere there is none: under the nose end's tip the skull
  stands 1.5 mm behind a brow's inside, and over the eye #967's lids stow 1.1 mm behind it. As built a tab keeps
  1.1 mm from the worn skull and 2.4 mm from the lids' shell. A brow comes off with the face, as a pupil with its
  cap.
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
- The hair in one piece, sprung off by hand: its sides have to open 5 to 16 mm each over the skull, which the model
  cannot show a 1.6 mm PLA hood doing.
- The hair in one piece, the skull slimmed along its way off: the skull loses its sides and back under the hair, and
  the tilt lever and its reaction bar stand in that way too.
- The brows left on the face and painted, or printed in a second filament in one piece: every Colour group is a
  Shell of its own in one filament (ADR 0022), so a Palette can change a brow's colour by swapping a spool.
- A brow as the proud slab alone, laid on a face that runs on under it: the face under a brow would be a surface
  the Sculpt does not have, the first we would invent, and it needs 1.4 to 2.3 mm more depth under a brow where
  1.1 mm is free over the eye.
- A ledge of face behind the whole brow: the same 1.1 mm over the eye.
- A magnet pair in each tab, so a brow pulls off alone: eight more magnets a head for a 1.5 g piece, and no balls
  fit to locate it.
- An eye Shell cut from each dome: the lids sweep where the dome's wall would be (#967).
- The face open to a 38.0 mm sphere about each eye's centre, so the lids stow hidden under its rim (#1037 to
  #1046): the opening stood 0.3 to 2.6 mm outside the dome's edge, and Cansin chose his eyes' own outline over
  hidden lids.
