# Themes: the Skeleton and its Skins (grilled 2026-11-02 and 2026-11-03, #51, #805, #819)

> [!NOTE]
> **Being designed, not built yet.** The Skins' Shells come after the Skeleton (#665); #51 holds the whole spec.

The Mech is one shared Skeleton that wears a Skin: a set of cosmetic Shells held on by magnets, swapped by pulling one
set off and pressing the other on. Both are CadQuery parts in the model (model/printed), adapted from our own design;
nothing comes from other people's designs. A Theme is a Shape and a Palette for the Skeleton and for the Skin, any
Palette painting any Shape of its category (docs/adr/0022). A Preset names one: Cansin's build (mechanical in black,
the cansin Skin; Morty's Shape stands in for its Shells until they exist, #813), Morty and Bart (each realistic in
anatomical, its own Skin). The model, the [viewer](https://yellowpine.com/noggin/viewer/) and every picture draw the
next Mech in one, Cansin's build unless another is picked; the viewer mixes any Shape with any Palette.

## Skeleton and Skin
- Skeleton, PETG: the eye gimbal with the eyeball cores and lid arms, the jaw arm and pivot, the neck, the Torso, the
  board rack. It is the same under every Skin; the eye centres stay fixed (model/geometry.py `EYE_R`). Its Shapes:
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

## Magnets
- Every cosmetic part sits on magnets, moving ones included: one small disc size everywhere (start 4x2 mm N52), more of
  them on heavier parts.
- The model checks that each part holds against its weight and its peak gesture acceleration.

## Hardware
Inventory and the buy list: [Parts](build/parts.md#parts-to-buy). The one new purchase is the magnets, and the
filaments not owned yet.
