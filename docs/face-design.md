# Morty face: design spec (grilled 2026-10-31)

Three screw-on 3D-printed modules, one per hardware stage, each leaving a complete-looking
Mech. Parametric OpenSCAD source in `face/`, STL exports, Blender preview renders, slicer
3MFs with AMS colour assignments. Nothing glued to the hardware.

## Character and look
- Morty. Clean 2.5D cartoon read: smooth shell, small bump nose, black line details printed with the AMS.
- On-model scale around the 41 mm eyeballs (59 mm centre to centre, lid span 107 mm): head about
  125 wide, 165 tall, 130 deep. Eye sockets 46 mm so the lids swing freely. Prints on the P1S in halves.
- Colours, all owned, all PLA (hex from the slicer, density 1.24 g/cm3, docs/research/2026-10-31-filament.md):
  Milky Pink #F7CED7, Pure White #FFFFFF, Absolute Black #000000, Apricot #FFB673. Face: Apricot skin, Absolute
  Black hair, lines and collar, Pure White / Absolute Black eyes; the four eyelid parts are reprinted in Apricot.
- Printed parts as they are (docs/build-photos/printed-parts.jpg; data in model/geometry.py): eyes mech brackets,
  lids, bars, crank, wire keeper = Milky Pink; eyeballs = Pure White; pupils, base plate, tilt cradle, bearing ring
  and the small black bits = Absolute Black; upright and tilt lever = Apricot; jaws, pan-tilt bars and servo
  mounts = Pure White. Material tracked per part (PETG Black possible for reprints).

## Stages
1. **Face mask** on the eyes mech: forehead, cheeks, nose, eye sockets. Bolts to the eye bracket's
   corner holes and side wings with M2x12 + M2 nuts (bracket holes are 2.2 mm). Chin stays open.
2. **Skull back + hair cap + collar** with the pan-tilt: skull and hair bolt to the same wings and tilt
   with the head, open at the bottom for the bracket stem; a black collar skirt sits on the 120 x 160
   pan-tilt base and hides boards and batteries.
3. **Jaw skin** on the mouth mechanism: screws to the bottom jaw, closes the chin.

## Freedom to change the base
The pan-tilt base and how the stages attach to it may be redesigned (our own base plate,
standoffs, battery pocket) when that serves the face, collar or wiring. The eyes mech brackets
and the jaw stay as designed.

## Measured hardware (history: read off the designer's STLs before our parts replaced them)
- Eye bracket 115 x 54 x 22; stem drops into the tilt arm slot. Side wings at x = -28 and +87 are flat faces.
- Pan-tilt stack 35.9 mm above the base plate; eye centre about 66-72 mm above the plate.
- Jaw 82 mm wide, 48 deep, front face 14 mm ahead of the pupils, bottom 61 mm below eye centre.

## Hardware
Inventory and the buy list: [Parts](build/parts.md#parts-to-buy).

## Assembly decisions
- Printed halves join with M2 screws into printed bosses and nuts (removable). Nothing glued.
- The collar screws to the base with two M3x10 and comes off for a pack swap. No magnets.
- Inside stays as hollow as possible: skin plus mounting bosses only.

## Toolchain
OpenSCAD 2026.10 (brew cask `openscad@snapshot`; the plain cask is disabled) for source and STL export; Blender 5.2 for preview renders; the printer's slicer for 3MFs.
