# Morty face: design spec (grilled 2026-10-31)

Three screw-on 3D-printed modules, one per hardware stage, each leaving a complete-looking
Mech. Parametric OpenSCAD source in `face/`, STL exports, Blender preview renders, Bambu Studio
3MFs with AMS colour assignments. Nothing glued to the hardware.

## Character and look
- Morty. Clean 2.5D cartoon read: smooth shell, small bump nose, black line details printed with the AMS.
- On-model scale around the 41 mm eyeballs (59 mm centre to centre, lid span 107 mm): head about
  125 wide, 165 tall, 130 deep. Eye sockets 46 mm so the lids swing freely. Prints on the P1S in halves.
- Colours, all owned, all Bambu PLA Pure (hex from Bambu Studio, density 1.24 g/cm3, docs/research/2026-10-31-filament.md):
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

## Hardware (inventory and buy list 2026-10-31, grilled)
Owned: Beginner Hardware Kit ZK004 (2 Cores, receiver + transmitter shields, switch module, 2S pack, charger,
one 180 and one 360 servo), Battery Upgrade Kit ZL003 (second switch module + second pack), 4 PG001 servos,
M3x10, M2x12, M2 nuts (20 each). Used by the eyes: 4 servos, 1 Core, 1 receiver shield, 1 switch, 1 pack.
Unused on the desk: 1 Core (the remote's, becomes Core 2), 1 switch module, 1 pack (spare on charge), one
180 servo (the 360 one is continuous rotation, not positional). Pan bearing: the printed bearing block (Bambu
no longer lists the F10-18M thrust bearing).

Ordered 2026-10-31 (Bambu EU store): Receiver Shield XA004 x1; servo PG001 x3 (2 needed + 1 spare); battery
PC003 x1 (one pack per shield + a spare on charge); M2x12 screws x1 pack and M2 nuts x1 pack (shell halves
and mask); one pack of longer M2 (x16 or x20, whichever is listed) for the mask + skull stack on the wings;
M2.5x6 screws x1 pack if listed (the remaining stages need 26 of the kit's M2.5). No filament: the shell is
a thin hollow skin, about 180 g Apricot in total and about 80 g Black.

## Assembly decisions
- Printed halves join with M2 screws into printed bosses and nuts (removable). Nothing glued.
- The collar screws to the base with two M3x10 and comes off for a pack swap. No magnets.
- Inside stays as hollow as possible: skin plus mounting bosses only.

## Toolchain
OpenSCAD 2026.10 (brew cask `openscad@snapshot`; the plain cask is disabled) for source and STL export; Blender 5.2 for preview renders; Bambu Studio for 3MFs.
