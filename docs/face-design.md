# Morty face: design spec (grilled 2026-10-31)

Three screw-on 3D-printed modules, one per hardware stage, each leaving a complete-looking
Mech. Parametric OpenSCAD source in `face/`, STL exports, Blender preview renders, Bambu Studio
3MFs with AMS colour assignments. Nothing glued to the hardware.

## Character and look
- Morty. Clean 2.5D cartoon read: smooth shell, small bump nose, black line details printed with the AMS.
- On-model scale around the 41 mm eyeballs (59 mm centre to centre, lid span 107 mm): head about
  125 wide, 165 tall, 130 deep. Eye sockets 46 mm so the lids swing freely. Prints on the P1S in halves.
- Colours, all owned: Apricot skin, Absolute Black for hair, eyebrow/mouth lines and the collar,
  Pure White / Absolute Black for eyes. The four eyelid parts are reprinted in Apricot.

## Stages
1. **Face mask** on the eyes mech: forehead, cheeks, nose, eye sockets. Bolts to main bracket v2's
   corner holes and side wings with M2x12 + M2 nuts (bracket holes are 2.2 mm). Chin stays open.
2. **Skull back + hair cap + collar** with the pan-tilt: skull and hair bolt to the same wings and tilt
   with the head, open at the bottom for the bracket stem; a black collar skirt sits on the 120 x 160
   pan-tilt base and hides boards and batteries.
3. **Jaw skin** on the mouth mechanism: screws to the bottom jaw, closes the chin.

## Measured hardware (from the designer's STLs, see docs/references)
- Main bracket v2 115 x 54 x 22; stem drops into the tilt arm slot. Side wings at x = -28 and +87 are flat faces.
- Pan-tilt v2 stack 35.9 mm above the base plate; eye centre about 66-72 mm above the plate.
- Jaw 82 mm wide, 48 deep, front face 14 mm ahead of the pupils, bottom 61 mm below eye centre.

## Hardware still to buy (Bambu EU store only, like the earlier orders)
Owned from the Oct 2026 order: Beginner Hardware Kit ZK004 (2 Cores, receiver + transmitter shields,
one 2S pack + switch, 1 servo), 4 extra PG001 servos (5 total), extra 2S pack ZL003, M3x10, M2x12, M2 nuts.
- 2 x 9g servo PG001 (7 needed in total)
- 1 x Remote Control Receiver Shield XA004 (the kit's second Core goes on it; no new Core)
- 1 x Miniature thrust ball bearings F10-18M EB007 (2 pcs)
- 1 x 100 mm 2-pin XH2.54 wires XC005 (2 pcs)
Second shield is powered by the second 2S pack plugged straight in, no second switch. No filament.

## Toolchain
OpenSCAD (brew cask) for source and STL export; Blender 5.2 for preview renders; Bambu Studio for 3MFs.
