# Parts

The Mech grows in three Stages, each a complete Mech on the desk: the eyes on the base plate
([Stage 1](stage-1.md)), then on the pan-and-tilt neck ([Stage 2](stage-2.md)), then with the mouth
([Stage 3](stage-3.md)). Each Stage's page lists, from the model, the parts it adds. This page is the shopping list.

The mechanism and its assembly instructions are the designer's ([Credits](../credits.md)); those files are not
redistributed here. Our own parametric parts print from `make stl` (model/build/stl, mm, in the designer's frames).

## Parts to buy

The one place the shop's names and codes appear (2026-10-31, grilled). Electronics are Bambu Lab's CyberBrick
range, filament is Bambu PLA Pure.

- Owned: Beginner Hardware Kit ZK004 (2 Cores, an X11 receiver shield + a transmitter shield, switch module, 2S pack,
  charger, one 180 and one 360 servo), Battery Upgrade Kit ZL003 (second switch module + second pack), 4 PG001
  servos, M3x10, M2x12, M2 nuts (20 each). Used by the eyes: 4 servos, 1 Core, 1 Shield, 1 switch board, 1 pack.
  Unused on the desk: 1 Core (the remote's, becomes Core 2), 1 switch board, 1 pack (spare on charge), one 180
  servo (the 360 one is continuous rotation, not positional). Pan bearing: the printed bearing block (the shop no
  longer lists the F10-18M thrust bearing).
- Ordered 2026-10-31 (Bambu EU store): X11 Receiver Shield XA004 x1; servo PG001 x3 (2 needed + 1 spare); battery
  PC003 x1 (one pack per Shield + a spare on charge); M2x12 screws x1 pack and M2 nuts x1 pack (shell halves and
  mask); one pack of longer M2 (x16 or x20, whichever is listed) for the mask + skull stack on the wings; M2.5x6
  screws x1 pack if listed (the remaining stages need 26 of the kit's M2.5).
- Filament, all owned, Bambu PLA Pure: Milky Pink, Pure White, Absolute Black, Apricot (hex and density:
  docs/research/2026-10-31-filament.md). No more needed: the face shell is a thin hollow skin, about 180 g Apricot
  in total and about 80 g Black.

## On the Mac

macOS, [uv](https://docs.astral.sh/uv/) (Python 3.12 and mpremote come with it) and Claude Code. `uv` manages
`.venv` and runs mpremote and pytest; the system Python is 3.9 and is not used.
