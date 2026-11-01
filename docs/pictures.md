# Pictures

Every picture is the model's: our parametric parts, posed by MuJoCo's trajectories and drawn by Blender, built in CI
and served by the site, never kept in git (ADR 0009). How they are made, their sizes and colours:
[Model notes](model-notes.md).

## The Stages

![The three Stages: stage 1 front (base and eyes), stage 2 side (eyes on the neck), stage 3 side and front (with the mouth)](https://yellowpine.com/noggin/images/stages.jpg)

![Stage 3 exploded: the base, the neck lifted off it, the eyes above and the mouth forward of them](https://yellowpine.com/noggin/images/exploded.jpg)

The Mech grows in three Stages: the eyes on the base, then on the pan-and-tilt neck, then with the mouth. `model/` is
the Mech as code: our own parametric CadQuery parts, a simulation (MuJoCo, ADR 0007) that sweeps every linkage,
finds its collisions and the supply's voltage sag (SPICE) before a part is printed, and Blender pictures from
MuJoCo's trajectories (every picture here). Main's sim reports are on the site at [/reports](https://yellowpine.com/noggin/reports/).

## The hero

![noggin: Stage 3 talking, turning and nodding](https://yellowpine.com/noggin/images/hero.gif)

## The gestures

| eureka | attention | bored |
|---|---|---|
| ![eureka](https://yellowpine.com/noggin/images/eureka.gif) | ![attention](https://yellowpine.com/noggin/images/attention.gif) | ![bored](https://yellowpine.com/noggin/images/bored.gif) |
| **wince** | **wink** | **thinking** |
| ![wince](https://yellowpine.com/noggin/images/wince.gif) | ![wink](https://yellowpine.com/noggin/images/wink.gif) | ![thinking](https://yellowpine.com/noggin/images/thinking.gif) |
