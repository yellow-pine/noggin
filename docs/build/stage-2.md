# Stage 2: neck

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

The eye block leaves its test stand for the neck: the head turns left and right (pan) and nods (tilt) on its own
pivots, each servo driving it through a bar. The Torso under it holds the pack and the pan servo; the boards ride in the
back of the head. Two more servos, on the neck Core.

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

1. **Torso**: the foot the Mech stands on, the pack lying low in it, the switch board lying flat in front of the
   pack's lead end, its lever reached from the open back, and the **neck mount** with the pan servo on top.
2. **Pan yoke** turning on the neck mount; the **pan bar** joins it to the pan servo's horn.
3. **Head mount** turning on the yoke's cheeks, the tilt pivot under the head's centre of mass; the **tilt bar** joins
   it to the tilt servo's horn.
4. **Eye block** from [Stage 1](stage-1.md) on the head mount, in the test stand's place.
5. **Board rack** on the gimbal frame's plate behind the eyes: a cradle in each cheek, each Core on its Shield slid
   in on edge from behind, its USB-C port facing back.

Each busy pivot is a greased M3 shank turning in a bore printed along the layers' axis.

## Wiring

The neck Core joins the Wi-Fi like the eyes Core ([Wiring](wiring.md)). One pack and one switch board in the Torso
feed both Shields: one power lead runs up the neck from the switch board and splits into the Y lead in the head; the leads that cross the pan and tilt pivots are clamped at both
ends and bent no tighter than ten times their diameter.
