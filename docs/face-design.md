# Skeleton and character shells (grilled 2026-11-02, #51)

> [!NOTE]
> **Planned.** Not built yet, and on hold with the next Mech (#51, which holds the whole spec).

The next Mech is one shared skeleton that wears a character: a set of cosmetic shells held on by magnets, swapped by
pulling one set off and pressing the other on. Both are CadQuery parts in the model (model/printed), adapted from our
own design; nothing comes from other people's designs.

## Skeleton and cosmetic parts
- Skeleton, black PETG: the eye gimbal with the eyeball cores and lid arms, the jaw arm and pivot, the neck, the base,
  the electronics mount. It is the same under every character; the eye centres stay fixed (model/geometry.py `EYE_R`).
- Cosmetic, PLA Pure (Milky Pink, Apricot, Pure White, Absolute Black): the head shell with hair, the ears, the nose,
  the eyeball caps, separate pupils, the lid covers, the mouth covers, the collar or shirt. A character's eyeball caps
  may grow up to touching.

## Magnets
- Every cosmetic part sits on magnets, moving ones included: one small disc size everywhere (start 4x2 mm N52), more of
  them on heavier parts.
- The model checks that each part holds against its weight and its peak gesture acceleration.

## Characters
| | Skin, lids | Hair | Collar or shirt | Eyes | Pupils |
|---|---|---|---|---|---|
| Morty | Milky Pink | Absolute Black | Pure White collar | Pure White | Absolute Black, jagged (a separate magnetic part) |
| Bart | Apricot | part of the head | Absolute Black and Milky Pink pattern (one AMS print) | Pure White | Absolute Black dots |

The filaments are owned; their hex and density are in docs/research/2026-10-31-filament.md.

## Hardware
Inventory and the buy list: [Parts](build/parts.md#parts-to-buy). The one new purchase is the magnets.
