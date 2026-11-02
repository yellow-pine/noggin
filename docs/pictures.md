# Pictures

The next Mech (#51) as its model has it, clean-room: our own parts and our Envelopes of the hardware we own, posed by
MuJoCo and drawn by Blender in CI on every merge to main, never kept in git (ADR 0009, ADR 0019). How the pictures are
made: [Model notes](model-notes.md).

## The next Mech

<!--{{ next_panels }}-->

<!--{{ next_front }}-->

<!--{# GitHub shows the line below; the site drops it for the grids, which it builds from the code -->
The next Mech's Stages from the side and isometric, and each of its parts, are in
[the grids on the site](https://yellowpine.com/noggin/docs/pictures/).
<!-- #}-->

Stage by Stage, each with its Skeleton as Bones and plain: Stage 1 the eye block on its test stand with the eyes Core,
Stage 2 adds the Torso, the neck and the boards, Stage 3 the jaw, the whole Mech. Under them, as the home shows them,
Stage 1 from the front and Stage 3 from the side, exploded. Turn each in
[the viewer](https://yellowpine.com/noggin/viewer/).

## In motion

<!--{{ next_motions }}-->

<!--{# GitHub shows the line below; the site drops it for the grid, which it builds from the code -->
Its eye gimbal sweeping its yaw and pitch with the lids following, then playing each gesture and Rest, are in
[the grid on the site](https://yellowpine.com/noggin/docs/pictures/#in-motion).
<!-- #}-->

The sweep is keyed through the gimbal's own kinematics (model/gimbal.py); the gestures and Rest are the eye program's,
played in MuJoCo through the gimbal's command map, as the next Mech's eyes Core will play them; the neck's pan turns
the gimbal with it on the wide gaze shifts (eureka, thinking). The jaw joins as it moves.

## Its parts

<!--{{ next_parts }}-->
