# Pictures

Every picture is the model's: our parametric parts, posed by MuJoCo's trajectories and drawn by Blender, built in CI
and served by the site, never kept in git (ADR 0009). How they are made, their sizes and colours:
[Model notes](model-notes.md).

## The Stages

<!--{{ panels }}-->

<!--{# GitHub shows the line below; the site drops it for the grid above, which it builds from the code -->
Each Stage from the side and isometric is in [the grid on the site](https://yellowpine.com/noggin/docs/pictures/).
<!-- #}-->

See Stage 3 [exploded in the web viewer](https://yellowpine.com/noggin/viewer/?stage=3&explode=1): the base, the
neck lifted off it, the eyes above and the mouth forward of them.

The Mech grows in three Stages: the eyes on the base, then on the pan-and-tilt neck, then with the mouth. `model/` is
the Mech as code: our own parametric CadQuery parts, a simulation (MuJoCo, ADR 0007) that sweeps every linkage,
finds its collisions and the supply's voltage sag (SPICE) before a part is printed, and Blender pictures from
MuJoCo's trajectories (every picture here). Main's sim reports are on the site at [/reports](https://yellowpine.com/noggin/reports/).

## The next Mech

<!--{{ next_panels }}-->

<!--{# GitHub shows the line below; the site drops it for the grid above, which it builds from the code -->
The next Mech from the side and isometric is in [the grid on the site](https://yellowpine.com/noggin/docs/pictures/).
<!-- #}-->

The Mech being designed to follow today's (#51), in the model as its own document beside the Stages, framed on its
own. It starts as Stage 3 until its parts replace today's, the eye gimbal first.

## The hero

<figure>
<img src="https://yellowpine.com/noggin/images/hero.webp" alt="noggin: Stage 3 talking, turning and nodding" width="800" height="400">
<figcaption>Stage 3 talking, turning and nodding</figcaption>
</figure>

## The gestures

The gestures play in [the viewer](https://yellowpine.com/noggin/viewer/), on the landing page too: its buttons pick
one, and the address links to it.
