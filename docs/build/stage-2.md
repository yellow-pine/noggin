# Stage 2: neck

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

[Open Stage 2 in the viewer](https://yellowpine.com/noggin/viewer/?stage=2)

The eye block leaves its test stand for the neck: the head turns left and right (pan) and nods (tilt) on its own
pivots: one aluminium tube up the neck carries the cervical carrier, which holds a nod plate for tilt, and the head
pans on a thrust bearing on that plate. Both
servos sit inside the skull; the tilt uses a standard metal-gear servo and a reduction four-bar, the pan a micro
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
   **neck socket** bolted to its floor: four countersunk screws up through the floor, a nut on each over the socket's
   flange. The **neck tube** stands in the socket, a pivot screw across both, and rises through the **torso lid**'s
   slot; the neck cable runs up its bore from the socket's open side. The lid drops onto its ledge inside the walls,
   flush with their top. The **cervical carrier** slides onto the tube's top, down to its hole, and takes the second
   screw across.
2. **Nod plate** turning on the carrier's C0 trunnions. The standard tilt servo's case stands upright in its low rear
   cradle, behind the wire corridor; the supplied horn and printed adapter react through a reduction four-bar to the
   carrier: a short crank on the horn and a longer arm on the carrier, so the head turns about half the servo's turn,
   reversed, and the servo holds the head's weight with no spring. The standard pan servo hangs shaft down from the cradle's rear
   mast, behind the pan bearing; both cases ride inside the compact head (#978).
3. **Head mount** on the C0 pan bearing on the nod plate's hollow spindle. The pan servo turns it
   through a parallelogram four-bar; the bearing carries the head's load, and the power leads pass its 8 mm bore. Pan
   follows tilt in the joint order. From the side:

   [Open Stage 2 in the viewer](https://yellowpine.com/noggin/viewer/?stage=2&view=side)

4. **Eye block** from [Stage 1](stage-1.md) on the head mount, in the test stand's place.
5. **Cranium tray** on the gimbal frame's plate, up behind the bail: both Cores lying flat on their Shields on it, and
   the hub on its riser, its upstream USB-C port out the back of the skull base.

Each busy pivot is a greased M3 shank turning in a bore printed along the layers' axis.

## The neck tube

The neck stands on one aluminium tube, bought as stock and cut and drilled by you ([Parts](parts.md), docs/adr/0031):

<!--{{ neck_tube }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The tube's length and its holes are in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-2/#the-neck-tube),
built from the model.
<!-- #}-->

1. Cut it square and take the burr off both ends, inside and out: the neck cable runs through it.
2. Mark one straight line down its length (lay it in the corner of a door frame and run a pen along it) and mark both
   holes on that line. Drill each straight through both walls. The two holes must lie in one plane: the screws run
   across the Mech, side to side, where a hole weakens the tube least.
3. Take the burr off each hole inside the bore too.

The socket's screw goes in from the Mech's left, under the lid; the carrier's from its left too. Neither is greased.

## Wiring

The neck Core joins the Wi-Fi like the eyes Core ([Wiring](wiring.md)) and runs the same eye program, which turns the
pan for wide gaze shifts once it is calibrated ([Gestures](../use/gestures.md#the-head-joins-wide-gaze-shifts)).
*Upcoming (#929): the neck Core drives the tilt too, so a gesture nods the head.* The power-path board in the Torso charges the
pack from the head's USB-C and feeds both Shields in the head through the switch board and the neck cable's four
conductors up the neck tube's bore, a 470 µF capacitor across the Y lead where it enters the Shields.

Use a USB-C source advertising 3 A until the input-limit detector is built and checked.
*Upcoming (#971): a TUSB320 detector that sets the limit from the source's advertisement at attach, without following
later changes. No ready-made breakout was found; this design is inferred (docs/research/2026-11-03-usb-c-power.md 7).*

Every servo lead runs to the Shields in the head, and the leads that cross the pan and tilt pivots (the pan servo's,
the tilt servo's and the neck cable) are clamped at both ends and bent no tighter than ten times their diameter.
