# Stage 3: mouth

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

[Open Stage 3 in the viewer](https://yellowpine.com/noggin/viewer/?stage=3)

Stage 2 with a jaw under the eyes: the whole Mech. One more servo, on the neck Core. *Upcoming (#850): Morty's Shells,
cut from his sculpt, get their Seats and go on after it ([Themes](../face-design.md)).* In the realistic Skeleton the skull, its mandible and the seven cervical vertebrae are adapted from
others' meshes ([Credits](../credits.md)), life-size and warped into Morty. The skull's calvaria is a cap: it lifts
straight up off three Seats on the skull's rim, a magnet pair and three balls in V-grooves at each, to reach the
Cores and the hub in the cranium.

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

1. **Jaw bar** on the jaw's pin, a post reaching in from the left ramus of the jaw's carrier. Its screw goes in from
   inside the jaw, where the mouth servo will stand, so it is fitted first.

2. **Jaw** on the gimbal frame's lugs, turning at the mandible's condyles; it turns down to open the mouth. Its
   carrier is a chain of Bones laid on the mandible's inner face, half let in, down each ramus and along the body,
   with a bar across behind the chin, sized to hold the mouth servo's stall. The mandible comes off it in one piece,
   down and 30° forward. *Upcoming (#968): the two magnet pairs that hold the mandible on, and the chin Shell's Seat
   in its front (#850).*

   [Open Stage 3 in the viewer](https://yellowpine.com/noggin/viewer/?stage=3&part=jaw)

3. **Mouth servo** in the gimbal frame's collar, forward under its plate, between the mandible's two sides; the jaw
   bar's other end joins its Horn, from the left.

The jaw rides the head mount, so it pans and tilts with the head. Each sub-assembly apart:

[Open Stage 3 in the viewer](https://yellowpine.com/noggin/viewer/?stage=3&explode=1)

## Wiring

The jaw servo goes to the neck Core, on its port in [Wiring](wiring.md). *Upcoming (#929): the neck Core drives the
jaw, so a gesture opens the mouth; today the jaw plays in the model and the viewer alone.*
