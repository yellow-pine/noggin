# Themes: the Skeleton and its Skins (grilled 2026-11-02 and 2026-11-03, #51, #805, #819)

> [!NOTE]
> **Upcoming (#51):** being designed, not built yet; #51 holds the whole spec. No Shell is drawn by hand: a Skin is
> cut from its Character's sculpt (docs/adr/0027). Morty's are cut; the eyeball caps are the only Shells a document
> wears until his go on (#850).

The Mech is one shared Skeleton that wears a Skin: a set of cosmetic Shells held on by magnets, swapped by pulling one
set off and pressing the other on. Both are parts in the model (model/printed), our own design, but for the
realistic Skeleton's skull and first two vertebrae, adapted from others' meshes under their licences (docs/adr/0023,
[Credits](credits.md)). A Theme is a Shape and a Palette for the Skeleton and for the Skin, any
Palette painting any Shape of its category (docs/adr/0022). A Preset names one: the Default build (mechanical in black, no
Skin, the Default Skin palette) and Morty (realistic in anatomical, his own Skin). *Upcoming (#913): Bart returns when
he has a sculpt to be cut from.* The default is the first Preset (model/geometry.py `PRESETS`): the model, the
[viewer](https://yellowpine.com/noggin/viewer/), every picture and the shopping list's filaments follow it unless you
pick another in the header; the viewer mixes any Shape with any Palette.

## Skeleton and Skin
- Skeleton, PETG: the eye gimbal with the eyeball cores and lid arms, the jaw arm and pivot, the neck, the Torso (the pack,
  the switch board and the power-path board alone since #858), the cranium tray (both Cores and the hub in the
  realistic skull's cranium, #858). It is the same under every Skin; the eye centres stay fixed (model/geometry.py `EYE_R`). Its Shapes:
  realistic, every part drawn as Bones, and mechanical, every part in boxes and cylinders (docs/adr/0020); its
  Palettes: anatomical, robot and black (PETG Basic Black throughout). *Upcoming (#893): the realistic Skeleton
  becomes a life-size bust from one anatomical source, warped into Morty.*
- Skin, PLA: a Character's Shells, cut from its sculpt (docs/adr/0027). The eyeball caps, every Character's, are the
  eye whites; a Character's caps may grow up to touching. Its Shapes: none, the Skeleton bare, and morty: his four
  Shells are cut ([Morty's Shells](#mortys-shells)), but no document wears them yet, so it draws the Skeleton as the
  document has it. *Upcoming (#850): the documents wear Morty's Shells.* *Upcoming (#913): Bart returns when he has a sculpt to be cut from.* *Upcoming (#917):
  Cansin returns when he has a sculpt to be cut from.* Its Palettes: morty and default (the four PLA Pure colours),
  each of the same six Colour groups (face, hair, pupils, clothes, eye whites, accessories), the accessories in one
  of the Palette's other filaments where its Character has none.

## Colour groups and filaments

Each Palette prints each of its category's Colour groups in one filament (at most four a Palette), each group's parts
as the model has them so far (model/geometry.py `THEMES` and `PRINTED`, the hexes the slicer's colour codes; the research behind the
picks: docs/adr/0022).

<!--{{ themes }}-->

<!--{# GitHub shows the line below; the site drops it for the table, which it builds from the code -->
The table of each Palette's filaments is [on the site](https://yellowpine.com/noggin/docs/face-design/).
<!-- #}-->

## Morty's Shells
His Skin is cut from his sculpt (`model/morty`, [Credits](credits.md)): its surface the outside from the crown to the
base, the wall grown inward, open underneath (docs/adr/0027, 0028). Four Shells, split along his cuts: the hair, above
and behind his hairline; the face, with his nose and ears; the chin, under the mouth line, which opens with the jaw;
and the shirt, under the collar, the whole fixed body. The face is open round each eye, where the eyeball cap is the
eye white and the lids stow behind the rim. *Upcoming (#850): their Seats, the gaps at the collar and the mouth
line that let the head and the jaw move, and room for them round the mechanism and the bones.* *Upcoming (#864): each Core's USB-C opening, and the Torso's, is cut through the Shells over it,
the hair and the shirt, for a plug.*

What the model has of them today (model/skin.py, model/printed/skin.py):
- the eyeball caps (eye whites, each Character's largest), each on its core's Seat, with a jagged seat in its front
  for a pupil, keyed by its shape with 0.15 mm of play a side and turned toward the other eye;
- his contours (model/contours.json) and the cuts they make on his sculpt (`cuts()`): the hair above and behind his
  hairline, each eye white its whole eye dome, the pupils, the jaw under the mouth line and the shirt under the
  collar, which colour the review's reference (model/review);
- the Motion regions (`MOTION`): the part each Shell moves with.

## Seats and magnets
- Every Shell sits on Seats (model/skin.py `SEATS`), the same for every Skin: on what carries it a 4x2 mm N52 disc
  flush in its pocket and three V-grooves round it; on the Shell its disc and three balls resting in the grooves,
  which take the shear and hold the discs 0.21 mm apart, so the magnets only preload it. Every Seat is flush in its
  carrier's surface, no pad raised on any Skeleton part, so the bare Skeleton shows at most a small circle (#852).
  The eyeball caps' Seats, in the cores' faces, are the only ones in the model. *Upcoming (#850): the Seats of
  Morty's Shells, on what carries each: the head, the jaw, the eyes and the Torso.*
- One polarity rule: the carrier's disc shows N to its Shell, reversed on the R Seat of each L/R pair (the caps), so
  a Shell on the other side's Seat is pushed off. Glue the discs in that way round.
- The hold check (model/test_report.py): each Shell's Seats pull it on with Magpylib's force at the Seats' gap
  (about 4.6 N a pair) at least twice its weight times the peak acceleration the sim reads at its centroid along
  every motion.
- The sim weighs every Shell (#830), and collides the Skeleton and the eyeball caps alone: a Skin's other Shells are
  drawn whole, so the servos carry the Skin. The caps' clearance is checked on their own shapes, 0.5 mm from every
  part but what carries them, at rest and with each servo at either end (model/printed/test_skin.py).

## Hardware
Inventory and the buy list: [Parts](build/parts.md#parts-to-buy). The one new purchase is the magnets, and the
filaments not owned yet.
