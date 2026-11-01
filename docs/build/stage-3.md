# Stage 3: mouth

!!! warning "Not yet built here"
    No Stage 3 stands on the desk yet. This guide is read off the model (model/stages.py, model/geometry.py), which
    follows the designer's mouth guide ([Credits](../credits.md)); where the model had to infer, it says so
    ([Model notes](../model-notes.md)).

Stage 2 with a jaw under the eyes: the full Mech, the one in the hero loop. One more servo, on Core 2.

## Parts it adds, from the model

<!--{{ stage_parts[3] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The parts list is in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-3/#parts-it-adds-from-the-model),
built from the model.
<!-- #}-->

The model has the plain jaws, the guide's first variant; the jaws with teeth are the same build.

## Servos it adds

<!--{{ stage_servos[3] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The servo, its port and range are in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-3/#servos-it-adds),
built from the model.
<!-- #}-->

The range is the model's, in servo degrees, where every part sweeps clear; the real servo gets calibrated as Stage 1's
were ([Calibration](calibration.md)).

## Assembly, as the model places it

1. **Top jaw**, screwed under the eye bracket: it carries the jaw hinge pins.
2. **Bottom jaw** on those pins; it turns to open the mouth.
3. **Jaw servo mount** on the eye bracket's rail (the neck's eye bracket from [Stage 2](stage-2.md); Stage 1's desk
   bracket has no rail), the mouth servo in it.
4. **Jaw bar** from the jaw horn to the bottom jaw's lug, seated flush between the lug and the horn arm (inferred).
5. **Horn** with the servo at 90 and the jaws closed: opening the mouth turns the horn the other way (the range above).

The jaw rides on the eyes, so it pans and tilts with the head.

## Wiring

The mouth servo goes to Core 2, on the port in the table above ([Wiring](wiring.md)).

## Pictures

<figure markdown="span">
![Stage 3 exploded: the base, the neck lifted off it, the eyes above and the mouth forward of them](https://yellowpine.com/noggin/images/exploded.jpg){ width="800" height="600" }
<figcaption>Stage 3 exploded: the base, the neck, the eyes and the mouth</figcaption>
</figure>

Turn it around in [the web viewer](https://yellowpine.com/noggin/viewer/), Stage 3.
