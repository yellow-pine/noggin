# Credits

The Mech is our own design (#51): our parts and the model of them, the behaviour (the Core program, the noggin service,
the hooks) and the simulation. It builds on:

- Bambu Lab's [CyberBrick](https://wiki.bambulab.com/en/cyberbrick) Core, shields, servos and MicroPython build.
- [BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/desc.html) 4.0, © The Database Center for Life
  Science (DBCLS), Japan (treated as CC BY-SA 2.1 JP), for the realistic Skeleton's skull, mandible and seven cervical
  vertebrae: posed in the bust's frame, decimated, warped onto the Mech within a local length budget, the orbits opened
  for the eyes and lids, remeshed and carved for the mechanism. The adaptation stays under its source's licence
  (`model/skeleton/LICENSE.md`, docs/adr/0023, 0025).
- [Morty Smith [Rick and Morty]](https://www.printables.com/model/13460-morty-smith-rick-and-morty) by ChelsCCT
  (Chelsey Creates Things), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), for Morty's Skin: the sculpt,
  decimated for git, stays under its own licence (`model/morty/LICENSE.md`, docs/adr/0027), and his
  Shells are cut from its surface. The licence covers the mesh alone: Morty Smith is Adult Swim's character.
- [GazeBase](https://doi.org/10.1038/s41597-021-00959-y) (Griffith et al., CC BY 4.0) for the recorded eye movements.

Built with [Claude Code](https://docs.claude.com/en/docs/claude-code), [CadQuery](https://cadquery.readthedocs.io),
[MuJoCo](https://mujoco.org), [Blender](https://www.blender.org), [three.js](https://threejs.org),
[MicroPython](https://micropython.org) on the Core and [Astro Starlight](https://starlight.astro.build).
