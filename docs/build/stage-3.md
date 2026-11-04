# Stage 3: mouth

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

[Open Stage 3 in the viewer](https://yellowpine.com/noggin/viewer/?stage=3)

Stage 2 with a jaw under the eyes: the whole Mech. One more servo, on the neck Core. The Skin's Shells go on after
it ([Themes](../face-design.md)). In the realistic Skeleton the skull and its first two vertebrae are adapted from
others' meshes ([Credits](../credits.md)); *Upcoming (#874): a life-size BodyParts3D teaching skull (calvaria cap,
face and skull base, mandible, held on magnets) and all seven cervical vertebrae, warped into Morty*.

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

1. **Jaw** on the gimbal frame's lugs, its hinge where the realistic skull's condyles are; it turns down to open the
   mouth. Its arms are scaled for the life-size head.

   [Open Stage 3 in the viewer](https://yellowpine.com/noggin/viewer/?stage=3&part=jaw)

2. **Jaw servo** in the gimbal frame's collar, hanging under its plate behind the jaw; the **jaw bar** joins its horn
   to the jaw's lever.

The jaw rides the head mount, so it pans and tilts with the head. Each sub-assembly apart:

[Open Stage 3 in the viewer](https://yellowpine.com/noggin/viewer/?stage=3&explode=1)

## Wiring

The jaw servo goes to the neck Core, on its port in [Wiring](wiring.md). *Upcoming (#929): the neck Core drives the
jaw, so a gesture opens the mouth; today the jaw plays in the model and the viewer alone.*
