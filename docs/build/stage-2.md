# Stage 2: neck

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

The eye block leaves its test stand for the neck: the head turns left and right (pan) and nods (tilt) on its own
pivots, each servo driving it through a bar. The Torso under it holds both packs and the switch board; both Cores ride
in the head's cranium. Two more servos, on the neck Core.

## Parts it adds, from the model

<!--{{ stage_parts[2] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The parts list is in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-2/#parts-it-adds-from-the-model),
built from the model.
<!-- #}-->

## Servos it adds

<!--{{ stage_servos[2] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The servos and their ranges are in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-2/#servos-it-adds),
built from the model.
<!-- #}-->

The ranges are the model's, in servo degrees, where every part sweeps clear; the real servos get calibrated
([Calibration](calibration.md)).

## Assembly, as the model places it

1. **Torso**: the box pedestal the Mech stands on, the pack lying low in it, the switch board lying flat beside the
   pack's lead end, its lever reached through a hole in the lid, the spare pack in front on the kit's charger dongle,
   an opening in the -x wall where the two packs' plugs swap and the dongle's USB lead leaves, and the **neck mount**
   standing on its floor, its hollow post rising through the **torso lid**, the pack's Y lead up inside it, the pan
   servo on its shelf over the lid. The lid slides onto the post from behind through its slot, over the walls, then
   drops onto its ledge inside them, flush with their top, where it cannot slide off.
2. **Pan yoke** turning on the post's top under the head, the tilt servo on its floor; the **pan bar** joins it to the
   pan servo's horn.
3. **Head mount** turning on the yoke's cheeks, the tilt pivot under the skull's base behind the head's centre of mass,
   a torsion spring on its shank holding the head's weight (the balance spring); the **tilt bar** joins it to the tilt
   servo's horn.
4. **Eye block** from [Stage 1](stage-1.md) on the head mount, in the test stand's place.
5. **Cranium tray** on the gimbal frame's plate, up behind the bail: both Cores lying flat on their Shields on it,
   each USB-C socket's opening straight back through the skull.

Each busy pivot is a greased M3 shank turning in a bore printed along the layers' axis.

## Wiring

The neck Core joins the Wi-Fi like the eyes Core ([Wiring](wiring.md)). One pack and the switch board in the Torso
feed both Shields in the head, the Y lead's one pair up the post, split in the cranium; every servo lead runs to the
Shields in the head, and the leads that cross the pan and tilt pivots (the pan servo's, the tilt servo's and the Y
lead's pair) are clamped at both ends and bent no tighter than ten times their diameter.
