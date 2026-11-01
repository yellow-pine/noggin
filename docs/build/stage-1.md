# Stage 1: eyes

The eyes on the base plate: the Stage built here. [Stage 2](stage-2.md) and [Stage 3](stage-3.md) are read off the
model.

## What we built

<figure markdown="span">
![The three Stages: stage 1 front (base and eyes), stage 2 side (eyes on the neck), stage 3 side and front (with the mouth)](https://yellowpine.com/noggin/images/stages.jpg){ width="3200" height="600" }
<figcaption>Stage 1 front, Stage 2 side, Stage 3 side and front</figcaption>
</figure>

Photo: `docs/references/build-photos/eye-mech-build-photo.jpg` (local only). Two eyeballs with eyelids on a base plate, four 180° 9 g servos, a Core on a Shield, a switch board and a 14500 cell
holder. Our board is mounted rotated 90° relative to the designer's photos, which changes nothing electrically. The
eyes stand on the desk eye bracket, its stem in the base plate's slot. Turn it around in
[the web viewer](https://yellowpine.com/noggin/viewer/), Stage 1.

## Parts, from the model

<!--{{ stage_parts[1] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The parts list is in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-1/#parts-from-the-model),
built from the model.
<!-- #}-->

## Assembly

The designer's eyes guide ([Credits](../credits.md)) is the assembly. Then:

1. Wire the four servos to the Shield's ports ([Wiring](wiring.md)).
2. Flash our program onto the Core ([Flashing](flashing.md)).
3. Fit the horns with every servo at 90 and tune the lids ([Calibration](calibration.md)).
