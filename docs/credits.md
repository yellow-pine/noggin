# Credits

The Mech is our own design (#51): our parts and the model of them, the behaviour (the Core program, the noggin service,
the hooks) and the simulation. It builds on:

- Bambu Lab's [CyberBrick](https://wiki.bambulab.com/en/cyberbrick) Core, shields, servos and MicroPython build.
- 3Demon's [Anatomically Correct Human Skull](https://www.printables.com/model/777324) (CC BY-SA 4.0) for the
  realistic Skeleton's skull and mandible, and Isopropyl Alcohol's
  [Atlas and Axis (C1 and C2) Cervical Vertebrae](https://www.printables.com/model/1087469) (CC BY-NC-SA 4.0) for its
  atlas and axis: scaled to the head, decimated, the orbits opened for the eyes and lids, remeshed and carved for the
  mechanism. Each adaptation stays under its source's licence (`model/skull/`, docs/adr/0023).
- [GazeBase](https://doi.org/10.1038/s41597-021-00959-y) (Griffith et al., CC BY 4.0) for the recorded eye movements.

Built with [Claude Code](https://docs.claude.com/en/docs/claude-code), [CadQuery](https://cadquery.readthedocs.io),
[MuJoCo](https://mujoco.org), [Blender](https://www.blender.org), [three.js](https://threejs.org),
[MicroPython](https://micropython.org) on the Core and [Astro Starlight](https://starlight.astro.build).
