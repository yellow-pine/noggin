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

`sources.json` maps every adopted object to its source FJ identifier. The working scene comes from
prototype commit `8a937251`: 21 cranial elements, one mandible, C1–C7 and 27 upper-chest elements.
The prototype selected T1–T4 and the first four rib/cartilage pairs from the complete downloaded
package; the package's remaining lower thoracic/rib/cartilage meshes and two sclera references are
not anatomical objects in this scene. Each working mesh was decimated to at most 3000 faces.
Do not describe these working meshes as restored full-resolution source geometry.

Adaptations include posing in the shared bust frame, landmark warping, authored Sculpt deltas,
teaching cuts and live Geometry Nodes finishes for walls and mechanical clearances. Basis, Warp
and Sculpt remain editable. No private character reference geometry is included in the source scene.

The fitting software uses SciPy and Shapely (BSD-3-Clause); Shapely wraps GEOS (LGPL-2.1-or-later).
Shapely 2.2.0 was published on 2026-10-07, more than 14 days before adoption on 2026-11-04.
