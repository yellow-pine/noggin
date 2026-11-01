# Stage 2: neck

!!! warning "Not yet built here"
    No Stage 2 stands on the desk yet. This guide is read off the model (model/stages.py, model/geometry.py), which
    follows the designer's pan-and-tilt guide ([Credits](../credits.md)); where the model had to infer, it says so
    (docs/research/2026-10-31-neck.md, [Model notes](../model-notes.md)).

The eyes move from the desk onto a pan-and-tilt neck: the head turns left and right (pan) and nods (tilt). Two more
servos on a second Core.

## Parts it adds, from the model

<!--{{ stage_parts[2] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The parts list is in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-2/#parts-it-adds-from-the-model),
built from the model.
<!-- #}-->

The eye bracket swaps: Stage 1's desk eye bracket has no jaw rail and a stem 5 mm shorter; the neck's eye bracket has
the rail the mouth hangs on in [Stage 3](stage-3.md).

## Servos it adds

<!--{{ stage_servos[2] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The servos, their ports and ranges are in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-2/#servos-it-adds),
built from the model.
<!-- #}-->

The ranges are the model's, in servo degrees, where every part sweeps clear; the real servos get calibrated as Stage 1's
were ([Calibration](calibration.md)).

## Assembly, as the model places it

1. **Base plate.** It carries the pan pivot, the pan servo's two mounts, both Shields' standoffs, the battery box and
   the switch board holder.
2. **Bearing block** in the base plate's recess, and the **pan turntable** on it: the turntable turns on the pan axis
   and carries the tilt servo tower and the upright.
3. **Pan servo** in its two mounts: the lead mount (arched to let the lead out) at the shaft end, the tail mount at the
   other. The pan bar (15 mm between holes, the shorter one) joins the pan horn to the upright's lever.
4. **Upright** on the turntable, carrying the tilt pivot. The **tilt arm** turns on it; the tilt bar (20 mm) joins the
   tilt horn to the arm's lever.
5. **Horns** with the servos at 90: the tilt horn horizontal with its bar vertical, the pan horn about square to its bar. Each bar
   screws to the horn's second hole from the end, drilled to 2 mm, with an M2 screw and nut.
6. **Eyes** on the tilt arm: the eye bracket's stem fills the arm's window and its rail lies on the arm top, the eye
   centres above the arm. The eyes face the plate's pointed end, away from the pack, the Cores and the
   switch board.
7. **Wire holder** on the base plate's two posts, holding the leads down.

The head turns less than its servos: the stock linkages give about 0.47 of the pan servo's angle and 0.32 of tilt's.
In the model pan swings 46° end to end and tilt about ±17° (docs/research/2026-10-31-neck.md).

## Wiring

Core 2 sits on its own Shield and joins the Wi-Fi like Core 1 ([Wiring](wiring.md)). The model still carries the stock
power: one pack and one switch board for both Shields. The plan is a pack and a switch board per Shield (one pack cannot
feed both at stall), a planned edit not yet in the model ([Model notes](../model-notes.md)).

## Pictures

<figure markdown="span">
![The three Stages: stage 2 is the second, the eyes on the neck](https://yellowpine.com/noggin/images/stages.jpg){ width="3200" height="600" }
<figcaption>Stage 1 front, Stage 2 side, Stage 3 side and front</figcaption>
</figure>

Turn it around in [the web viewer](https://yellowpine.com/noggin/viewer/), Stage 2.
