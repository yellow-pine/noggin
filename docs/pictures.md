# Pictures

The next Mech (#51) as its model has it, clean-room: our own parts and our Envelopes of the hardware we own, posed by
MuJoCo and drawn by Blender in CI on every merge to main, never kept in git (ADR 0009, ADR 0019). Today's Mech is not
shown: its printed parts derive from the designer's models. How the pictures are made: [Model notes](model-notes.md).

## The next Mech

<!--{{ next_panels }}-->

<!--{# GitHub shows the line below; the site drops it for the grids, which it builds from the code -->
The next Mech from the side and isometric, and each of its parts, are in
[the grids on the site](https://yellowpine.com/noggin/docs/pictures/).
<!-- #}-->

For now the eye gimbal and the hardware the next Mech keeps (the Cores, the Shields, the switch board, the pack, the
servos), laid out apart until the neck and the base place them. Turn it in
[the viewer](https://yellowpine.com/noggin/viewer/).

## In motion

<!--{{ next_motions }}-->

<!--{# GitHub shows the line below; the site drops it for the grid, which it builds from the code -->
Its eye gimbal sweeping its yaw and pitch with the lids following, then playing each gesture and Rest, are in
[the grid on the site](https://yellowpine.com/noggin/docs/pictures/#in-motion).
<!-- #}-->

The sweep is keyed through the gimbal's own kinematics (model/gimbal.py); the gestures and Rest are the eye program's,
played in MuJoCo through the gimbal's command map, as the next Mech's eyes Core will play them. The neck and the jaw
join as they move.

## Its parts

<!--{{ next_parts }}-->
