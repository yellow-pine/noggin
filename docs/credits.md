# Credits

The mechanism is [PurpleShark](https://makerworld.com/en/@PurpleShark)'s three-part CyberBrick animatronic series on
MakerWorld: [eyes](https://makerworld.com/en/models/1718839) (1718839),
[pan & tilt](https://makerworld.com/en/models/1766064) (1766064) and
[mouth](https://makerworld.com/en/models/1861301) (1861301). noggin owes its existence to that work; what this repo
adds is the behaviour (the Core program, the noggin service, the hooks) and the model (our own parametric parts and a
simulation of the Mech). The designer's models carry their own licences and are not redistributed here.

- Bambu Lab's [CyberBrick](https://wiki.bambulab.com/en/cyberbrick) Core, shields and MicroPython build, and the
  release notes of its [firmware](https://wiki.bambulab.com/en/software/cyberbrick-apps/Firmware-release-notes) and
  [desktop app](https://wiki.bambulab.com/en/software/cyberbrick-apps/PC-release-notes) (`firmware.yml` reads both
  links from here).
- [GazeBase](https://doi.org/10.1038/s41597-021-00959-y) (Griffith et al., CC BY 4.0) for the recorded eye movements.
- Duke Doks' [Morty head](https://makerworld.com/en/models/1455413) (MakerWorld 1455413), the reference for the face.

Built with [Claude Code](https://docs.claude.com/en/docs/claude-code), [CadQuery](https://cadquery.readthedocs.io),
[MuJoCo](https://mujoco.org), [Blender](https://www.blender.org), [three.js](https://threejs.org),
[MicroPython](https://micropython.org) on the Core and [Astro Starlight](https://starlight.astro.build).
