# Themes: the Skeleton and its Skins (grilled 2026-11-02 and 2026-11-03, #51, #805, #819)

> [!NOTE]
> **Being designed, not built yet.** Morty's Shells are in the model (#665); Bart's (#807) and Cansin's (#813) follow.
> #51 holds the whole spec.

The Mech is one shared Skeleton that wears a Skin: a set of cosmetic Shells held on by magnets, swapped by pulling one
set off and pressing the other on. Both are CadQuery parts in the model (model/printed), adapted from our own design;
nothing comes from other people's designs. A Theme is a Shape and a Palette for the Skeleton and for the Skin, any
Palette painting any Shape of its category (docs/adr/0022). A Preset names one: Cansin's build (mechanical in black,
the cansin Skin; Morty's Shape stands in for its Shells until they exist, #813), Morty and Bart (each realistic in
anatomical, its own Skin). The model, the [viewer](https://yellowpine.com/noggin/viewer/) and every picture draw the
next Mech in one, Cansin's build unless another is picked; the viewer mixes any Shape with any Palette.

## Skeleton and Skin
- Skeleton, PETG: the eye gimbal with the eyeball cores and lid arms, the jaw arm and pivot, the neck, the Torso (the packs
  and the switch board since #858), the cranium tray (both Cores in the realistic skull's cranium, #858). It is the same under every Skin; the eye centres stay fixed (model/geometry.py `EYE_R`). Its Shapes:
  realistic, every part drawn as Bones, and mechanical, every part in boxes and cylinders (docs/adr/0020); its
  Palettes: anatomical, robot and black (PETG Basic Black throughout).
- Skin, PLA: the head shell with hair, the ears, the nose, the eyeball caps, separate pupils, the lid covers, the mouth
  covers, the collar or shirt. A Character's eyeball caps may grow up to touching. Its Shapes: morty, his face with
  ears, nose and lids, his hair and jagged pupils, his shirt and collar, his eye whites; bart, his face with the spikes
  and lids, his shirt and collar, his eye whites, his pupils as dots; cansin, Cansin in Rick and Morty style with
  sunglasses on the collar (#813). Its Palettes: morty, bart and cansin, each of the same six Colour groups (face,
  hair, pupils, clothes, eye whites, accessories), the accessories in one of the Palette's other filaments where its
  Character has none.

## Colour groups and filaments

Each Palette prints each of its category's Colour groups in one filament (at most four a Palette), each group's parts
as the model has them so far (model/geometry.py `THEMES` and `PRINTED`, the hexes the slicer's colour codes; the research behind the
picks: docs/adr/0022).

<!--{{ themes }}-->

<!--{# GitHub shows the line below; the site drops it for the table, which it builds from the code -->
The table of each Palette's filaments is [on the site](https://yellowpine.com/noggin/docs/face-design/).
<!-- #}-->

## Morty's Shells
In model/printed/skin.py, on Stage 3 (#665), each drawn in what carries it, shaped from his model sheet (#844; every
size inferred):
- the head: round from the front, its face flat over the eyes and its cranium round behind, the muzzle over the jaw and
  the head mount, square from above where the mouth servo's corners need it; 140 x 140 x 150 mm
  but for the ears (model/printed/test_skin.py);
- the face (face): the head's front under the hairline, the eyes' openings round everything the lids and their covers
  reach, his round nose, a C-shaped ear each side, the mouth's opening; it comes off forward;
- the hair (hair): the head's top and back over his hairline, from over the forehead down behind the ears to the
  nape, standing 1.5 mm proud of the face; it comes off upward, so it goes on last;
- the eyeball caps (eye whites, each Character's largest) with a jagged pupil (pupils) glued in each, keyed by its
  shape in its seat with 0.15 mm of play a side and turned toward the other eye;
- a cover on each lid (face): the lower lid's whole, the upper lid's top band alone, since the lower lid passes outside
  the upper one when a shut eye looks down;
- the mouth cover (face), his chin under the jaw, in the face's mouth opening;
- the shirt (clothes), his T-shirt: a front and a back half round the Torso, its sides and shoulders rounded, each
  with its half of the round crew neck's collar.

## Seats and magnets
- Every Shell sits on Seats (model/skin.py `SEATS`), the same for every Skin: on what carries it a 4x2 mm N52 disc
  flush in its pocket and three V-grooves round it; on the Shell its disc and three balls resting in the grooves,
  which take the shear and hold the discs 0.21 mm apart, so the magnets only preload it. Every Seat is flush in its
  carrier's surface, no pad raised on any Skeleton part, so the bare Skeleton shows at most a small circle (#852):
  the face's in the front of the gimbal frame's beam (its bar to the lids' uprights, deepened its whole width; Stage
  1's stand stands behind it), the mouth cover's in the jaw's chin, thickened inside its U, the shirt's in the Torso's
  front and back walls, thickened 1 mm inside (the shirt on bosses out to its sleeve); the face carries the hair's
  front Seats. The cores, the lids and the gimbal frame plate's back (the hair's back Seats, #838) take theirs in
  their own faces.
- One polarity rule: the carrier's disc shows N to its Shell, reversed on the R Seat of each L/R pair (caps, lid
  covers), so a Shell on the other side's Seat is pushed off. Glue the discs in that way round.
- The hold check (model/test_report.py): each Shell's Seats pull it on with Magpylib's force at the Seats' gap
  (about 4.6 N a pair) at least twice its weight times the peak acceleration the sim reads at its centroid along
  every motion.
- The sim weighs every Shell (#830), but collides the Skeleton and the eyeball caps alone: the other Shells are drawn
  whole, so the servos carry the Skin, and the balance spring holds Morty's head and the bare head alike. Their
  clearance is checked on their own shapes, 0.5 mm from every part but what carries them, at rest and with each servo
  at either end (model/printed/test_skin.py).

## Hardware
Inventory and the buy list: [Parts](build/parts.md#parts-to-buy). The one new purchase is the magnets, and the
filaments not owned yet.
