# Anatomical mesh source: BodyParts3D 4.0

The anatomical meshes in `model/skeleton/skeleton.blend` are adaptations of
[BodyParts3D](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/desc.html),
© The Database Center for Life Science (DBCLS), Japan.

The downloaded Compatibility Version 4.0 OBJ package's headers identify FJ/FMA elements and
[Creative Commons Attribution-ShareAlike 2.1 Japan](https://creativecommons.org/licenses/by-sa/2.1/jp/).
These anatomical meshes and their adaptations are **not under the repo's PolyForm Noncommercial licence**.
The current [archive licence page](https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html), updated
2025-02-27, instead states CC BY 4.0. This project retains the source package's attribution and the
stricter CC BY-SA 2.1 JP treatment agreed for this adoption; it does not silently relabel the package.

`sources.json` maps every adopted object to its source FJ identifier: 21 cranial elements, the mandible and C1–C7,
taken from prototype commit `8a937251`'s scene, each working mesh decimated to at most 3000 faces. Do not describe these
working meshes as restored full-resolution source geometry. The upper chest's elements are #875's.

Adaptations include posing in the shared bust frame, landmark warping, authored Sculpt deltas,
teaching cuts and live Geometry Nodes finishes for walls and mechanical clearances. Basis, Warp
and Sculpt remain editable. No private character reference geometry is included in the source scene.

The fitting software uses SciPy (BSD-3-Clause).
