# Stage 1: eyes

> [!WARNING]
> **Being designed, not built yet.** This guide is read off the model (model/stages.py, model/geometry.py STAGES,
> [Model notes](../model-notes.md)); every size in it is inferred until the Mech is printed (#51).

[Open Stage 1 in the viewer](https://yellowpine.com/noggin/viewer/?stage=1)

The eye block on its test stand: both eyes turn together, left and right on one servo and up and down on another, and
each eye's upper and lower lid close on that eye's own servo. Four servos on the eyes Core, which stands against the
stand's back. The model sizes the eyes, caps and lids from Morty's life-size eye reference, with the gimbal frame
sized for his pupil spacing.

## Parts it adds, from the model

<!--{{ stage_parts[1] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The parts list is in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-1/#parts-it-adds-from-the-model),
built from the model.
<!-- #}-->

## Servos it adds

<!--{{ stage_servos[1] }}-->

<!--{# GitHub shows the line below; the site drops it for the table above, which it builds from the code -->
The servos and their ranges are in [the table on the site](https://yellowpine.com/noggin/docs/build/stage-1/#servos-it-adds),
built from the model.
<!-- #}-->

The ranges are the model's, in servo degrees, where every part sweeps clear; the eye program starts from its own
calibration inside them ([Wiring](wiring.md#servo-ports)), and you calibrate your servos from there
([Calibration](calibration.md)).

## Assembly, as the model places it

1. **Gimbal frame**: the eye block's plate, carrying both eyes' pivots and the four servos behind and between the eyes:
   each lid servo upright behind its eye, the yaw servo hanging under the plate.
2. **Yaw yokes**, one per eye, turning left and right in the frame; the **tie-bar** joins them to the yaw servo's horn.
3. **Eyeball cores** turning up and down in the yokes; the **bail** and its two **push-rods** turn both from the pitch
   servo through the **pitch bar**.
4. **Lids**: each eye's upper lid through its **lid bar** from its lid servo, the lower lid through a **lid link** off
   that bar, so the two close against each other. The left upper lid:

   [Open Stage 1 in the viewer](https://yellowpine.com/noggin/viewer/?stage=1&part=L+upper+lid)

5. **Eyeball caps** on the cores, as the eyes look out from the front:

   [Open Stage 1 in the viewer](https://yellowpine.com/noggin/viewer/?stage=1&view=front)

6. **Test stand** screwed under the frame's plate, where the head mount goes in [Stage 2](stage-2.md); the eyes Core
   on its Shield against the stand's back. *Upcoming (#877): Stage 1 becomes a cut of Stage 3, the eye block arriving
   in the cranium that carries it, and the test stand goes.*

## Wiring

The four servos go to the eyes Core ([Wiring](wiring.md)); flash it ([Flashing](flashing.md)). The model's Stage 1
carries no pack: the pack and the switch board sit beside the stand until the Torso holds them in Stage 2
(inferred). Then calibrate the four servos on your Stage 1 ([Calibration](calibration.md)) and run the noggin service
([The noggin service](../use/noggin-service.md)): the eyes react to Claude Code.
