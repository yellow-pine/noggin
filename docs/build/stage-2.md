# Stage 2: neck

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

[Open Stage 2 in the viewer](https://yellowpine.com/noggin/viewer/?stage=2)

The eye block leaves its test stand for the neck: the head turns left and right (pan) and nods (tilt) on its own
pivots: the cervical carrier holds a nod plate for tilt, and the head pans on a thrust bearing on that plate. Both
servos sit inside the skull; the tilt uses a standard metal-gear servo and a reaction parallelogram, the pan a micro
servo and keyed torque coupling (#978). The Torso under it holds the pack, its switch and the power-path board;
both Cores ride in the head's cranium, the hub's USB-C port at the back of the skull base. Two more servos, on the neck
Core.

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

1. **Torso**: ~~the box pedestal the Mech stands on~~ *a T1–T4 ribcage of primitives on a floor plate, the Mech
   standing on the plate (#879)*, the pack lying low in it, the switch board lying flat beside the
   pack's lead end, its lever reached through a hole in the lid, the power-path board lying flat in front, and the
   **cervical carrier** bolted to its floor, its two medial rails through the **torso lid** beside the wire corridor.
   The lid drops onto its ledge inside the walls, flush with their top.
2. **Nod plate** turning on the carrier's C0 trunnions. The standard tilt servo's case is fixed to its upper saddle;
   the supplied horn and printed adapter react through a closed parallelogram to the carrier. Its output reverses
   the servo's rotation. A torsion balance spring at the tilt pivot supports the head's weight.
3. **Head mount** on the F8-16M thrust bearing in the nod plate. The pan micro servo turns a keyed quill through the
   bearing's bore; the bearing carries axial head load. Pan follows tilt in the joint order. From the side:

   [Open Stage 2 in the viewer](https://yellowpine.com/noggin/viewer/?stage=2&view=side)

4. **Eye block** from [Stage 1](stage-1.md) on the head mount, in the test stand's place.
5. **Cranium tray** on the gimbal frame's plate, up behind the bail: both Cores lying flat on their Shields on it, and
   the hub on its riser, its upstream USB-C port out the back of the skull base.

Each busy pivot is a greased M3 shank turning in a bore printed along the layers' axis.

## Wiring

The neck Core joins the Wi-Fi like the eyes Core ([Wiring](wiring.md)) and runs the same eye program, which turns the
pan for wide gaze shifts once it is calibrated ([Gestures](../use/gestures.md#the-head-joins-wide-gaze-shifts)).
*Upcoming (#929): the neck Core drives the tilt too, so a gesture nods the head.* The power-path board in the Torso charges the
pack from the head's USB-C and feeds both Shields in the head through the switch board and the neck cable's four
conductors up the post, a 470 µF capacitor across the Y lead where it enters the Shields.

Use a USB-C source advertising 3 A until the input-limit detector is built and checked.
*Upcoming (#971): a TUSB320 detector that sets the limit from the source's advertisement at attach, without following
later changes. No ready-made breakout was found; this design is inferred (docs/research/2026-11-03-usb-c-power.md 7).*

Every servo lead runs to the Shields in the head, and the leads that cross the pan and tilt pivots (the pan servo's,
the tilt servo's and the neck cable) are clamped at both ends and bent no tighter than ten times their diameter.
