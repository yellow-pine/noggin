# Anatomically Correct Human Skull, by 3Demon: CC BY-SA 4.0

The files in this folder are not under the repo's PolyForm Noncommercial licence (`LICENSE.md` at the root). They are
adapted from [Anatomically Correct Human Skull (Homo Sapiens Sapiens)](https://www.printables.com/model/777324) by
[3Demon](https://www.printables.com/@3Demon), shared under
[Creative Commons Attribution-ShareAlike 4.0 International](https://creativecommons.org/licenses/by-sa/4.0/), and are
shared under the same licence.

Changes from the original (#838, 2026-11-03):

- The cranium: the original's two cranium bodies (its cut) as one mesh, the alignment pegs left out, decimated to
  160,000 faces in Blender.
- The mandible: the original's mandible, decimated to 40,000 faces.

Since #873 (2026-11-04) both live in the Skeleton scene, `model/skeleton/skeleton.blend` (its objects `next skull` and
`next mandible`), scaled to the next Mech's head and set on its eyes, under this licence. The model builds from them,
and every adaptation it writes is shared under the same licence (`model/skeleton`, docs/adr/0025): the orbits enlarged
for its eyes and lids, remeshed for printing and carved for its mechanism.
