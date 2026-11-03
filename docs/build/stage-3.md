# Stage 3: mouth

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

Stage 2 with a jaw under the eyes: the whole Mech. One more servo, on the neck Core. The Skin's Shells go on after
it ([Themes](../face-design.md)).

## Parts it adds, from the model

<!--{{ stage_parts[3] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The parts list is in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-3/#parts-it-adds-from-the-model),
built from the model.
<!-- #}-->

## Servos it adds

<!--{{ stage_servos[3] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The servo and its range are in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-3/#servos-it-adds),
built from the model.
<!-- #}-->

The range is the model's, in servo degrees from the jaw shut, where every part sweeps clear; the real servo gets
calibrated ([Calibration](calibration.md)).

## Assembly, as the model places it

1. **Jaw** on the head mount's lugs; it turns down to open the mouth.
2. **Jaw servo** in the head mount's collar, lying on the gimbal frame's plate beside the mouth; the **jaw bar** joins
   its horn to the jaw.

The jaw rides the head mount, so it pans and tilts with the head.

## Wiring

The jaw servo goes to the neck Core, on its port in [Wiring](wiring.md).
